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
    cc_ts = []

    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

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
                cwnd = float(event_data['congestion_window']) / 1024
                cc_ts.append((ts, cwnd))

    return cc_ts, filename


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


def plot(data, graph_title: str):
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.ylabel('Cwnd', fontsize=18, labelpad=10)
    plt.xlabel('Time (ms)', fontsize=18, labelpad=10)
    # plt.title(graph_title)

    legend = []

    for i, (cc_ts, title) in enumerate(data):
        if title.count('chrome_h3') > 0:
            # color = ORANGE.popleft()
            color = 'orange'
            legend.append(mpatches.Patch(color='orange',
                                         label='Chrome H3:                  {} updates'.format(len(cc_ts))))
        elif title.count('proxygen_h3') > 0:
            # color = BLUE.popleft()
            color = 'blue'
            legend.append(mpatches.Patch(color='blue',
                                         label='Proxygen H3 (10 ACK): {} updates'.format(len(cc_ts))))
        elif title.count('proxygen_ack_h3') > 0:
            # color = BLUE.popleft()
            color = '#A7DFE2'
            legend.append(mpatches.Patch(color='#A7DFE2',
                                         label='Proxygen H3 (2 ACK):   {} updates'.format(len(cc_ts))))
        elif title.count('ngtcp2_h3') > 0:
            # continue
            color = 'green'
            legend.append(mpatches.Patch(color='green',
                                         label='Ngtcp2 H3:                   {} updates'.format(len(cc_ts))))

        ax.plot(
            [x[0] for x in cc_ts],
            [x[1] for x in cc_ts],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=2,
            markersize=4,
        )

    ax.tick_params(axis='both', which='major', labelsize=18)
    ax.tick_params(axis='both', which='minor', labelsize=18)

    formatter0 = StrMethodFormatter('{x:,g} KB')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.yticks(np.array([0, 250, 500, 750, 1000]))
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    # plt.xticks(np.array([250, 500, 750, 1000, 1250]))
    plt.rcParams["legend.fontsize"] = 14
    plt.rcParams['legend.loc'] = 'upper right'
    plt.legend(handles=legend)
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs_revised/{}'.format(Path.home(), graph_title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("qlogdir")
    parser.add_argument("--title")

    args = parser.parse_args()

    qlogdir = args.qlogdir
    title = args.title

    data = []

    files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
    files.sort()
    for qlog in files:
        data.append(analyze_cc(qlog))

    plot(data, title)


if __name__ == "__main__":
    main()
