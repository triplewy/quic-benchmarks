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


def analyze_pcap(filename: str) -> (dict, str):
    end_time = 0
    losses = []

    rx_seq = set()

    with open(filename) as f:
        data = json.load(f)

        # Associate each ACK offset with a timestamp
        for packet in data:
            tcp = packet['_source']['layers']['tcp']
            srcport = tcp['tcp.srcport']
            time = float(tcp['Timestamps']['tcp.time_relative']) * 1000

            # receive packet
            if srcport == '443':
                end_time = max(end_time, time)

                bytes_seq = int(tcp['tcp.seq'])
                bytes_len = int(tcp['tcp.len'])

                if bytes_len == 0:
                    continue

                # Since pcap captures all packets before the filter, it will capture 'lost' packets as well
                # So a lost packet is when we receive the same seq multiple times
                if bytes_seq in rx_seq:
                    losses.append({'of': bytes_seq})
                else:
                    rx_seq.add(bytes_seq)

    losses.sort(key=lambda x: x['of'])
    print(losses, len(losses) / len(rx_seq) * 100, filename)
    return losses, end_time,


def analyze_qlog(filename: str):
    start_time = None
    end_time = 0
    losses = []
    rx_packets = 0

    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        prev_pkt = {'pn': -1, 'of': -1}

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

            if event_type.lower() == 'packet_received':

                if 'frames' not in event_data:
                    continue

                rx_packets += 1

                frames = event_data['frames']
                for frame in frames:
                    if frame['frame_type'].lower() == 'stream':
                        if frame['stream_id'] != '0':
                            continue

                        pkt_num = int(event_data['header']['packet_number'])
                        offset = int(frame['offset'])

                        # if current packet offset is greater than prev packet, there is no loss
                        if prev_pkt['of'] < offset:
                            prev_pkt = {'pn': pkt_num, 'of': offset}
                        # here, current packet offset is less than or equal to prev packet
                        # in that case, current packet number is greater than prev packet number,
                        # there was loss at the offset defined in the current packet
                        elif prev_pkt['pn'] < pkt_num:
                            losses.append({'pn': pkt_num, 'of': offset})
                        else:
                            print('out of order packet')

                end_time = max(end_time, ts)

    losses.sort(key=lambda x: x['of'])
    return losses, end_time, rx_packets


def plot(data, graph_title: str):
    fig, ax = plt.subplots(figsize=(8, 6))

    if graph_title.count('tcp') > 0:
        plt.ylabel('TTLB', fontsize=18, labelpad=15)

    plt.xlabel('Data offset of first retransmitted packet',
               fontsize=18, labelpad=15)

    losses = [x[0] for x in data]
    end_times = [x[1] for x in data]
    rx_packets = [x[2] for x in data]

    x = np.array([x[0]['of'] / 1024 for x in losses])
    y = np.array([x for x in end_times])
    t = [len(losses[i]) / rx_packets[i] * 100 for i in range(len(losses))]

    plt.scatter(x, y, s=200, c=t, cmap=cm.cool, norm=colors.LogNorm())
    plt.clim(1, 10)

    if graph_title.count('quic') > 0:
        cb = plt.colorbar(ticks=[1, 2, 3, 4, 5, 6, 10])
        cb.ax.set_yticklabels(['1%', '2%', '3%', '4%', '5%', '6%', '10%'])
        cb.ax.tick_params(labelsize=16)
        cb.set_label(label='Percentage of retransmitted packets', size=18)

        plt.yticks([])

    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.tick_params(axis='both', which='minor', labelsize=16)

    formatter0 = StrMethodFormatter('{x:,g} ms')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} kb')
    ax.xaxis.set_major_formatter(formatter1)

    plt.ylim(900, 2000)
    plt.xticks(np.array([0, 100, 200, 300, 400]))

    fig.tight_layout()
    if graph_title is not None:
        plt.savefig(
            '{}/Desktop/graphs_revised/{}'.format(Path.home(), graph_title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qlogdir")
    parser.add_argument("--pcapdir")
    parser.add_argument("--title")

    args = parser.parse_args()

    if args.qlogdir is not None:
        data = []
        qlogdir = args.qlogdir
        files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
        files.sort()
        for qlog in files:
            res = analyze_qlog(qlog)
            data.append(res)

        plot(
            data, f'quic-{args.title}-loss_analysis' if args.title is not None else None)

    if args.pcapdir is not None:
        data = []
        pcapdir = args.pcapdir
        files = glob('{}/**/*.json'.format(pcapdir), recursive=True)
        files.sort()
        for pcap in files:
            res = analyze_pcap(pcap)
            data.append(res)

        plot(
            data, f'tcp-{args.title}-loss_analysis' if args.title is not None else None)


if __name__ == "__main__":
    main()
