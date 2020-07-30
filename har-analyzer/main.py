import os
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from datetime import datetime, timedelta
from pathlib import Path
from operator import itemgetter
from termcolor import colored
from collections import defaultdict

ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

# http://www.softwareishard.com/blog/har-12-spec/#timings

fb_urls = [
    'speedtest-0B',
    'speedtest-1KB',
    'speedtest-10KB',
    'speedtest-100KB',
    'speedtest-500KB',
    'speedtest-1MB',
    'speedtest-2MB',
    'speedtest-5MB',
    'speedtest-10MB',
]

cf_urls = [
    '1MB.png',
    '5MB.png'
]

ms_urls = [
    '1MBfile.txt',
    '5000000.txt',
    '10000000.txt',
]

f5_urls = [
    '50000',
    '5000000',
    '10000000',
]

clients = ['chrome', 'firefox', 'curl', 'ngtcp2', 'proxygen']

graph_dir = Path.joinpath(Path.home(), 'quic-benchmarks', 'graphs')
Path(graph_dir).mkdir(parents=True, exist_ok=True)


def graph(loss: int, delay: int, bw: int, host: str):
    # KB graph
    fig = plt.figure(figsize=(12, 8))
    plt.title('loss-{}_delay-{}_bw-{}'.format(loss, delay, bw))
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[:5], loss, delay, bw)
    fig.savefig(Path.joinpath(
        graph_dir, '{}_loss-{}_delay-{}_bw-{}'.format('KB', loss, delay, bw)), dpi=fig.dpi)
    plt.close(fig=fig)

    # MB graph
    fig = plt.figure(figsize=(10, 8))
    plt.title('loss-{}_delay-{}_bw-{}'.format(loss, delay, bw))
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[5:], loss, delay, bw)
    fig.savefig(Path.joinpath(
        graph_dir, '{}_loss-{}_delay-{}_bw-{}'.format('MB', loss, delay, bw)), dpi=fig.dpi)
    plt.close(fig=fig)


def populate_line_graph(host: str, urls: list, loss: int, delay: int, bw: int):
    xticks_pos = np.arange(len(urls))
    xtick_labels = urls
    plt.xticks(xticks_pos, xtick_labels, rotation=10)

    plt.legend(handles=[
        mpatches.Patch(color='red', label='Chrome H2'),
        mpatches.Patch(color='cyan', label='Chrome H3'),
        # mpatches.Patch(color='orange', label='Firefox H2'),
        # mpatches.Patch(color='blue', label='Firefox H3'),
        mpatches.Patch(color='magenta', label='Curl H2'),
        mpatches.Patch(color='yellow', label='Ngtcp2 H3'),
        mpatches.Patch(color='green', label='Proxygen H3'),
    ], loc='upper left', bbox_to_anchor=(0., 1.02, 1., .102))
    plt.ylabel('Time (ms)')

    lines = defaultdict(list)
    y_max = 1

    for client in clients:

        har_dir = Path.joinpath(
            Path.home(),
            'quic-benchmarks',
            'browser',
            'har',
            'loss-{}_delay-{}_bw-{}'.format(loss, delay, bw),
            client
        )

        for url in urls:
            for h in ['h2', 'h3']:
                if client == 'firefox':
                    break
                filename = Path.joinpath(
                    har_dir, h, host, "{}.json".format(url))
                try:
                    with open(filename) as f:
                        data = json.load(f)
                        total_mean = np.mean(data['total'])
                        total_std = np.std(data['total'])
                        lines['{}-{}'.format(client, h)
                              ].append((total_mean, total_std))
                        y_max = max(y_max, total_mean)
                except:
                    pass

    # 10% buffer at top
    plt.ylim(1, y_max + y_max * 0.1)

    for k, v in lines.items():
        client = k.split('-')[0]
        h = k.split('-')[1]

        if client == 'chrome':
            if h == 'h2':
                color = 'r'
            else:
                color = 'c'
        elif client == 'firefox':
            if h == 'h2':
                color = '#ffa500'
            else:
                color = 'b'
        elif client == 'curl':
            if h == 'h2':
                color = 'm'
            else:
                continue
        elif client == 'ngtcp2':
            if h == 'h2':
                continue
            else:
                color = 'y'
        elif client == 'proxygen':
            if h == 'h2':
                continue
            else:
                color = 'g'

        plt.plot(
            xticks_pos,
            list(map(lambda x: x[0], v)),
            color=color,
            linestyle='--',
            marker='o'
        )

        for i, (mean, std) in enumerate(v):
            plt.errorbar(
                i,
                mean,
                yerr=std,
                ecolor=color,
                lolims=True,
                uplims=True,
                linewidth=0,
            )

    plt.show()


