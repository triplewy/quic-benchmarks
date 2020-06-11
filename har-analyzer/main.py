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


def plot(title: str, page: str, entries: object):
    entries.sort(key=lambda x: x['startedDateTime'])
    size = page.split('/')[-2]
    numObjects = page.split('/')[-1].split('.')[0].split('-')[-1]

    start_time = datetime.strptime(
        entries[0]['startedDateTime'], ISO_8601_FORMAT)

    captions = list(map(lambda x: x['request']['url'].split('/')[-1], entries))
    captions.insert(0, '')

    fig = plt.figure()
    plt.title(title)
    plt.yticks(np.arange(len(entries) + 1), captions)
    plt.ylim(0, len(entries) + 1)

    if size == '10kb':
        if numObjects == '1':
            plt.xlim(0, 500)
        elif numObjects == '10':
            plt.xlim(0, 1500)
        elif numObjects == '100':
            plt.xlim(0, 5000)
    elif size == '100kb':
        if numObjects == '1':
            plt.xlim(0, 1000)
        elif numObjects == '10':
            plt.xlim(0, 5000)
        elif numObjects == '100':
            plt.xlim(0, 15000)
    elif size == '1000kb':
        if numObjects == '1':
            plt.xlim(0, 3000)
        elif numObjects == '10':
            plt.xlim(0, 10000)
        elif numObjects == '100':
            plt.xlim(0, 20000)

    plt.autoscale(False)
    plt.xlabel('Time (ms)')
    plt.legend(handles=[
        mpatches.Patch(color='green', label='connect'),
        mpatches.Patch(color='cyan', label='send'),
        mpatches.Patch(color='yellow', label='wait'),
        mpatches.Patch(color='magenta', label='receive')
    ])

    for i, entry in enumerate(entries):
        start = datetime.strptime(
            entry['startedDateTime'], ISO_8601_FORMAT)
        end = start + timedelta(milliseconds=entry['time'])
        connect, send, wait, receive, = itemgetter(
            'connect', 'send', 'wait', 'receive')(entry['timings'])

        y = i + 1
        xstart = (start - start_time) / timedelta(milliseconds=1)
        xstop = (end - start_time) / timedelta(milliseconds=1)

        # Total time
        plt.hlines(y, xstart, xstop, 'r', lw=8)
        # line_height = len(entries) / 40
        # plt.vlines(xstart, y+line_height, y-line_height, 'k', lw=2)
        # plt.vlines(xstop, y+line_height, y-line_height, 'k', lw=2)

        # Connect time: green
        if connect != -1:
            plt.hlines(y, xstart, xstart + connect, 'g', lw=8)
            xstart += connect

        # Send time: cyan
        plt.hlines(y, xstart, xstart + send, 'c', lw=8)
        xstart += send

        # Wait time: yellow
        plt.hlines(y, xstart, xstart + wait, 'y', lw=8)
        xstart += wait

        # Receive time: magenta
        plt.hlines(y, xstart, xstart + receive, 'm', lw=8)
        xstart += receive

    # plt.show()
    graph_dir = Path.joinpath(
        Path.home(), 'quic', 'graphs', size, numObjects, title)
    Path(graph_dir).mkdir(parents=True, exist_ok=True)

    graph_file = Path.joinpath(graph_dir, 'graph.png')
    if os.path.isfile(graph_file):
        os.remove(graph_file)

    fig.savefig(graph_file, dpi=fig.dpi)
    plt.close(fig=fig)


