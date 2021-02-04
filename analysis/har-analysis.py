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
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

# http://www.softwareishard.com/blog/har-12-spec/#timings

G = nx.Graph()


def plot(h2, h3):
    for h in [h2, h3]:
        fig, ax = plt.subplots(figsize=(12, 4))

        data, dclt, pagelt = h

        data.sort(key=lambda x: x['_requestTime'])

        domains = defaultdict(list)

        for resource in data:
            url_obj = urlparse(resource['request']['url'])
            domains[url_obj.netloc].append(resource)

        items = sorted(list(domains.items()),
                       key=lambda x: x[1][0]['_requestTime'], reverse=True)

        i = 1

        for d, entries in domains.items():
            ax.scatter([entries[0]['_requestTime'], entries[-1]
                        ['_requestTime'] + entries[-1]['time']], [i] * 2)

            i += 1

        plt.vlines([dclt, pagelt], 0, len(domains) + 1)
        plt.yticks(np.arange(len(domains) + 1), [''] + list(domains.keys()))
        plt.ylim(0, len(domains) + 1)
        plt.xlabel('Time (ms)')
        # plt.legend(handles=[
        #     mpatches.Patch(color='green', label='connect'),
        #     mpatches.Patch(color='cyan', label='send'),
        #     mpatches.Patch(color='yellow', label='wait'),
        #     mpatches.Patch(color='magenta', label='receive')
        # ])

        fig.tight_layout()
        plt.show()
        plt.close(fig=fig)


