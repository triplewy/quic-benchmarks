import argparse
import sys
import json
import numpy as np
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm

from matplotlib.ticker import StrMethodFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size

from collections import deque
from pathlib import Path
from glob import glob

BLUE = deque(['#0000FF', '#0000B3', '#0081B3',
              '#14293D', '#A7DFE2', '#8ED9CD'])
RED = deque(['#FF0000', '#950000', '#FF005A',
             '#A9385A', '#C95DB4', 'orange',
             '#FF0000', '#950000', ])
GREEN = deque(['#00FF00', '#008D00', '#005300',
               '#00FF72', '#76FF00', '#24A547',
               '#00FF00', '#008D00', ])
ORANGE = deque(['#FF8100', '#FFA700', '#FF6D26'])
YELLOW = deque(['#FFFF00', '#DCFF20', '#DCC05A'])
PURPLE = deque(['#6A00CD', '#A100CD', '#7653DE'])


def analyze_qlog(filename: str) -> (dict, str):
    # print(filename)
    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        start_time = None
        end_time = 0

        ack_ts = {}
        pkts_received = {}
        received_ts = {}

        prev_pkt = {'pn': 0, 'dl': 0, 'of': 0}
        losses = []

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

            if event_type.lower() == 'packet_sent' and start_time is None:
                start_time = ts

            if start_time is None:
                continue

            ts -= start_time

            if event_type.lower() == 'packets_lost':
                losses.append(
                    {'pn': event_data['largest_lost_packet_num'], 'dl': 0, 'of': 0})

            elif event_type.lower() == 'packet_received':
                if ts >= end_time + 31 and event_data['packet_type'] != '1RTT' and event_data['header']['packet_number'] != 0:
                    print('loss detected', filename, event_data)
                    losses.append(
                        {'pn': event_data['header']['packet_number'], 'dl': 0, 'of': 0})

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

                        data_length = (offset + length) / 1024

                        pkts_received[pkt_num] = data_length
                        received_ts[ts] = data_length

                        if prev_pkt['dl'] < data_length:
                            prev_pkt = {'pn': pkt_num,
                                        'dl': data_length, 'of': offset / 1024}
                        elif prev_pkt['pn'] < pkt_num:
                            # print(filename, 'loss detected',
                            #       pkt_num, offset / 1024)
                            losses.append(
                                {'pn': pkt_num, 'dl': data_length, 'of': offset / 1024})
                        else:
                            print('out of order packet')
            elif event_type.lower() == 'datagram_received':
                continue

            end_time = max(end_time, ts)

    losses.sort(key=lambda x: x['dl'])
    return losses, end_time


def plot(data, graph_title: str):
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.ylabel('PLT', fontsize=18, labelpad=15)
    plt.xlabel('Data offset of first detected lost packet',
               fontsize=18, labelpad=15)
    # plt.title(graph_title)

    print(
        min([len(losses) for (losses, _) in data]),
        max([len(losses) for (losses, _) in data]),
    )

    # x = np.array([np.mean(np.ediff1d([x['dl'] for x in losses]))
    #   for (losses, _) in data])
    # x = np.array([len(losses) for (losses, _) in data])
    x = np.array([losses[0]['of'] for (losses, _) in data])
    y = np.array([end_time for (_, end_time) in data])
    t = [len(losses) for (losses, _) in data]

    plt.scatter(x, y, s=100, c=t, cmap=cm.cool, norm=colors.LogNorm()
                # c=min(100, len(losses) ** 1.2),
                # marker='o',
                # linestyle='-',
                # linewidth=1,
                # markersize=8,
                )

    m, b = np.polyfit(x, y, 1)
    # plt.plot(x, m*x + b)

    cb = plt.colorbar(ticks=[5, 10, 20, 30, 40, 50, 90])
    cb.ax.set_yticklabels(['5', '10', '20', '30', '40', '50', '90'])
    cb.ax.tick_params(labelsize=16)
    cb.set_label(label='# of lost packets', size=18)

    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.tick_params(axis='both', which='minor', labelsize=16)

    formatter0 = StrMethodFormatter('{x:,g} ms')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} kb')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.ylim(800, 2200)
    # plt.xlim(0, 200)
    # plt.yticks(np.array([1000, 1250, 1500, 1750, 2000]))
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    # plt.xticks(np.array([0, 300, 600, 900, 1200]))
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs/{}_loss_analysis'.format(Path.home(), graph_title), transparent=True)
    # plt.legend(handles=legend)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("qlogdir")

    args = parser.parse_args()

    qlogdir = args.qlogdir

    data = []

    files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
    files.sort()
    for qlog in files:
        if qlog.count('proxygen') == 0:
            continue

        res = analyze_qlog(qlog)
        if len(res[0]) == 0 or res[1] > 2000:
            continue

        print(qlog, res[0][0]['dl'], res[1], '{} losses'.format(len(res[0])))

        data.append(res)

    plot(data, qlogdir.split('/')[-1])


if __name__ == "__main__":
    main()