def populate_line_graph(host: str, urls: list, loss: int):
    xticks_pos = np.arange(len(urls))
    xtick_labels = urls
    plt.xticks(xticks_pos, xtick_labels, rotation=10)

    plt.legend(handles=[
        mpatches.Patch(color='red', label='Chrome H2'),
        mpatches.Patch(color='cyan', label='Chrome H3'),
        mpatches.Patch(color='orange', label='Firefox H2'),
        mpatches.Patch(color='blue', label='Firefox H3'),
        mpatches.Patch(color='magenta', label='Curl H2'),
        mpatches.Patch(color='yellow', label='Curl H3'),
        mpatches.Patch(color='green', label='Proxygen H3'),
    ], loc='upper left', bbox_to_anchor=(0., 1.02, 1., .102))
    plt.ylabel('Time (ms)')

    lines = defaultdict(list)
    y_max = 1

    for i, client in enumerate(['chrome', 'firefox', 'curl', 'hq']):
        har_dir = Path.joinpath(
            Path.home(), 'quic-benchmarks', 'browser', 'har', 'loss_{}'.format(loss), client)
        for j, url in enumerate(urls):
            for k, h in enumerate(['h2', 'h3']):
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
                color = 'y'
        elif client == 'hq':
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


def populate_graph(host: str, urls: list):
    xticks_pos = np.arange(len(urls))
    xtick_labels = urls

    for i, client in enumerate(['chrome', 'firefox', 'curl', 'hq']):
        har_dir = Path.joinpath(
            Path.home(), 'quic-benchmarks', 'browser', 'har', client)

        for j, url in enumerate(urls):

            for k, h in enumerate(['h2', 'h3']):
                filename = Path.joinpath(
                    har_dir, h, host, "{}.json".format(url))

                try:
                    with open(filename) as f:
                        data = json.load(f)
                        total_mean = np.mean(data['total'])

                        x = j + 0.16 * i + 0.08 * k
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
                                color = 'y'
                        elif client == 'hq':
                            if h == 'h2':
                                continue
                            else:
                                x -= 0.08
                                color = 'g'

                        plt.vlines(x, 0, total_mean, color, lw=10)
                        plt.errorbar(x, total_mean, yerr=np.std(
                            data['total']), lolims=True, uplims=True,
                            elinewidth=2, capsize=2, barsabove=True)

                except:
                    pass

    return xticks_pos, xtick_labels


def main():
    graph_dir = Path.joinpath(Path.home(), 'quic-benchmarks', 'graphs')
    Path(graph_dir).mkdir(parents=True, exist_ok=True)

    # FB KB 0% Loss
    fig = plt.figure(figsize=(12, 8))
    plt.title('Facebook 0% Loss')
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[:5], 0)
    fig.savefig(Path.joinpath(
        graph_dir, 'FB-{}-loss_{}'.format('KB', 0)), dpi=fig.dpi)
    plt.close(fig=fig)

    # FB MB 0% Loss
    fig = plt.figure(figsize=(10, 8))
    plt.title('Facebook 0% Loss')
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[5:], 0)
    fig.savefig(Path.joinpath(
        graph_dir, 'FB-{}-loss_{}'.format('MB', 0)), dpi=fig.dpi)
    plt.close(fig=fig)

    # FB KB 1% Loss
    fig = plt.figure(figsize=(12, 8))
    plt.title('Facebook 1% Loss')
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[:5], 1)
    fig.savefig(Path.joinpath(
        graph_dir, 'FB-{}-loss_{}'.format('KB', 1)), dpi=fig.dpi)
    plt.close(fig=fig)

    # FB MB 1% Loss
    fig = plt.figure(figsize=(10, 8))
    plt.title('Facebook 1% Loss')
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[5:], 1)
    fig.savefig(Path.joinpath(
        graph_dir, 'FB-{}-loss_{}'.format('MB', 1)), dpi=fig.dpi)
    plt.close(fig=fig)

    # FB KB 5% Loss
    fig = plt.figure(figsize=(12, 8))
    plt.title('Facebook 5% Loss')
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[:5], 5)
    fig.savefig(Path.joinpath(
        graph_dir, 'FB-{}-loss_{}'.format('KB', 5)), dpi=fig.dpi)
    plt.close(fig=fig)

    # FB MB 5% Loss
    fig = plt.figure(figsize=(10, 8))
    plt.title('Facebook 5% Loss')
    populate_line_graph('scontent.xx.fbcdn.net', fb_urls[5:], 5)
    fig.savefig(Path.joinpath(
        graph_dir, 'FB-{}-loss_{}'.format('MB', 5)), dpi=fig.dpi)
    plt.close(fig=fig)

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
