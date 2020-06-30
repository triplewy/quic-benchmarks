import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from pathlib import Path
from glob import glob


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

        # Store all stream packets received by client
        for event in events:
            if not event:
                continue

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

        # Associate each ACK packet sent with a data offset
        for event in events:
            if not event:
                continue

            if time_units == 'ms':
                ts = int(event[0])
            else:
                ts = int(event[0]) / 1000

            event_type = event[2]
            event_data = event[3]

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

                ack_ts[ts] = local_max_ack

    if 'title' in traces:
        title = traces['title']
    else:
        title = '{} {}'.format(vantage['name'], vantage['type'])

    return ack_ts, title


def plot_ack(data, graph_title: str):
    colors = ['green', 'cyan', 'orange', 'red', '#763BB1']
    fig = plt.figure(figsize=(12, 9))
    plt.ylabel('Total Data ACKed (bytes)')
    plt.xlabel('Time (ms)')
    plt.title('ACK timeline for {}'.format(graph_title))

    legend = []

    for i, (ack_ts, title) in enumerate(data):
        color = colors[i]
        legend.append(mpatches.Patch(
            color=color, label=title.replace(' ', '_')))

        plt.plot(
            [x[0] for x in ack_ts.items()],
            [x[1] for x in ack_ts.items()],
            color=color,
            marker='o',
            linestyle='',
            markersize=2,
        )

    plt.legend(handles=legend)
    fig.savefig(Path.joinpath(Path.home(), 'quic-benchmarks',
                              'graphs', 'qlog_{}'.format(graph_title)), dpi=fig.dpi)
    plt.close(fig=fig)


def main():
    dir_name = sys.argv[1]
    size = sys.argv[2]
    rtt = sys.argv[3]
    loss = sys.argv[4]
    data = []

    files = glob('{}/**/*.qlog'.format(dir_name), recursive=True)

    for qlog_file in files:
        data.append(analyze_qlog(qlog_file))
    plot_ack(data, '{}-{}ms-{}loss'.format(size, rtt, loss))


if __name__ == "__main__":
    main()
