import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

from matplotlib.ticker import StrMethodFormatter
from datetime import datetime, timedelta
from pathlib import Path
from operator import itemgetter
from termcolor import colored
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

# http://www.softwareishard.com/blog/har-12-spec/#timings

G = nx.Graph()


def get_start_cdf(entries: list):
    entries.sort(key=lambda x: x['_requestTime'])
    start = float(entries[0]['_requestTime'])

    x = [(float(entry['_requestTime']) - start) * 1000 for entry in entries]
    y = [(i + 1) * 100 / len(entries) for i in range(len(entries))]

    return x, y, entries[0]['response']['httpVersion']


def get_end_cdf(entries: list):
    entries.sort(key=lambda x: x['_requestTime'])
    start = float(entries[0]['_requestTime']) * 1000

    entries.sort(key=lambda x: float(
        x['_requestTime']) * 1000 + float(x['time']))

    x = [float(entry['_requestTime']) * 1000 + float(entry['time']) -
         start for entry in entries]
    y = [(i + 1) * 100 / len(entries) for i in range(len(entries))]

    return x, y, entries[0]['response']['httpVersion']


def plot_cdf(cdfs: list):
    fig, ax = plt.subplots(figsize=(10, 6))

    for (x, y, name) in cdfs:
        if name == 'h3-29':
            color = 'blue'
        else:
            color = 'red'

        plt.plot(
            x,
            y,
            color=color,
            linestyle='-',
            linewidth=1,
            markersize=0,
        )

    ax.tick_params(axis='both', which='major', labelsize=18)
    ax.tick_params(axis='both', which='minor', labelsize=18)

    formatter0 = StrMethodFormatter('{x:,g}%')
    ax.yaxis.set_major_formatter(formatter0)

    formatter1 = StrMethodFormatter('{x:,g} ms')
    ax.xaxis.set_major_formatter(formatter1)

    # plt.yticks(np.array([0, 250, 500, 750, 1000]))
    # plt.xticks(np.array([1000, 3000, 5000, 7000]))
    # plt.xticks(np.array([0, 500, 1000, 1500, 2000, 2500, 3000]))
    fig.tight_layout()
    # plt.savefig(
    #     '{}/Desktop/graphs/{}'.format(Path.home(), graph_title), transparent=True)
    # plt.legend(handles=legend)
    plt.show()
    plt.close(fig=fig)


