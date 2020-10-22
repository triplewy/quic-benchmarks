import argparse
import json
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

from matplotlib.ticker import StrMethodFormatter
from glob import glob
from pathlib import Path
from collections import defaultdict, deque
from scipy import stats


OMIT_HOSTS = ['survey.g.doubleclick.net',
              'googleads.g.doubleclick.net', 'www.google.com', 'adservice.google.com',
              'stats.g.doubleclick.net', 'www.google-analytics.com', 'www.googleadservices.com',
              'www.googletagmanager.com', 'bid.g.doubleclick.net', 'cx.atdmt.com']


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
    connections = {}
    # streams = defaultdict(list)
    max_time = 0
    max_host = None
    max_request = None
    tcp_sessions = set()
    tcp_connect_time = 0

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

                    connections[source_id] = {
                        'host': params['host'], 'start_time': event_time - start_time,
                        'first_request_time': math.inf, 'first_receive_time': math.inf,
                        'total_time': 0, 'streams': defaultdict(list)}

                if event_type == 'TCP_CONNECT' and phase == 'PHASE_BEGIN':
                    if start_time is None:
                        start_time = event_time

                    tcp_connect_time = event_time - start_time

                if event_type == 'HTTP2_SESSION':
                    connections[source_id] = {
                        'host': params['host'].split(':')[0], 'start_time': tcp_connect_time,
                        'first_request_time': math.inf, 'first_receive_time': math.inf,
                        'total_time': 0, 'streams': defaultdict(list)}

                if event_type == 'HTTP2_SESSION_SEND_HEADERS' or event_type == 'HTTP3_HEADERS_SENT':
                    tcp_sessions.add(source_id)
                    headers = params['headers']
                    host, path = get_host_path(headers)
                    host_path = host + path
                    short_path = '...{}'.format(
                        path[-20:]) if len(path) >= 20 else path
                    referrer = get_referrer(headers)
                    # if referrer is not None:
                    #     referrer_id = get_referrer_stream(referrer, streams)
                    # else:
                    #     referrer_id = None

                    connections[source_id]['first_request_time'] = min(
                        connections[source_id]['first_request_time'], event_time - start_time)

                    connections[source_id]['total_time'] = max(
                        connections[source_id]['total_time'], event_time - start_time)

                    connections[source_id]['streams'][params['stream_id']].append({
                        'path': host + short_path, 'full_path': host_path,
                        'data': [event_time - start_time]})

                if event_type == 'HTTP2_SESSION_RECV_PUSH_PROMISE':
                    h2_push_responses += 1

                if event_type == 'HTTP2_SESSION_RECV_DATA' or event_type == 'HTTP3_DATA_FRAME_RECEIVED':
                    if event_type == 'QUIC_SESSION_STREAM_FRAME_RECEIVED':
                        if params['stream_id'] % 2 != 0:
                            continue

                    connections[source_id]['streams'][params['stream_id']][-1]['data'].append(
                        event_time - start_time)

                    if event_type == 'HTTP2_SESSION_RECV_DATA':
                        total_size += params['size'] / 1024
                    else:
                        total_size += params['payload_length'] / 1024

                    full_path = connections[source_id]['streams'][params['stream_id']
                                                                  ][-1]['full_path']

                    if connections[source_id]['host'] not in OMIT_HOSTS:
                        if event_time - start_time > max_time:
                            max_time = event_time - start_time
                            max_host = connections[source_id]['host']
                            max_request = connections[source_id]['streams'][params['stream_id']
                                                                            ][-1]['full_path']

                    connections[source_id]['total_time'] = max(
                        connections[source_id]['total_time'], event_time - start_time)

                    connections[source_id]['first_receive_time'] = min(
                        connections[source_id]['first_receive_time'], event_time - start_time
                    )

                # if event_type == 'HTTP3_HEADERS_DECODED' or event_type == 'HTTP2_SESSION_RECV_HEADERS':
                #     headers = params['headers']
                #     for header in headers:
                #         if header.count('301') > 0:
                #             streams[params['stream_id']][-1]['301'] = True

    except Exception as e:
        print(filename, 'error', e)
        return None

    # print(total_size)

    print(max_time, max_host, max_request)
    # if filename.count('h2') > 0:
    #     final_tcp_sessions = []

    #     for source_id in tcp_sessions:
    #         final_tcp_sessions.append(connections[source_id])

    #     connections = final_tcp_sessions
    # else:
    #     connections = list(connections.values())

    return list(sorted(connections.values(), key=lambda x: x['start_time'])), max_time, filename.count('h2') == 0


