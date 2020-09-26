import argparse
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import StrMethodFormatter

from collections import deque
from pathlib import Path
from glob import glob

BLUE = deque(['#0000FF', '#0000B3', '#0081B3',
              '#14293D', '#A7DFE2', '#8ED9CD'])
RED = deque(['#FF0000', '#950000', '#FF005A', '#A9385A', '#C95DB4', 'orange'])
GREEN = deque(['#00FF00', '#008D00', '#005300',
               '#00FF72', '#76FF00', '#24A547'])
ORANGE = deque(['#FF8100', '#FFA700', '#FF6D26', '#FFB500', '#FF632F'])
YELLOW = deque(['#FFFF00', '#DCFF20', '#DCC05A'])
PURPLE = deque(['#6A00CD', '#A100CD', '#7653DE'])


def analyze_cc(filename: str) -> (dict, str):
    print(filename)
    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        cc_ts = {}

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

            if event_type.lower() == 'metrics_updated':
                cwnd = float(event_data['congestion_window']) / 1000
                cc_ts[ts] = cwnd

    return cc_ts


def analyze_ack(filename: str) -> (dict, str):
    print(filename)
    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        ack_ts = {}
        pkts_received = {}
        received_ts = {}

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

            if event_type.lower() == 'packet_received':

                # Associate packet num with data offset
                if 'frames' not in event_data:
                    continue

                frames = event_data['frames']

                for frame in frames:
                    if frame['frame_type'].lower() == 'stream':
                        if frame['stream_id'] != '0':
                            continue

                        pkt_num = int(event_data['header']['packet_number'])
                        offset = int(frame['offset'])
                        length = int(frame['length'])
                        pkts_received[pkt_num] = offset + length
                        received_ts[ts] = (offset + length) / 1024

            if event_type.lower() == 'packet_sent':
                # Get max ack sent
                if 'frames' not in event_data:
                    continue

                local_max_ack = None
                frames = event_data['frames']
                for frame in frames:
                    if 'acked_ranges' not in frame:
                        continue

                    for ack in frame['acked_ranges']:
                        if len(ack) != 2:
                            continue

                        ack_begin = int(ack[0])
                        ack_end = int(ack[1])

                        for i in range(ack_begin, ack_end + 1):
                            if i not in pkts_received:
                                continue

                            if local_max_ack is None:
                                local_max_ack = pkts_received[i]

                            local_max_ack = max(
                                local_max_ack, pkts_received[i])

                if local_max_ack is not None:
                    ack_ts[ts] = local_max_ack / 1024

    return ack_ts


def plot(client_data, server_data, graph_title: str):
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()
    # plt.ylabel('Total KB ACKed')
    # plt.xlabel('Time (ms)')
    # plt.title(graph_title)

    legend = [
        mpatches.Patch(color='red', label='Chrome H3'),
        mpatches.Patch(color='blue', label='Proxygen H3'),
        mpatches.Patch(color='green', label='Ngtcp2 H3'),
        mpatches.Patch(color='orange', label='Quiche H3'),
        mpatches.Patch(color='yellow', label='Aioquic H3'),
    ]

    for i, ack_ts in enumerate(client_data):
        color = BLUE.popleft()
        ax1.plot(
            [x[0] for x in ack_ts.items()],
            [x[1] for x in ack_ts.items()],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=4,
        )

    for i, cc_ts in enumerate(server_data):
        color = ORANGE.popleft()
        ax2.plot(
            [x[0] for x in cc_ts.items()],
            [x[1] for x in cc_ts.items()],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=2,
            markersize=0,
        )

    ax1.tick_params(axis='both', which='major', labelsize=18)
    ax1.tick_params(axis='both', which='minor', labelsize=18)
    ax2.tick_params(axis='both', which='major', labelsize=18)
    ax2.tick_params(axis='both', which='minor', labelsize=18)

    formatter0 = StrMethodFormatter('{x:,g} kb')
    ax1.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax1.xaxis.set_major_formatter(formatter1)

    ax2.yaxis.set_major_formatter(formatter0)

    # plt.yticks(np.array([0, 250, 500, 750, 1000]))
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    # plt.xticks(np.array([250, 500, 750, 1000, 1250]))
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs/quiche_analysis'.format(Path.home()), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("qlogdir")

    args = parser.parse_args()

    qlogdir = args.qlogdir

    client_data = []
    server_data = []

    files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
    files.sort()
    for qlog in files:
        if qlog.count('server') > 0:
            server_data.append(analyze_cc(qlog))
        elif qlog.count('client') > 0:
            client_data.append(analyze_ack(qlog))

    plot(client_data, server_data, qlogdir.split('/')[-1])


if __name__ == "__main__":
    main()
