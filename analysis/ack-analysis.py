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
RED = deque(['#FF0000', '#950000', '#FF005A',
             '#A9385A', '#C95DB4', 'orange',
             '#FF0000', '#950000', '#FF005A',
             '#A9385A', '#C95DB4', 'orange'])
GREEN = deque(['#00FF00', '#008D00', '#005300',
               '#00FF72', '#76FF00', '#24A547',
               '#00FF00', '#008D00', ])
ORANGE = deque(['#FF8100', '#FFA700', '#FF6D26'])
YELLOW = deque(['#FFFF00', '#DCFF20', '#DCC05A'])
PURPLE = deque(['#6A00CD', '#A100CD', '#7653DE'])


def analyze_pcap(filename: str) -> (dict, str):
    # print(filename)
    with open(filename) as f:
        data = json.load(f)

        ack_ts = {}
        received_ts = {}
        window_updates = {}
        max_stream_data = {}
        lost_packets = {}

        prev_ack = 0
        lost_packet = None
        lost_time = None
        num_lost = 0

        fin = False
        prev_seq = -1

        # Associate each ACK offset with a timestamp
        for packet in data:
            tcp = packet['_source']['layers']['tcp']
            srcport = tcp['tcp.srcport']
            dstport = tcp['tcp.dstport']
            time = float(tcp['Timestamps']['tcp.time_relative']) * 1000

            # receive packet
            if srcport == '443':
                if tcp['tcp.flags_tree']['tcp.flags.fin'] == '1':
                    fin = True
                bytes_seq = int(tcp['tcp.seq']) / 1024
                received_ts[time] = bytes_seq

                if bytes_seq > prev_seq:
                    prev_seq = bytes_seq
                else:
                    num_lost += 1
                    lost_packets[time] = bytes_seq

            # send packet
            else:
                if fin:
                    continue
                if tcp['tcp.flags_tree']['tcp.flags.syn'] == '1' and time > 500:
                    fin = True
                    continue

                bytes_ack = int(tcp['tcp.ack']) / 1024
                ack_ts[time] = bytes_ack
                window = int(tcp['tcp.window_size']) / 1024
                window_updates[time] = window
                max_stream_data[time] = bytes_ack + window

                if bytes_ack == prev_ack and bytes_ack > 1:
                    if lost_packet is None:
                        lost_packet = (bytes_ack, window)
                        lost_time = time
                        # print('ack: {}kb, window: {}kb'.format(bytes_ack, window))
                else:
                    if lost_time and time - lost_time > 5:
                        # print('recovery: {}ms, lost_packet: {}'.format(
                        #     time - lost_time, lost_packet))
                        pass

                    lost_time = None
                    lost_packet = None
                    prev_ack = bytes_ack

    print(filename, "num_lost", num_lost)
    return {'ack_ts': ack_ts, 'window_updates': window_updates, 'max_stream_data': max_stream_data, 'lost_packets': lost_packets}, filename


def analyze_qlog(filename: str) -> (dict, str):
    print(filename)
    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        first_time = None

        ack_ts = {}
        pkts_received = {}
        received_ts = {}
        max_stream_data = {}
        lost_packets = {}

        prev_pkt = {'pn': 0, 'dl': 0}
        loss_count = 0

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

            if event_type.lower() == 'packet_sent' and first_time is None:
                first_time = ts

            if first_time is None:
                continue

            ts -= first_time

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

                        data_length = (offset + length) / 1024

                        pkts_received[pkt_num] = data_length
                        received_ts[ts] = data_length

                        if prev_pkt['dl'] < data_length:
                            prev_pkt = {'pn': pkt_num, 'dl': data_length}
                        elif prev_pkt['pn'] < pkt_num:
                            # print('loss detected', prev_pkt, data_length)
                            lost_packets[ts] = data_length
                            loss_count += 1
                        else:
                            print('out of order packet')

            if event_type.lower() == 'packet_sent':
                # Get max ack sent
                if 'frames' not in event_data:
                    continue

                local_max_ack = None
                frames = event_data['frames']
                for frame in frames:
                    if frame['frame_type'] == 'max_stream_data':
                        max_stream_data[ts] = int(frame['maximum']) / 1024

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
                    ack_ts[ts] = local_max_ack

    print(filename, "num_lost", loss_count)
    return {'ack_ts': ack_ts, 'max_stream_data': max_stream_data, 'lost_packets': lost_packets}, filename


