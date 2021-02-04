import argparse
import json
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import random

from matplotlib.ticker import StrMethodFormatter
from glob import glob
from pathlib import Path
from collections import defaultdict, deque
from scipy import stats

COLORS = deque(['blue', 'green', 'gray', 'orange', 'purple', 'lime', 'pink', 'teal', '#441dfd', '#0b1667',
                '#f908f4', '#8a3f1b', '#fcd2bc', '#b5972b', '#c5ffae', '#ec6f99', '#8cac9a', '#ad5ad8', '#313d8a', '#6a700d'])


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
                        'host': params['host'],
                        'start_time': event_time - start_time,
                        'total_time': 0,
                        'streams': defaultdict(list),
                        'frame': 0
                    }

                if event_type == 'TCP_CONNECT' and phase == 'PHASE_BEGIN':
                    if start_time is None:
                        start_time = event_time

                    tcp_connect_time = event_time - start_time

                if event_type == 'HTTP2_SESSION':
                    connections[source_id] = {
                        'host': params['host'].split(':')[0],
                        'start_time': tcp_connect_time,
                        'total_time': 0,
                        'streams': defaultdict(list),
                        'frame': 0
                    }

                if event_type == 'HTTP2_SESSION_SEND_HEADERS' or event_type == 'HTTP3_HEADERS_SENT':
                    headers = params['headers']
                    host, path = get_host_path(headers)
                    host_path = host + path
                    short_path = '...{}'.format(
                        path[-20:]) if len(path) >= 20 else path
                    referrer = get_referrer(headers)

                    connections[source_id]['total_time'] = max(
                        connections[source_id]['total_time'], event_time - start_time)

                    connections[source_id]['streams'][params['stream_id']].append({
                        'path': host + short_path,
                        'full_path': host_path,
                        'start_time': event_time - start_time,
                        'data': []
                    })

                if event_type == 'HTTP2_SESSION_RECV_DATA' or event_type == 'HTTP3_DATA_FRAME_RECEIVED':
                    if event_type == 'HTTP2_SESSION_RECV_DATA':
                        size = params['size']
                    else:
                        size = params['payload_length']

                    connections[source_id]['streams'][params['stream_id']][-1]['data'].append({
                        'time': event_time - start_time,
                        'frame': connections[source_id]['frame'],
                        'size': size,
                        'path': connections[source_id]['streams'][params['stream_id']][-1]['full_path']
                    })

                    connections[source_id]['frame'] += 1

    except Exception as e:
        print(filename, 'error', e)
        return None

    return list(sorted(connections.values(), key=lambda x: x['start_time']))


def plot(conns, graph_title, **kwargs):
    fig, ax = plt.subplots(figsize=(10, 4))

    ax.set_xlabel('Total Size', fontsize=18, labelpad=10)

    for conn in conns:
        if 'host' in kwargs and kwargs['host'] is not None and conn['host'] != kwargs['host']:
            continue

        streams = conn['streams']

        min_frame = math.inf
        all_frames = []
        all_streams = []
        for streams_list in streams.values():
            for stream in streams_list:
                if len(stream['data']) <= 1 or '301' in stream:
                    continue
                # if stream['full_path'].count('png') == 0 \
                #         and stream['full_path'].count('gif') == 0 \
                #         and stream['full_path'].count('jpeg') == 0:
                #     continue

                all_streams.append(stream)
                all_frames += stream['data']

                min_frame = min(min_frame, min(
                    [x['frame'] for x in stream['data']]))

        all_streams.sort(key=lambda x: x['start_time'])
        all_frames.sort(key=lambda x: x['frame'])

        print(len(all_streams))

        min_req_data_time = math.inf
        max_req_data_time = -math.inf
        max_req_data_frame_no = -math.inf
        max_req_data_frame_size = 0

        start_time = None
        end_time = None

        total_size = 0

        colors = {}

        for frame in all_frames:
            size = frame['size']
            full_path = frame['path']

            if full_path.count('image8-3.png') > 0:
                color = 'red'
            else:
                if full_path in colors:
                    color = colors[full_path]
                else:
                    color = "#%06x" % random.randint(0, 0xFFFFFF)
                    # color = COLORS.popleft()
                    colors[full_path] = color

            plt.scatter([total_size / 1024], [0.3],
                        color=color, marker='|', s=200, linewidth=4 if graph_title.count('h3') > 0 else 3)

            total_size += size

        # for stream in all_streams:
        #     req_path = stream['full_path']
        #     req_data = stream['data']
        #     req_data_times = [x['time'] for x in req_data]
        #     req_data_frame_nos = [x['frame'] - min_frame for x in req_data]

        #     min_req_data_time = min(min_req_data_time, min(req_data_times))
        #     max_req_data_time = max(max_req_data_time, max(req_data_times))
        #     max_req_data_frame_no = max(
        #         max_req_data_frame_no, max(req_data_frame_nos))

        #     # color = "#%06x" % random.randint(0, 0xFFFFFF)

        #     if req_path.count('image8-3.png') > 0:
        #         start_time = stream['start_time']
        #         end_time = max(req_data_times)
        #         color = 'red'
        #     else:
        #         if req_path in colors:
        #             color = colors[req_path]
        #         else:
        #             color = "#%06x" % random.randint(0, 0xFFFFFF)
        #             # color = COLORS.popleft()
        #             colors[req_path] = color

        #     if min(req_data_frame_nos) == 0:
        #         y = 4
        #     elif req_path.count('.css') > 0:
        #         y = 3
        #     elif req_path.count('.js') > 0:
        #         y = 1
        #     else:
        #         y = 2

        #     plt.scatter([stream['start_time']], [y], marker='o', s=100,
        #                 facecolors='none', edgecolors=color, linewidth=3)
        #     plt.scatter(req_data_times, [y] * len(req_data),
        #                 color=color, marker='|', s=100, linewidth=5)
        #     # plt.scatter(req_data_frame_nos, [0.3] * len(req_data),
        #     #             color=color, marker='|', s=200, linewidth=4 if graph_title.count('h3') > 0 else 1.8)

    print('Resources:', len(all_streams))
    ax.tick_params(axis='x', which='major', labelsize=18)
    ax.tick_params(axis='x', which='minor', labelsize=18)

    # Hide the right and top spines
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    # # Only show ticks on the bottom spines
    ax.xaxis.set_ticks_position('bottom')

    # plt.xlim(0, 3000)
    plt.ylim(0, 6)
    plt.yticks([])
    ax.set_yticklabels([])
    # ax.vlines(1853.219, 0, 4)

    legend = [
        mpatches.Patch(
            color='red', label='Main image')
    ]

    formatter0 = StrMethodFormatter('{x:,g} KB')
    ax.xaxis.set_major_formatter(formatter0)

    plt.title('H3' if graph_title.count('h3') >
              0 else 'H2', fontsize=18, fontweight='bold', y=0.63)
    fig.tight_layout()
    plt.rcParams["legend.fontsize"] = 14
    plt.legend(handles=legend)
    plt.savefig(
        '{}/Desktop/graphs_revised/{}'.format(Path.home(), graph_title), transparent=True)
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--netlog")
    parser.add_argument("--host")
    parser.add_argument("--title")

    args = parser.parse_args()

    netlog = Path(args.netlog)
    host = args.host
    title = args.title

    conns = analyze_netlog(str(netlog))

    plot(
        conns, f'{title}_{"h3" if str(netlog).count("h3") > 0 else "h2"}', host=host)


if __name__ == "__main__":
    main()
#