def analyze_wprofx(filename):
    resources = []
    h3 = 0
    h3_transfer_size = 0

    non_h3 = 0
    non_h3_transfer_size = 0

    html = 0
    html_transfer_size = 0
    html_transfer_size_h3 = 0

    css = 0
    css_transfer_size = 0
    css_transfer_size_h3 = 0

    js = 0
    js_transfer_size = 0
    js_transfer_size_h3 = 0

    image = 0
    image_transfer_size = 0
    image_transfer_size_h3 = 0

    misc = 0
    misc_transfer_size = 0
    misc_transfer_size_h3 = 0

    total_transfer_size = 0

    with open(filename) as f:
        out = json.load(f)
        dclt = out['domContentLoadedEventEnd']
        plt = out['loadEventEnd']
        loading = list(out['loading'].values())
        loading.sort(key=lambda x: x['endTime'] - x['startTime'], reverse=True)

        har = out['entries']
        har.sort(key=lambda x: x['_requestTime'])

        start = None

        for entry in har:
            start_time = entry['_requestTime'] * 1000

            if start is None:
                start = start_time

            start_time -= start
            entry['_requestTime'] = start_time
            elapsed_time = entry['time']
            transfer_size = entry['response']['_transferSize']

            total_transfer_size += transfer_size

            is_h3 = False

            if entry['response']['httpVersion'].count('h3') > 0:
                h3 += 1
                h3_transfer_size += transfer_size
                is_h3 = True
            else:
                non_h3 += 1
                non_h3_transfer_size += transfer_size

            mime_type = entry['response']['content']['mimeType']

            if mime_type.count('javascript') > 0:
                js += 1
                js_transfer_size += transfer_size
                if is_h3:
                    js_transfer_size_h3 += transfer_size

            elif mime_type.count('html') > 0:
                html += 1
                html_transfer_size += transfer_size
                if is_h3:
                    html_transfer_size_h3 += transfer_size

            elif mime_type.count('css') > 0:
                css += 1
                css_transfer_size += transfer_size
                if is_h3:
                    css_transfer_size_h3 += transfer_size

            elif mime_type.count('image') > 0:
                image += 1
                image_transfer_size += transfer_size
                if is_h3:
                    image_transfer_size_h3 += transfer_size

            else:
                misc += 1
                misc_transfer_size += transfer_size
                if is_h3:
                    misc_transfer_size_h3 += transfer_size

            # if start_time + elapsed_time < plt:
            resources.append(entry)

    print(f'{h3} / {h3 + non_h3} h3 resources')
    print(f'{h3_transfer_size} / {h3_transfer_size + non_h3_transfer_size} h3 transferred bytes')

    print(f'HTML: {html_transfer_size_h3} / {html_transfer_size}, {html_transfer_size_h3 / html_transfer_size}')
    print(
        f'CSS: {css_transfer_size_h3} / {css_transfer_size}, {css_transfer_size_h3 / css_transfer_size}')
    print(
        f'JS: {js_transfer_size_h3} / {js_transfer_size}, {js_transfer_size_h3 / js_transfer_size}')
    if image_transfer_size > 0:
        print(
            f'Image: {image_transfer_size_h3} / {image_transfer_size}, {image_transfer_size_h3 / image_transfer_size}')
    if misc_transfer_size > 0:
        print(
            f'Misc: {misc_transfer_size_h3} / {misc_transfer_size}, {misc_transfer_size_h3 / misc_transfer_size}')

    return resources, dclt, plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--h2')
    parser.add_argument('--h3')

    args = parser.parse_args()

    h2 = Path(args.h2)
    h3 = Path(args.h3)

    h2_res = analyze_wprofx(h2)
    h3_res = analyze_wprofx(h3)

    resources_dict = {}

    for res in [h2_res[0], h3_res[0]]:
        for entry in res:
            url = entry['request']['url']
            start_time = entry['_requestTime']
            elapsed_time = entry['time']

            if url in resources_dict:
                resources_dict[url]['h3'] = {
                    'start_time': start_time, 'end_time': start_time + elapsed_time}
            else:
                resources_dict[url] = {
                    'h2': {'start_time': start_time, 'end_time': start_time + elapsed_time}}

    print(h2_res[2], h3_res[2])

    total = 0
    h3_fast = 0

    for k, v in resources_dict.items():
        if 'h2' not in v or 'h3' not in v:
            continue

        h2 = v['h2']
        h3 = v['h3']

        # ignore if end time ends after plt
        if h2['end_time'] > h2_res[2] or h3['end_time'] > h3_res[2]:
            continue

        if h3['end_time'] < h2['end_time']:
            print(k, h2['end_time'], h3['end_time'])
            h3_fast += 1

        total += 1

    print(f'{h3_fast} / {total}: {h3_fast / total * 100}')
    plot(h2_res, h3_res)

    # for name in ['chrome_h3.json']:
    #     reverse_deps = {}
    #     dependencies = {}
    #     callstacks = {}
    #     start_time = None

    #     filename = Path.joinpath(hardir, name)

    #     with open(filename) as f:
    #         data = json.load(f)

    #         har = data[0]

    #         print(len(har))

    #         for entry in har:
    #             req = entry['request']
    #             url = req['url']
    #             initiator = json.loads(entry['_initiator_detail'])

    #             if start_time is None:
    #                 start_time = entry['_requestTime'] * 1000

    #             requestTime = entry['_requestTime'] * 1000 - start_time
    #             endTime = requestTime + entry['time']

    #             if initiator['type'] == 'parser':
    #                 initiator_url = initiator['url']

    #                 G.add_edge(initiator_url, url)

    #                 parent = dependencies[initiator_url]
    #                 parent['children'].append(url)

    #                 if url not in dependencies:
    #                     dependencies[url] = {
    #                         'level': parent['level'] + 1, 'children': [], '_requestTime': requestTime, '_endTime': endTime, 'callstack': []}

    #                 reverse_deps[url] = initiator_url
    #                 callstacks[url] = [initiator_url]

    #             elif initiator['type'] == 'script':
    #                 scripts = set()
    #                 for frame in initiator['stack']['callFrames']:
    #                     scripts.add(frame['url'])

    #                 print('callstack', len(scripts))
    #                 initiator_url = initiator['stack']['callFrames'][-1]['url']

    #                 G.add_edge(initiator_url, url)

    #                 parent = dependencies[initiator_url]
    #                 parent['children'].append(url)

    #                 if url not in dependencies:
    #                     dependencies[url] = {
    #                         'level': parent['level'] + 1, 'children': [], '_requestTime': requestTime, '_endTime': endTime, 'callstack': list(scripts)}

    #                 reverse_deps[url] = initiator_url
    #                 callstacks[url] = list(scripts)

    #             elif initiator['type'] == 'other':
    #                 G.add_node(url)
    #                 dependencies[url] = {'level': 0,
    #                                      'children': [], '_requestTime': requestTime, '_endTime': endTime, 'callstack': []}
    #                 reverse_deps[url] = ''
    #                 callstacks[url] = []
    #             else:
    #                 print(req['url'], initiator)

    #                 reverse_deps[url] = ''
    #                 callstacks[url] = []

    #         print(reverse_deps)
    #         dependencies_list = sorted(
    #             list(dependencies.items()), key=lambda x: len(x[1]['children']), reverse=True)

    #         for dep in dependencies_list[:5]:
    #             print(dep[0], dep[1]['level'], dep[1]
    #                   ['_requestTime'], len(dep[1]['children']))

    #         dependencies_list = sorted(
    #             list(dependencies.items()), key=lambda x: x[1]['_endTime'], reverse=True)

    #         for dep in dependencies_list[:5]:
    #             print(dep)

    #         print()
    #         last = 'https://connect.facebook.net/signals/config/486822841454810?v=2.9.27&r=stable'
    #         print(last, callstacks[last])
    #         while reverse_deps[last] != '':
    #             print(reverse_deps[last], callstacks[reverse_deps[last]])
    #             last = reverse_deps[last]
    # print(dependencies_list)
    # plot_cdf(start_cdfs)
    # plot_cdf(end_cdfs)
    # fig, ax = plt.subplots(figsize=(14, 10))
    # nx.draw(G, with_labels=True)
    # fig.tight_layout()
    # plt.show()


if __name__ == '__main__':
    main()
