import argparse
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import math
import scipy.stats as st

from collections import Counter
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
    ack_ts = {}
    rx_ts = {}
    window_updates = {}
    max_stream_data = {}
    lost_packets = {}
    rx_packets_ts = []
    initial_rtt = None
    second_rtt = None
    init_cwnd = 0

    with open(filename) as f:
        data = json.load(f)

        prev_ack = 0
        lost_packet = None
        lost_time = None
        num_lost = 0
        tx_tls = None
        rx_tls = None
        start_data_time = None

        fin = False
        prev_seq = -1

        # Associate each ACK offset with a timestamp
        for packet in data:
            tcp = packet['_source']['layers']['tcp']
            srcport = tcp['tcp.srcport']
            dstport = tcp['tcp.dstport']
            time = float(tcp['Timestamps']['tcp.time_relative']) * 1000

            if tcp['tcp.flags_tree']['tcp.flags.fin'] == '1':
                fin = True

            init_rtt = tcp.get('tcp.analysis', {}).get(
                'tcp.analysis.initial_rtt')
            if init_rtt is not None:
                initial_rtt = float(init_rtt)

            if tcp.get("tcp.analysis", {}).get("tcp.analysis.acks_frame") == "4":
                second_rtt = float(tcp.get("tcp.analysis").get(
                    "tcp.analysis.ack_rtt"))

            # receive packet
            if srcport == '443':
                if tcp['tcp.len'] == '1376' and int(tcp['tcp.seq']) >= 3000:
                    if start_data_time is None:
                        start_data_time = time

                    min_rtt = min(initial_rtt, second_rtt) * 1000

                    if time - start_data_time < min_rtt:
                        init_cwnd += 1

                if tcp['tcp.len'] == '0' or int(tcp['tcp.seq']) < 3000:
                    continue

                if fin:
                    continue

                bytes_seq = int(tcp['tcp.seq']) / 1024
                bytes_len = int(tcp['tcp.len']) / 1024

                rx_ts[time] = bytes_seq
                rx_packets_ts.append((time, {'length': bytes_len}))

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
                else:
                    if lost_time and time - lost_time > 5:
                        pass

                    lost_time = None
                    lost_packet = None
                    prev_ack = bytes_ack

    print(filename, initial_rtt, second_rtt, init_cwnd)
    return {
        'ack_ts': ack_ts,
        'rx_ts': rx_ts,
        'rx_packets_ts': rx_packets_ts
    }, filename


def analyze_qlog(filename: str) -> (dict, str):
    ack_ts = {}
    pkts_received = {}
    rx_ts = {}
    max_stream_data = {}
    lost_packets = {}
    rx_packets_ts = []

    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        first_time = None

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
                        rx_ts[ts] = data_length
                        rx_packets_ts.append((ts, {'length': length / 1024}))

                        if prev_pkt['dl'] < data_length:
                            prev_pkt = {'pn': pkt_num, 'dl': data_length}
                        elif prev_pkt['pn'] < pkt_num:
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
                        if 'maximum' in frame:
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

    return {
        'ack_ts': ack_ts,
        'rx_ts': rx_ts,
        'rx_packets_ts': rx_packets_ts,
        'max_stream_data': max_stream_data,
        'lost_packets': lost_packets,
    }, filename