def main():
    # (loss, delay, bw)
    graphs = [
        (0, 0, 10),
        (0, 0, 5),
        (0, 0, 1),
        (1, 0, 10),
        (5, 0, 10),
        (10, 0, 10),
        (0, 200, 10),
        (0, 500, 10),
        (5, 200, 10)
    ]

    for loss, delay, bw in graphs:
        graph(loss, delay, bw, 'scontent.xx.fbcdn.net')

    # # Plot cloudflare
    # fig = plt.figure(figsize=(4, 6))
    # plt.title('Cloudflare')
    # plt.legend(handles=[
    #     mpatches.Patch(color='red', label='Chrome H2'),
    #     mpatches.Patch(color='cyan', label='Chrome H3'),
    #     mpatches.Patch(color='orange', label='Firefox H2'),
    #     mpatches.Patch(color='blue', label='Firefox H3'),
    #     mpatches.Patch(color='magenta', label='Curl H2'),
    #     mpatches.Patch(color='yellow', label='Curl H3'),
    #     mpatches.Patch(color='green', label='Proxygen H3'),
    # ], loc='upper left', bbox_to_anchor=(0., 1.02, 1., .102))
    # plt.ylabel('Time (ms)')
    # plt.ylim(1, 5000)

    # xtick_pos, xtick_labels = populate_graph(
    #     'cloudflare-quic.com', cf_urls)
    # plt.xticks(xtick_pos, xtick_labels, rotation=10)

    # plt.show()
    # fig.savefig(Path.joinpath(graph_dir, 'CF'), dpi=fig.dpi)
    # plt.close(fig=fig)

    # # Plot microsoft
    # fig = plt.figure(figsize=(6, 6))
    # plt.title('Microsoft')
    # plt.legend(handles=[
    #     mpatches.Patch(color='red', label='Chrome H2'),
    #     mpatches.Patch(color='cyan', label='Chrome H3'),
    #     mpatches.Patch(color='orange', label='Firefox H2'),
    #     mpatches.Patch(color='blue', label='Firefox H3'),
    #     mpatches.Patch(color='magenta', label='Curl H2'),
    #     mpatches.Patch(color='yellow', label='Curl H3'),
    #     mpatches.Patch(color='green', label='Proxygen H3'),
    # ], loc='upper left', bbox_to_anchor=(0., 1.02, 1., .102))
    # plt.ylabel('Time (ms)')
    # plt.ylim(1, 20000)

    # xtick_pos, xtick_labels = populate_graph(
    #     'quic.westus.cloudapp.azure.com', ms_urls)
    # plt.xticks(xtick_pos, xtick_labels, rotation=10)

    # plt.show()
    # fig.savefig(Path.joinpath(graph_dir, 'MS'), dpi=fig.dpi)
    # plt.close(fig=fig)

    # # Plot f5
    # fig = plt.figure(figsize=(6, 6))
    # plt.title('F5')
    # plt.legend(handles=[
    #     mpatches.Patch(color='red', label='Chrome H2'),
    #     mpatches.Patch(color='cyan', label='Chrome H3'),
    #     mpatches.Patch(color='orange', label='Firefox H2'),
    #     mpatches.Patch(color='blue', label='Firefox H3'),
    #     mpatches.Patch(color='magenta', label='Curl H2'),
    #     mpatches.Patch(color='yellow', label='Curl H3'),
    #     mpatches.Patch(color='green', label='Proxygen H3'),
    # ], loc='upper left', bbox_to_anchor=(0., 1.02, 1., .102))
    # plt.ylabel('Time (ms)')
    # plt.ylim(1, 25000)

    # xtick_pos, xtick_labels = populate_graph(
    #     'f5quic.com:4433', f5_urls)
    # plt.xticks(xtick_pos, xtick_labels, rotation=10)

    # plt.show()
    # fig.savefig(Path.joinpath(graph_dir, 'F5'), dpi=fig.dpi)
    # plt.close(fig=fig)


if __name__ == "__main__":
    main()