def plot(h2_data, h3_data, graph_title):
    GREEN = deque(['#00FF00', '#008D00', '#005300', '#76FF00', '#24A547',
                   '#00FF00', '#008D00', '#005300', '#76FF00', '#24A547', ])

    fig, ax = plt.subplots(figsize=(12, 8))

    stream_order = []
    for streams_list in h3_data[0].values():
        for stream in streams_list:
            if '301' in stream:
                continue
            stream_order.append(stream)

    stream_order.sort(key=lambda x: x['data'][0], reverse=True)
    stream_order = [x['path'] for x in stream_order]

    for data in [h2_data, h3_data]:
        streams, connections, isH3 = data

        # all_streams = []
        # for streams_list in streams.values():
        #     all_streams += streams_list
        # all_streams.sort(key=lambda x: x['data'][0], reverse=True)

        all_streams = {}
        for streams_list in streams.values():
            for stream in streams_list:
                all_streams[stream['path']] = stream

        y_tick_labels = [None] * (len(stream_order) + 1)
        max_time = 0

        for i, stream_name in enumerate(stream_order):
            i = i + 1

            stream = all_streams[stream_name]

            if len(stream['data']) == 1 or '301' in stream:
                continue

            if isH3:
                send_color = '#8ACEEA'
                recv_color = 'blue'
                diff = 0.11
            else:
                send_color = '#DA90D5'
                recv_color = 'red'
                diff = -0.11

            plt.plot(stream['data'][:1], [i + diff],
                     color=recv_color, marker='o', markersize=5, linestyle='-', linewidth=0)
            plt.plot(stream['data'][:2], [i + diff, i + diff],
                     color=recv_color, marker='o', markersize=0, linestyle='-', linewidth=1)
            plt.plot(stream['data'][1:], [i + diff for _ in range(len(stream['data'][1:]))], color=recv_color, marker='|',
                     markersize=4, linestyle='-', linewidth=4)

            y_tick_labels[i] = stream['path']

            max_time = max(max_time, max(stream['data']))

        if isH3:
            color = 'blue'
        else:
            color = 'red'

        ax.axvline(max_time, color=color)
        plt.text(max_time + 1, len(y_tick_labels) - 3, '{} ms'.format(max_time),
                 rotation=-90, color=color, size=14)

        ax.tick_params(axis='y', which='major', labelsize=10)
        ax.tick_params(axis='y', which='minor', labelsize=10)

        ax.tick_params(axis='x', which='major', labelsize=18)
        ax.tick_params(axis='x', which='minor', labelsize=18)

    # formatter0 = StrMethodFormatter('{x:,g} kb')
    # ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    plt.yticks(np.array([i for i in range(len(y_tick_labels))]))
    ax.set_yticklabels(y_tick_labels)
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    plt.xticks(np.array([200, 400, 600, 800]))
    # plt.xlim(0, 1250)
    red_circle = mlines.Line2D([], [], color='red', marker='o', linestyle='None',
                               markersize=8, label='H2 Request Sent')
    red_line = mlines.Line2D([], [], color='red', marker='|', linestyle='None',
                             markersize=8, label='H2 Data Received')
    blue_circle = mlines.Line2D([], [], color='blue', marker='o', linestyle='None',
                                markersize=8, label='H3 Request Sent')
    blue_line = mlines.Line2D([], [], color='blue', marker='|', linestyle='None',
                              markersize=8, label='QUIC Stream Frame Received')

    legend = [
        red_circle,
        # red_line,
        mpatches.Patch(color='red', label='H2 Data Received'),
        blue_circle,
        # blue_line,
        mpatches.Patch(color='blue', label='H3 Data Received'),
    ]

    fig.tight_layout()
    plt.legend(handles=legend)
    plt.savefig(
        '{}/Desktop/graphs/{}'.format(Path.home(), graph_title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def plot_v2(conns: object, title: str):
    conns.sort(key=lambda x: x['start_time'], reverse=True)

    real_conns = []

    for conn in conns:
        if conn['host'] not in OMIT_HOSTS:
            real_conns.append(conn)

    conns = real_conns

    start_time = conns[-1]['start_time']

    captions = list(map(lambda x: x['host'], conns))
    captions.insert(0, '')

    fig, ax = plt.subplots(figsize=(16, 2))
    plt.yticks(np.arange(len(conns) + 1), captions)
    plt.ylim(0, len(conns) + 1)

    plt.xlabel('Time (ms)')
    # plt.legend(handles=[
    #     mpatches.Patch(color='green', label='connect', alpha=0.4),
    #     mpatches.Patch(color='purple', label='wait', alpha=0.2),
    #     mlines.Line2D([], [], color='gray', marker='o', linestyle='None',
    #                   markersize=8, label='Request Begin/End')
    #     # mpatches.Patch(color='yellow', label='wait'),
    #     # mpatches.Patch(color='magenta', label='receive')
    # ])

    max_image = (0, None)
    image_count = 0

    for i, entry in enumerate(conns):
        if i == len(conns) - 1:
            for streams in entry['streams'].values():
                for stream in streams:
                    if stream['full_path'] == 'careers.google.com/jobs/dist/js/main.en_US.min.1fb6bc645a33df65e5dc.js':
                        print(stream['data'][0], stream['data'][-1],
                              stream['data'][-1] - stream['data'][0])
            # print(entry['streams'])

        start = entry['start_time']
        end = entry['total_time']

        # connect, send, wait, receive, = itemgetter(
        #     'connect', 'send', 'wait', 'receive')(entry['timings'])

        y = i + 1
        xstart = (start - start_time)
        xstop = (end - start_time)

        # Total time
        plt.hlines(y, xstart, xstop, 'purple', lw=6, alpha=0.2)

        # Connect time: green
        plt.hlines(
            y, xstart, entry['first_request_time'], 'g', lw=6, alpha=0.4)

        # # Send time: cyan
        # plt.hlines(y, xstart, xstart + send, 'c', lw=4)
        # xstart += send

        # # Wait time: yellow
        # plt.hlines(y, entry['first_request_time'],
        #            entry['first_receive_time'], 'y', lw=6)

        # # Receive time: magenta
        # plt.hlines(y, xstart, xstart + receive, 'm', lw=4)
        # xstart += receive

        colors = [
            'tab:blue',
            'tab:orange',
            'tab:green',
            'tab:red',
            'tab:purple',
            'tab:pink',
            'tab:cyan',
            'tab:olive',
            'tab:brown',
        ]
        i = 0

        for streams in entry['streams'].values():
            for stream in streams:
                fp = stream['full_path']
                if fp.count('.png') + fp.count('.svg') + fp.count('.gif') + fp.count('.woff') + fp.count('.jpg') > 0:
                    image_count += 1
                    color = 'tab:cyan'

                    if stream['data'][-1] > max_image[0]:
                        max_image = (stream['data'][-1], fp)
                elif fp.count('.js') > 0:
                    color = 'tab:orange'
                elif fp.count('.css') > 0:
                    color = 'tab:pink'
                else:
                    # print(fp)
                    color = 'tab:brown'

                plt.plot(
                    [stream['data'][0], stream['data'][-1]],
                    [y, y],
                    marker='o',
                    markersize=8,
                    linewidth=2,
                    color=color
                )
                i += 1

    # print('image_count', image_count)
    # print('max_image', max_image)
    # plt.xlim(0, 2400)

    plt.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs/facebook_multi_medium_{}'.format(Path.home(), title), transparent=True)
    # plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    dirname = Path(args.dir)

    h2_data = []
    h3_data = []

    h2_final_connections = []
    h3_final_connections = []

    h2_start = []
    h2_end = []
    h2_duration = []
    h2_connect = []

    h3_start = []
    h3_end = []
    h3_duration = []
    h3_connect = []

    h2_lh3 = {'start': [], 'duration': []}
    h3_lh3 = {'start': [], 'duration': []}

    h2_google = {}
    h3_google = {}

    google_urls = [
        'careers.google.com/jobs/dist/js/main.en_US.min.f810219bb28efa8cc0d9.js',
    ]

    for url in google_urls:
        h2_google[url] = {'start': [], 'duration': []}
        h3_google[url] = {'start': [], 'duration': []}

    files = glob('{}/**/*.json'.format(dirname), recursive=True)
    files.sort()
    for i, netlog in enumerate(files):
        # if not (netlog == 'analysis/data/google_loss-1_multi_medium_v2/chrome_h2_7.json' or netlog == 'analysis/data/google_loss-1_multi_medium_v2/chrome_h3_3.json'):
        #     continue

        res = analyze_netlog(netlog)
        if res is None or res[1] == 0:
            continue

        conns = res[0]
        conns.sort(key=lambda x: x['start_time'])

        start = math.inf
        end = 0
        conn = conns[0]
        connect = conn['first_request_time'] - conn['start_time']

        if netlog.count('h2') > 0:
            h2_connect.append(connect)
        else:
            h3_connect.append(connect)

        if netlog.count('h2') > 0:
            h2_data.append(res)
            h2_final_connections.append(res[1])
        else:
            h3_data.append(res)
            h3_final_connections.append(res[1])

        for conn in conns:
            if conn['host'] == 'lh3.googleusercontent.com':
                if netlog.count('h2') > 0:
                    h2_lh3['start'].append(conn['start_time'])
                    h2_lh3['duration'].append(
                        conn['total_time'])
                else:
                    h3_lh3['start'].append(conn['start_time'])
                    h3_lh3['duration'].append(
                        conn['total_time'])

            for streams in conn['streams'].values():
                for stream in streams:
                    if stream['full_path'] in google_urls:
                        if netlog.count('h2') > 0:
                            facebook_obj = h2_google[stream['full_path']]
                        else:
                            facebook_obj = h3_google[stream['full_path']]

                        facebook_obj['start'].append(stream['data'][0])
                        facebook_obj['duration'].append(stream['data'][-1])

        plot_v2(res[0], 'h2' if netlog.count('h2') else 'h3')

    for thing in ['connect', 'lh3start', 'lh3duration']:
        if thing == 'connect':
            h2 = h2_connect
            h3 = h3_connect
        elif thing == 'start':
            h2 = h2_start
            h3 = h3_start
        elif thing == 'lh3start':
            h2 = h2_lh3['start']
            h3 = h3_lh3['start']
        elif thing == 'lh3duration':
            h2 = h2_lh3['duration']
            h3 = h3_lh3['duration']
        else:
            h2 = h2_duration
            h3 = h3_duration

        print(thing)
        ttest = stats.ttest_ind(
            h2,
            h3,
            equal_var=False
        )

        if ttest.pvalue >= 0.01:
            print('No diff')

        h2.sort()
        h3.sort()
        print('p50', np.median(h2),
              np.median(h3))
        print('p75', h2[int(len(h2) * 0.75)],
              h3[int(len(h2) * 0.75)])
        print('p90', h2[int(len(h2) * 0.9)],
              h3[int(len(h2) * 0.9)])
        print()

    for url in google_urls:
        for thing in ['start', 'duration']:
            h2 = h2_google[url][thing]
            h3 = h3_google[url][thing]

            ttest = stats.ttest_ind(
                h2,
                h3,
                equal_var=False
            )

            print(url, thing)
            if ttest.pvalue >= 0.01:
                print('No diff')

            h2.sort()
            h3.sort()
            print('p50', np.median(h2),
                np.median(h3))
            print('p75', h2[int(len(h2) * 0.75)],
                h3[int(len(h2) * 0.75)])
            print('p90', h2[int(len(h2) * 0.9)],
                h3[int(len(h2) * 0.9)])
            print()

    h2_final_connections.sort()
    h3_final_connections.sort()

    print('mean', np.mean(h2_final_connections), np.mean(h3_final_connections))
    print('std', np.std(h2_final_connections), np.std(h3_final_connections))
    print('p50', np.median(h2_final_connections),
          np.median(h3_final_connections))
    print('p75', h2_final_connections[int(len(h2_final_connections) * 0.75)],
          h3_final_connections[int(len(h3_final_connections) * 0.75)])
    print('p90', h2_final_connections[int(len(h2_final_connections) * 0.90)],
          h3_final_connections[int(len(h3_final_connections) * 0.90)])

    ttest = stats.ttest_ind(
        h2_final_connections,
        h3_final_connections,
        equal_var=False
    )

    diff = (np.mean(h2_final_connections) -
            np.mean(h3_final_connections)) / np.mean(h2_final_connections) * 100

    # accept null hypothesis
    if ttest.pvalue >= 0.01:
        print('No diff', diff)
    else:
        print('diff', diff)


if __name__ == "__main__":
    main()