def analyze_netlog(filename: str) -> (dict, str):
    ack_ts = {}
    rx_ts = {}
    rx_packets_ts = []

    with open(filename) as f:
        data = json.load(f)

        constants = data['constants']
        events = data['events']
        event_types = {v: k for k,
                       v in constants['logEventTypes'].items()}
        source_types = {v: k for k,
                        v in constants['logSourceType'].items()}
        phases = {v: k for k,
                  v in constants['logEventPhase'].items()}

        start_time = None
        total_size = 0

        for event in events:
            # source_type in string
            source_type = source_types[event['source']['type']]
            # source id
            source_id = event['source']['id']
            # event_type in string
            event_type = event_types[event['type']]
            # phase in string
            phase = phases[event['phase']]

            if 'params' not in event:
                continue

            # params
            params = event['params']
            # event time
            event_time = int(event['time'])

            if start_time is not None:
                ts = event_time - start_time

            if (event_type == 'TCP_CONNECT' or event_type == 'QUIC_SESSION') and phase == 'PHASE_BEGIN':
                if start_time is None:
                    start_time = event_time

            if event_type == 'HTTP2_SESSION_RECV_DATA':
                total_size += params['size']
                ack_ts[ts] = total_size / 1024
                rx_ts[ts] = total_size / 1024
                rx_packets_ts.append((ts, {'length': params['size'] / 1024}))

            if event_type == 'QUIC_SESSION_STREAM_FRAME_RECEIVED':
                if params['stream_id'] != 0:
                    continue
                rx_ts[ts] = (params['offset'] + params['length']) / 1024
                ack_ts[ts] = (params['offset'] + params['length']) / 1024
                rx_packets_ts.append((ts, {'length': params['length'] / 1024}))

    return {
        'ack_ts': ack_ts,
        'rx_ts': rx_ts,
        'rx_packets_ts': rx_packets_ts
    }, filename


def plot(data, graph_title: str):
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.ylabel('Count', fontsize=18, labelpad=10)
    plt.xlabel('Time (ms)', fontsize=18, labelpad=10)

    legend = []

    data.sort(key=lambda x: np.median(x[0]))

    for i, (timings, title) in enumerate(data):
        print(title)

        median = int(np.median(timings))

        counter = Counter()

        for time in timings:
            bucket = round(time, -2)
            counter[bucket] += 1

        median_bucket = round(median, -2)
        buckets = sorted(list(counter.items()), key=lambda x: x[0])

        if title.count('chrome_h2') > 0:
            continue
            color = 'purple'
            legend.append(mpatches.Patch(color='purple',
                                         label='Chrome H2 (median):   {}ms'.format(median)))
        elif title.count('curl_h2') > 0:
            continue
            color = 'red'
            legend.append(mpatches.Patch(color='red',
                                         label='Curl H2 (median):         {}ms'.format(median)))
        elif title.count('chrome_h3') > 0:
            color = 'orange'
            legend.append(mpatches.Patch(color='orange',
                                         label='Chrome H3 (median):   {}ms'.format(median)))
        elif title.count('proxygen_h3') > 0:
            color = 'blue'
            legend.append(mpatches.Patch(color='blue',
                                         label='Proxygen H3 (median): {}ms'.format(median)))
        elif title.count('proxygen_ack_h3') > 0:
            color = '#A7DFE2'
            legend.append(mpatches.Patch(color='#A7DFE2',
                                         label='Proxygen H3 (median): {}ms'.format(median)))
        elif title.count('ngtcp2') > 0:
            color = 'green'
            legend.append(mpatches.Patch(color='green',
                                         label='Ngtcp2 H3 (median):    {}ms'.format(median)))

        ax.plot(
            [x[0] for x in buckets],
            [x[1] for x in buckets],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=2,
            markersize=4,
        )
        ax.plot(median_bucket, counter[median_bucket],
                color='red', marker='o', markersize=8)

    ax.tick_params(axis='both', which='major', labelsize=18)
    ax.tick_params(axis='both', which='minor', labelsize=18)

    # formatter0 = StrMethodFormatter('{x:,g} kb')
    # formatter0 = StrMethodFormatter('{x:,g} KB')
    # ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.xticks(np.array([0, 2000, 4000, 6000]))
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    # plt.xticks(np.array([0, 800, 1600, 2400, 3200]))
    plt.xticks(np.array([500, 1000, 1500, 2000]))
    fig.tight_layout()
    plt.rcParams["legend.fontsize"] = 14
    plt.rcParams['legend.loc'] = 'upper right'
    plt.legend(handles=legend)
    plt.savefig(
        '{}/Desktop/graphs_revised/{}'.format(Path.home(), graph_title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title")
    parser.add_argument("--timingsdir")

    args = parser.parse_args()

    title = args.title

    data = []

    if args.timingsdir is not None:
        timingsdir = Path.joinpath(Path.cwd(), args.timingsdir)
        files = glob('{}/**/*.json'.format(timingsdir), recursive=True)
        for filepath in files:
            with open(filepath) as f:
                data.append((json.load(f), filepath))

    plot(data, title)


if __name__ == "__main__":
    main()
