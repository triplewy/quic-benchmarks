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

BLUE = deque(['#7CDCED', '#0000FF', '#0000B3', '#0081B3',
              '#14293D', '#A7DFE2', '#8ED9CD'])
RED = deque(['#FF0000', '#950000', '#FF005A', '#A9385A', '#C95DB4', 'orange'])
GREEN = deque(['#00FF00', '#008D00', '#005300',
               '#00FF72', '#76FF00', '#24A547'])
ORANGE = deque(['#FF8100', '#FFA700', '#FF6D26'])
YELLOW = deque(['#FFFF00', '#DCFF20', '#DCC05A'])

COLORS = deque(['#0000FF', '#FF0000', '#00FF00', '#FF8100', ])

LINE = 10


def analyze_qlog(filename):
    global LINE

    if filename.count('good') > 0:
        name = 'Proxygen (good)'
        event_line = LINE
        # LINE += 5
    elif filename.count('mid') > 0:
        name = 'Proxygen (bad)'
        event_line = LINE
        LINE += 10
    elif filename.count('ngtcp2') > 0:
        name = 'Ngtcp2'
        event_line = LINE
        LINE += 10
    elif filename.count('chrome') > 0:
        name = 'Chrome'
        event_line = LINE
        LINE += 10
    else:
        return None

    with open(filename) as f:
        data = json.load(f)

        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        curr_bw = 0
        bandwidth = {}
        loss = {}
        handshake_done = {}
        data_sent = {}
        acks_received = {}
        packets_sent = {}

        curr_ack = 0

        # Store all stream packets received by client
        for event in events:
            if not event:
                continue

            if time_units == 'ms':
                ts = int(event[0])
            else:
                ts = int(event[0]) / 1000

            event_type = event[2]
            event_data = event[3]

            if event_type.lower() == 'bandwidth_est_update':
                bandwidth[ts] = int(event_data['bandwidth_bytes']) / 1024
                curr_bw = bandwidth[ts]

            if event_type.lower() == 'loss_alarm':
                loss[ts] = event_line

            if event_type.lower() == 'packet_sent':
                if 'frames' in event_data:
                    for frame in event_data['frames']:
                        if frame['frame_type'] == 'handshake_done':
                            handshake_done[ts] = event_line
                        if frame['frame_type'] == 'stream' and frame['stream_id'] == '0':
                            data_offset = frame['offset'] + frame['length']
                            data_sent[ts] = data_offset / 1024
                            packets_sent[event_data['header']
                                         ['packet_number']] = data_offset / 1024

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

        return {
            'bw': bandwidth,
            'loss': loss,
            'handshake_done': handshake_done,
            'data_sent': data_sent,
            'acks_received': acks_received
        }, name


def plot_ack(data, title):
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.ylabel('Server estimated bandwidth', fontsize=18, labelpad=15)
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

        if name.count('Chrome') > 0:
            color = RED.popleft()
            name = 'Chrome (Loss)'
        elif name.count('Proxygen (bad)') > 0:
            if found_proxygen_bad:
                continue
            found_proxygen_bad = True
            if random.uniform(0, 1) >= 0.5:
                color = ORANGE.popleft()
            else:
                color = RED.popleft()
            color = BLUE.popleft()
            name = 'Proxygen (Loss)'
        elif name.count('Proxygen (good)') > 0:
            color = BLUE.popleft()
            name = 'Proxygen (No Loss)'
        else:
            color = GREEN.popleft()
            name = 'Ngtcp2 (Loss)'

        legend.append(mpatches.Patch(color=color, label=name))

        plt.plot(
            [x[0] for x in bw_ts.items()],
            [x[1] for x in bw_ts.items()],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=4,
        )

        # if len(loss_ts) > 0:
        #     plt.axvline(
        #         x=[x + random.uniform(-10, 10) for x in loss_ts.keys()],
        #         color=color,
        #         # marker='x',
        #         linestyle='dashed',
        #         linewidth=0.5,
        #     )

        # plt.plot(
        #     [x[0] for x in loss_ts.items()],
        #     [x[1] for x in loss_ts.items()],
        #     color=color,
        #     marker='x',
        #     linewidth=0,
        #     markersize=8,
        #     mew=4
        # )

        # plt.plot(
        #     [x[0] for x in handshake_done.items()],
        #     [x[1] for x in handshake_done.items()],
        #     color=color,
        #     marker='v',
        #     linewidth=0,
        #     markersize=8,
        # )

        # plt.plot(
        #     [x[0] for x in data_sent.items()],
        #     [x[1] for x in data_sent.items()],
        #     color=color,
        #     marker='s',
        #     linestyle='dotted',
        #     linewidth=1,
        #     markersize=2,
        # )

        # plt.plot(
        #     [x[0] for x in acks_received.items()],
        #     [x[1] for x in acks_received.items()],
        #     color=color,
        #     marker='D',
        #     linestyle='dotted',
        #     linewidth=1,
        #     markersize=2,
        # )

    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.tick_params(axis='both', which='minor', labelsize=16)

    formatter0 = StrMethodFormatter('{x:,g} kb')
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

    found_ngtcp2 = False
    found_chrome = False

    for qlog in files:
        if qlog.count('server') == 0:
            continue

        if qlog.count('ngtcp2') > 0:
            if found_ngtcp2:
                continue
            found_ngtcp2 = True

        if qlog.count('chrome') > 0:
            if found_chrome:
                continue
            found_chrome = True

        res = analyze_qlog(qlog)
        if res is not None:
            data.append(analyze_qlog(qlog))
        else:
            print(qlog)

    plot_ack(data, '{}_bw_analysis'.format(qlogdir.split('/')[-1]))


if __name__ == "__main__":
    main()
