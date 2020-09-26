import argparse
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from matplotlib.ticker import StrMethodFormatter
from glob import glob
from pathlib import Path
from collections import defaultdict, deque


def get_referrer_stream(referrer: str, streams: dict):
    for key, value in streams.items():
        print(referrer, value['path'])
        if referrer.count(value['path']) > 0:
            return key

    return None


def get_referrer(headers) -> str:
    referrer = None
    for header in headers:
        if header.count('referrer') > 0:
            referrer = header.split()[1]
            return referrer

    return None


def get_host_path(headers) -> str:
    host = None
    path = None

    for header in headers:
        if header.count('authority') > 0:
            host = header.split()[1]
        if header.count('path') > 0:
            path = header.split()[1]

        if host is not None and path is not None:
            return host, path

    print('No authority and path found')
    raise 'No authority and path found'


def analyze_netlog(filename):
    print(filename)

    connections = []
    streams = defaultdict(list)
    max_time = 0

    try:
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

            h2_push_responses = 0

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

                if event_type == 'QUIC_SESSION' and phase == 'PHASE_BEGIN':
                    if start_time is None:
                        start_time = event_time

                    connections.append(
                        {'host': params['host'], 'time': event_time - start_time if event_time - start_time > 0 else 2})

                if event_type == 'TCP_CONNECT' and phase == 'PHASE_BEGIN':
                    if start_time is None:
                        start_time = event_time

                    connections.append(
                        {'time': event_time - start_time if event_time - start_time > 0 else 2})

                if event_type == 'HTTP2_SESSION_SEND_HEADERS' or event_type == 'HTTP3_HEADERS_SENT':
                    headers = params['headers']
                    host, path = get_host_path(headers)
                    host_path = host + path
                    short_path = '...{}'.format(
                        path[-20:]) if len(path) >= 20 else path
                    referrer = get_referrer(headers)
                    if referrer is not None:
                        referrer_id = get_referrer_stream(referrer, streams)
                    else:
                        referrer_id = None

                    streams[params['stream_id']].append({
                        'path': host + short_path, 'full_path': host_path, referrer_id: referrer_id,
                        'data': [event_time - start_time]})

                if event_type == 'HTTP2_SESSION_RECV_PUSH_PROMISE':
                    h2_push_responses += 1

                if event_type == 'HTTP2_SESSION_RECV_DATA' or event_type == 'QUIC_SESSION_STREAM_FRAME_RECEIVED':
                    if event_type == 'QUIC_SESSION_STREAM_FRAME_RECEIVED':
                        if params['stream_id'] % 2 != 0:
                            continue

                    streams[params['stream_id']][-1]['data'].append(
                        event_time - start_time)
                    if event_type == 'HTTP2_SESSION_RECV_DATA':
                        total_size += params['size'] / 1024
                    else:
                        total_size += params['length'] / 1024

                    max_time = max(max_time, event_time - start_time)

            print(filename, h2_push_responses)

    except Exception as e:
        print('error', e)
        return None

    print(max_time)
    return streams, connections, filename.count('h2') == 0


def plot(data, graph_title):
    GREEN = deque(['#00FF00', '#008D00', '#005300', '#76FF00', '#24A547',
                   '#00FF00', '#008D00', '#005300', '#76FF00', '#24A547', ])

    fig, ax = plt.subplots(figsize=(12, 6))

    streams, connections, isH3 = data[0]

    all_streams = []
    for streams_list in streams.values():
        all_streams += streams_list

    all_streams.sort(key=lambda x: x['data'][0])

    y_tick_labels = [None] * (len(all_streams) + 1)

    for i, stream in enumerate(all_streams):
        print(stream)
        i = i + 1

        if len(stream['data']) == 1:
            continue

        plt.plot(stream['data'][:2], [i, i],
                 color='b', marker='|', markersize=6, linestyle='-', linewidth=1)

        plt.plot(stream['data'][1:], [i for _ in range(len(stream['data'][1:]))], color='r', marker='|',
                 markersize=10, linestyle='-', linewidth=2)

        y_tick_labels[i] = stream['path']

    for i, conn in enumerate(connections):
        ax.axvline(conn['time'], color=GREEN.popleft())

    ax.tick_params(axis='x', which='major', labelsize=18)
    ax.tick_params(axis='x', which='minor', labelsize=18)

    # formatter0 = StrMethodFormatter('{x:,g} kb')
    # ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    plt.yticks(np.array([i for i in range(len(y_tick_labels))]))
    ax.set_yticklabels(y_tick_labels)
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    plt.xticks(np.array([0, 250, 500, 750, 1000, 1250]))
    plt.xlim(0, 1250)

    fig.tight_layout()
    plt.title('H3' if isH3 else 'H2')
    # plt.legend(handles=legend)
    plt.savefig(
        '{}/Desktop/graphs/{}'.format(Path.home(), graph_title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    dirname = Path(args.dir)

    h2_data = []
    h3_data = []

    files = glob('{}/**/*.json'.format(dirname), recursive=True)
    files.sort()
    for i, netlog in enumerate(files):
        # if netlog.split('.')[0][-1] > '4':
        #     continue
        res = analyze_netlog(netlog)
        if res is None:
            continue

        if netlog.count('h2') > 0:
            # h2_data.append(res)
            plot([res], '{}_h2_{}_netlog_analysis'.format(
                args.dir.split('/')[-1], i))
        else:
            # h3_data.append(res)
            plot([res], '{}_h3_{}_netlog_analysis'.format(
                args.dir.split('/')[-1], i))

    # plot(h2_data, '{}_h2_netlog_analysis'.format(args.dir.split('/')[-1]))
    # plot(h3_data, '{}_h3_netlog_analysis'.format(args.dir.split('/')[-1]))


if __name__ == "__main__":
    main()