def plot_ack(data, graph_title: str):
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.ylabel('Total KB ACKed', fontsize=18, labelpad=10)
    plt.xlabel('Time (ms)', fontsize=18, labelpad=10)
    # plt.title(graph_title)
    # ax2 = ax.twinx()

    legend = [
        mpatches.Patch(color='red', label='Chrome H3'),
        mpatches.Patch(color='blue', label='Proxygen H3'),
        mpatches.Patch(color='green', label='Ngtcp2 H3'),
        mpatches.Patch(color='orange', label='Quiche H3'),
        mpatches.Patch(color='yellow', label='Aioquic H3'),
    ]

    for i, (obj, title) in enumerate(data):
        ack_ts = obj['ack_ts']

        if title.count('.json') > 0:
            color = RED.popleft()
        elif title.count('chrome') > 0:
            color = BLUE.popleft()
        elif title.count('proxygen') > 0:
            # color = BLUE.popleft()
            color = 'blue'
        elif title.count('ngtcp2') > 0:
            # color = GREEN.popleft()
            color = 'green'
        elif title.count('quiche') > 0:
            color = PURPLE.popleft()
        elif title.count('aioquic') > 0:
            color = YELLOW.popleft()

        ax.plot(
            [x[0] for x in ack_ts.items()],
            [x[1] for x in ack_ts.items()],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=4,
        )

        # # throughput
        # items = list(sorted(ack_ts.items(), key=lambda x: x[0]))
        # throughputs = []
        # for j, (k2, v2) in enumerate(items):
        #     if j == 0:
        #         continue
        #     k1, v1 = items[j - 1]
        #     throughput = (v2 - v1) / (k2 - k1)
        #     throughputs.append((k2, throughput))

        # if title.count('ngtcp2') == 0:
        #     continue

        # ax2.plot(
        #     [x[0] for x in throughputs],
        #     [x[1] for x in throughputs],
        #     color='purple',
        #     linestyle='-',
        #     linewidth=1
        # )

    # for obj, title in data:
    #     if 'lost_packets' not in obj:
    #         continue
    #     for k, v in obj['lost_packets'].items():
    #         ax.plot(
    #             k,
    #             v,
    #             color='orange' if title.count('ngtcp2') == 0 else 'blue',
    #             marker='x',
    #             markersize=4,
    #             linewidth=0
    #         )

    # for i, (obj, title) in enumerate(data):
    #     if 'window_updates' not in obj:
    #         continue
    #     updates = obj['window_updates']

    #     ax2.plot(
    #         [x[0] for x in updates.items()],
    #         [x[1] for x in updates.items()],
    #         color='green',
    #         marker='o',
    #         linestyle='-',
    #         linewidth=1,
    #         markersize=1,
    #     )

    #     for k, v in updates.items():
    #         if v == 0:
    #             ax.axvline(k, color='orange')

    # for i, (obj, title) in enumerate(data):
    #     if 'max_stream_data' not in obj:
    #         continue
    #     updates = obj['max_stream_data']

    #     ax.plot(
    #         [x[0] for x in updates.items()],
    #         [x[1] for x in updates.items()],
    #         color='blue',
    #         marker='o',
    #         linestyle='-',
    #         linewidth=1,
    #         markersize=1,
    #     )

    ax.tick_params(axis='both', which='major', labelsize=18)
    ax.tick_params(axis='both', which='minor', labelsize=18)

    formatter0 = StrMethodFormatter('{x:,g} kb')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.xticks(np.array([0, 2000, 4000, 6000]))
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    plt.xticks(np.array([0, 200, 400, 600, 800]))
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs/{}'.format(Path.home(), graph_title), transparent=True)
    # plt.legend(handles=legend)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qlogdir")
    parser.add_argument("--pcapdir")

    args = parser.parse_args()

    qlogdir = args.qlogdir
    pcapdir = args.pcapdir

    data = []
    wnd_updates = []

    files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
    files.sort()
    for qlog in files:
        if qlog.split('.')[0][-1] != '3':
            continue

        data.append(analyze_qlog(qlog))

    if pcapdir is not None:
        files = glob('{}/**/*.json'.format(pcapdir), recursive=True)
        for pcap in files:
            if pcap.split('.')[0][-1] != '1':
                continue

            data.append(analyze_pcap(pcap))
            # print(pcap, max(data[-1][0].keys()))

    plot_ack(data, qlogdir.split('/')[-1])


if __name__ == "__main__":
    main()
