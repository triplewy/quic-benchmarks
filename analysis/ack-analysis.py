import argparse
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import StrMethodFormatter


from pathlib import Path
from glob import glob
from optparse import OptionParser


def analyze_pcap(filename: str) -> (dict, str):
    print(filename)
    with open(filename) as f:
        data = json.load(f)

        ack_ts = {}

        fin = False

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
                continue
            # send packet
            else:
                if fin:
                    continue
                bytes_ack = int(tcp['tcp.ack'])
                ack_ts[time] = bytes_ack / 1024

    return ack_ts, filename


def analyze_qlog(filename: str) -> (dict, str):
    print(filename)
    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        vantage = traces['vantage_point']
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

    if 'title' in traces:
        title = traces['title']
    else:
        title = '{} {}'.format(vantage['name'], vantage['type'])

    return ack_ts, filename


def plot_ack(data, graph_title: str):
    colors = [
        '#41A9C0', 'cyan', 'blue',
        '#14293D', '#A7DFE2', '#8ED9CD',
        # 'red', '#C34B5D', '#DC00A1',
        # '#A9385A', '#C95DB4', 'orange'
    ]
    fig, ax = plt.subplots(figsize=(12, 9))
    # plt.ylabel('Total KB ACKed')
    # plt.xlabel('Time (ms)')
    plt.title(graph_title)

    legend = [
        mpatches.Patch(color='red', label='Chrome H2'),
        mpatches.Patch(color='blue', label='Proxygen H3')
    ]

    for i, (ack_ts, title) in enumerate(data):
        color = colors[i]
        # legend.append(mpatches.Patch(
        #     color=color, label=title))

        plt.plot(
            [x[0] for x in ack_ts.items()],
            [x[1] for x in ack_ts.items()],
            color=color,
            marker='o',
            linestyle='-',
            markersize=3,
        )

    ax.tick_params(axis='both', which='major', labelsize=20)
    ax.tick_params(axis='both', which='minor', labelsize=20)

    formatter0 = StrMethodFormatter('{x:,g} kb')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.yticks(np.array([0, 250, 500, 750, 1000]))
    # plt.xticks(np.array([0, 500, 1000, 1500]))

    plt.legend(handles=legend)
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

    files = glob('{}/**/*.qlog'.format(qlogdir), recursive=True)
    files.sort()
    for qlog in files:
        if qlog.count('proxygen') > 0:
            continue
        data.append(analyze_qlog(qlog))

    files = glob('{}/**/*.json'.format(pcapdir), recursive=True)
    for pcap in files:
        data.append(analyze_pcap(pcap))

    plot_ack(data, 'Google 1MB - 5% Loss')


if __name__ == "__main__":
    main()