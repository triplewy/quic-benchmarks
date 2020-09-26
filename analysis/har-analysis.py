import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from matplotlib.ticker import StrMethodFormatter
from datetime import datetime, timedelta
from pathlib import Path
from operator import itemgetter
from termcolor import colored
from pathlib import Path

ISO_8601_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

# http://www.softwareishard.com/blog/har-12-spec/#timings


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
    entries.sort(key=lambda x: x['startedDateTime'])

    start_time = datetime.strptime(
        entries[0]['startedDateTime'], ISO_8601_FORMAT)

    captions = list(map(lambda x: x['request']['url'].split('/')[-1], entries))
    captions.insert(0, '')

    fig = plt.figure()
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
        start = datetime.strptime(
            entry['startedDateTime'], ISO_8601_FORMAT)
        end = start + timedelta(milliseconds=entry['time'])
        connect, send, wait, receive, = itemgetter(
            'connect', 'send', 'wait', 'receive')(entry['timings'])

        y = i + 1
        xstart = (start - start_time) / timedelta(milliseconds=1)
        xstop = (end - start_time) / timedelta(milliseconds=1)

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

    # plt.show()
    plt.show()
    plt.close(fig=fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    hardir = Path(args.dir)

    start_cdfs = []
    end_cdfs = []

    for name in ['chrome_h2.json', 'chrome_h3.json']:
        filename = Path.joinpath(hardir, name)

        with open(filename) as f:
            data = json.load(f)
            for entries in data:
                print(len(entries))
                if len(entries) == 1:
                    print(entries)

                entries.sort(key=lambda x: x['_requestTime'])

                start_cdfs.append(get_start_cdf(entries))
                end_cdfs.append(get_end_cdf(entries))

                # start_time = datetime.strptime(
                #     entries[0]['startedDateTime'], ISO_8601_FORMAT)

                # end_time = datetime.strptime(
                #     entries[-1]['startedDateTime'], ISO_8601_FORMAT)
                # end_time += timedelta(milliseconds=entries[-1]['time'])

                # total_time = end_time - start_time
                # print(colored("Filename: {}, Total time: {} ms".format(filename,
                #                                                        total_time / timedelta(milliseconds=1)), "green"))

                # plot(entries)

    # plot_cdf(start_cdfs)
    plot_cdf(end_cdfs)


if __name__ == "__main__":
    main()
