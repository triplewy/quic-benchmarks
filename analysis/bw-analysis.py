import argparse
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import StrMethodFormatter
import random

from collections import deque
from pathlib import Path
from glob import glob

BLUE = deque(['blue', '#7CDCED', '#0000FF', '#0000B3', '#0081B3',
              '#14293D', '#A7DFE2', '#8ED9CD'])
RED = deque(['red', '#FF0000', '#950000', '#FF005A',
             '#A9385A', '#C95DB4', 'orange'])
GREEN = deque(['green', '#00FF00', '#008D00', '#005300',
               '#00FF72', '#76FF00', '#24A547'])
ORANGE = deque(['#FF8100', '#FFA700', '#FF6D26'])
YELLOW = deque(['#FFFF00', '#DCFF20', '#DCC05A'])

COLORS = deque(['#0000FF', '#FF0000', '#00FF00', '#FF8100', ])

LINE = 10


def analyze_qlog(filename):
    bandwidth = {}
    loss = {}
    handshake_done = {}
    data_sent = []
    acks_received = {}
    packets_sent = {}
    cwnd_updates = []
    bytes_in_flight = []

    with open(filename) as f:
        data = json.load(f)

        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        start = None
        curr_bw = 0
        curr_ack = 0

        # Store all stream packets received by client
        for event in events:
            if not event:
                continue

            if time_units == 'ms':
                ts = int(event[0])
            else:
                ts = int(event[0]) / 1000

            if start is None:
                start = ts

            ts -= start

            event_type = event[2]
            event_data = event[3]

            if event_type.lower() == 'bandwidth_est_update':
                bandwidth[ts] = int(event_data['bandwidth_bytes'])
                curr_bw = bandwidth[ts]

            if event_type.lower() == 'packet_sent':
                if 'frames' in event_data:
                    for frame in event_data['frames']:
                        if frame['frame_type'] == 'stream' and frame['stream_id'] == '0':
                            data_offset = frame['offset'] + frame['length']
                            data_sent.append((ts, data_offset))
                            packets_sent[event_data['header']
                                         ['packet_number']] = data_offset

            if event_type.lower() == 'packet_received':
                if 'frames' in event_data:
                    for frame in event_data['frames']:
                        if frame['frame_type'] == 'ack':

                            local_max_ack = None

                            for ack in frame['acked_ranges']:
                                if len(ack) != 2:
                                    continue

                                ack_begin = int(ack[0])
                                ack_end = int(ack[1])

                                for i in range(ack_begin, ack_end + 1):
                                    if i not in packets_sent:
                                        continue

                                    if local_max_ack is None:
                                        local_max_ack = packets_sent[i]

                                    local_max_ack = max(
                                        local_max_ack, packets_sent[i])

                            curr_ack = local_max_ack
                            acks_received[ts] = local_max_ack

            if event_type.lower() == 'congestion_metric_update':
                bif = int(event_data['bytes_in_flight'])
                cwnd = int(event_data['current_cwnd'])
                cwnd_updates.append((ts, cwnd))
                bytes_in_flight.append((ts, bif))

    return {
        'bw': bandwidth,
        'loss': loss,
        'handshake_done': handshake_done,
        'data_sent': data_sent,
        'acks_received': acks_received,
        'cwnd_updates': cwnd_updates,
        'bytes_in_flight': bytes_in_flight
    }, filename


def plot_ack(data, title):
    fig, ax = plt.subplots(figsize=(10, 6))
    # plt.ylabel('Server estimated bandwidth', fontsize=18, labelpad=15)
    plt.ylabel('Data sent', fontsize=18, labelpad=15)
    plt.xlabel('Time elapsed', fontsize=18, labelpad=15)
    # plt.title(graph_title)

    legend = []
    found_proxygen_bad = False

    for i, (obj, name) in enumerate(data):
        bw_ts = obj['bw']
        loss_ts = obj['loss']
        handshake_done = obj['handshake_done']
        data_sent = obj['data_sent']
        acks_received = obj['acks_received']
        cwnd_updates = obj['cwnd_updates']
        bytes_in_flight = obj['bytes_in_flight']

        if name.count('chrome_h3') > 0:
            color = RED.popleft()
            name = 'Chrome H3'
        elif name.count('proxygen_h3') > 0:
            color = BLUE.popleft()
            name = 'Proxygen H3'
            continue
        else:
            color = GREEN.popleft()
            name = 'Ngtcp2 H3'

        legend.append(mpatches.Patch(color=color, label=name))

        # plt.plot(
        #     [x[0] for x in bw_ts.items()],
        #     [x[1] / 1024 for x in bw_ts.items()],
        #     color=color,
        #     marker='o',
        #     linestyle='-',
        #     linewidth=1,
        #     markersize=4,
        # )

        plt.plot(
            [x[0] for x in data_sent],
            [x[1] / 1024 for x in data_sent],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=4,
        )

        plt.plot(
            [x[0] for x in cwnd_updates],
            [x[1] / 1024 for x in cwnd_updates],
            color='red',
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=4,
        )

        # plt.plot(
        #     [x[0] for x in bytes_in_flight],
        #     [x[1] / 1024 for x in bytes_in_flight],
        #     color=color,
        #     marker='o',
        #     linestyle='-',
        #     linewidth=1,
        #     markersize=4,
        # )

    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.tick_params(axis='both', which='minor', labelsize=16)

    # formatter0 = StrMethodFormatter('{x:,g} KB/s')
    formatter0 = StrMethodFormatter('{x:,g} KB')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.yticks(np.array([0, 250, 500, 750, 1000]))
    # plt.xticks(np.array([0, 500, 1000, 1500, 2000]))
    # plt.xlim(0, 6000)
    # plt.ylim(0, 100)
    plt.legend(handles=legend, prop={'size': 12})
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs/{}'.format(Path.home(), title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    qlogdir = args.dir

    data = []

    files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
    files.sort()

    for qlog in files:
        if qlog != 'local/LTE/server/ngtcp2_h3/ngtcp2_h3_1.qlog' and qlog != 'local/LTE/server/proxygen_h3/proxygen_h3_2.qlog':
            continue

        res = analyze_qlog(qlog)
        if res is not None:
            data.append(analyze_qlog(qlog))
        else:
            print(qlog)

        print(qlog, max(res[0]['bw'].keys()))
    plot_ack(data, '{}_bw_analysis'.format(qlogdir.split('/')[-1]))


if __name__ == "__main__":
    main()