def plot(entries: object):
    entries.sort(key=lambda x: x['_requestTime'] * 1000)

    start_time = entries[0]['_requestTime'] * 1000

    captions = list(map(lambda x: urlparse(
        x['request']['url']).hostname, entries))
    captions.insert(0, '')

    fig, ax = plt.subplots(figsize=(12, 6))
    plt.yticks(np.arange(len(entries) + 1), captions)
    plt.ylim(0, len(entries) + 1)

    plt.xlabel('Time (ms)')
    plt.legend(handles=[
        mpatches.Patch(color='green', label='connect'),
        mpatches.Patch(color='cyan', label='send'),
        mpatches.Patch(color='yellow', label='wait'),
        mpatches.Patch(color='magenta', label='receive')
    ])

    for i, entry in enumerate(entries):
        start = entry['_requestTime'] * 1000
        end = start + entry['time']
        connect, send, wait, receive, = itemgetter(
            'connect', 'send', 'wait', 'receive')(entry['timings'])

        y = i + 1
        xstart = (start - start_time)
        xstop = (end - start_time)

        # Total time
        plt.hlines(y, xstart, xstop, 'r', lw=4)

        # Connect time: green
        if connect != -1:
            plt.hlines(y, xstart, xstart + connect, 'g', lw=4)
            xstart += connect

        # Send time: cyan
        plt.hlines(y, xstart, xstart + send, 'c', lw=4)
        xstart += send

        # Wait time: yellow
        plt.hlines(y, xstart, xstart + wait, 'y', lw=4)
        xstart += wait

        # Receive time: magenta
        plt.hlines(y, xstart, xstart + receive, 'm', lw=4)
        xstart += receive

    fig.tight_layout()
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    hardir = Path(args.dir)

    start_cdfs = []
    end_cdfs = []

    for name in ['chrome_h3.json']:
        reverse_deps = {}
        dependencies = {}
        callstacks = {}
        start_time = None

        filename = Path.joinpath(hardir, name)

        with open(filename) as f:
            data = json.load(f)
            # for entries in data:
            #     print(len(entries))
            # start_cdfs.append(get_start_cdf(entries))
            # end_cdfs.append(get_end_cdf(entries))

            # start_time = datetime.strptime(
            #     entries[0]['startedDateTime'], ISO_8601_FORMAT)

            # end_time = datetime.strptime(
            #     entries[-1]['startedDateTime'], ISO_8601_FORMAT)
            # end_time += timedelta(milliseconds=entries[-1]['time'])

            # total_time = end_time - start_time
            # print(colored("Filename: {}, Total time: {} ms".format(filename,
            #                                                        total_time / timedelta(milliseconds=1)), "green"))

            # plot(entries)

            # break

            har = data[0]

            print(len(har))

            for entry in har:
                req = entry['request']
                url = req['url']
                initiator = json.loads(entry['_initiator_detail'])

                if start_time is None:
                    start_time = entry['_requestTime'] * 1000

                requestTime = entry['_requestTime'] * 1000 - start_time
                endTime = requestTime + entry['time']

                if initiator['type'] == 'parser':
                    initiator_url = initiator['url']

                    G.add_edge(initiator_url, url)

                    parent = dependencies[initiator_url]
                    parent['children'].append(url)

                    if url not in dependencies:
                        dependencies[url] = {
                            'level': parent['level'] + 1, 'children': [], '_requestTime': requestTime, '_endTime': endTime, 'callstack': []}

                    reverse_deps[url] = initiator_url
                    callstacks[url] = [initiator_url]

                elif initiator['type'] == 'script':
                    scripts = set()
                    for frame in initiator['stack']['callFrames']:
                        scripts.add(frame['url'])

                    print('callstack', len(scripts))
                    initiator_url = initiator['stack']['callFrames'][-1]['url']

                    G.add_edge(initiator_url, url)

                    parent = dependencies[initiator_url]
                    parent['children'].append(url)

                    if url not in dependencies:
                        dependencies[url] = {
                            'level': parent['level'] + 1, 'children': [], '_requestTime': requestTime, '_endTime': endTime, 'callstack': list(scripts)}

                    reverse_deps[url] = initiator_url
                    callstacks[url] = list(scripts)

                elif initiator['type'] == 'other':
                    G.add_node(url)
                    dependencies[url] = {'level': 0,
                                         'children': [], '_requestTime': requestTime, '_endTime': endTime, 'callstack': []}
                    reverse_deps[url] = ''
                    callstacks[url] = []
                else:
                    print(req['url'], initiator)

                    reverse_deps[url] = ''
                    callstacks[url] = []

            print(reverse_deps)
            dependencies_list = sorted(
                list(dependencies.items()), key=lambda x: len(x[1]['children']), reverse=True)

            for dep in dependencies_list[:5]:
                print(dep[0], dep[1]['level'], dep[1]
                      ['_requestTime'], len(dep[1]['children']))

            dependencies_list = sorted(
                list(dependencies.items()), key=lambda x: x[1]['_endTime'], reverse=True)

            for dep in dependencies_list[:5]:
                print(dep)

            print()
            last = 'https://connect.facebook.net/signals/config/486822841454810?v=2.9.27&r=stable'
            print(last, callstacks[last])
            while reverse_deps[last] != '':
                print(reverse_deps[last], callstacks[reverse_deps[last]])
                last = reverse_deps[last]
            # print(dependencies_list)
            # plot_cdf(start_cdfs)
            # plot_cdf(end_cdfs)
            # fig, ax = plt.subplots(figsize=(14, 10))
            # nx.draw(G, with_labels=True)
            # fig.tight_layout()
            # plt.show()


if __name__ == "__main__":
    main()
