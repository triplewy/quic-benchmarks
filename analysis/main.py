import os
import json
import math
import argparse
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from matplotlib.ticker import StrMethodFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size
from pathlib import Path
from pprint import pprint
from scipy import stats
from glob import glob

DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']
WEBPAGE_SIZES = ['small', 'medium', 'large']
CLIENTS = ['chrome_h3', 'proxygen_h3',
           'ngtcp2_h3', 'chrome_h2', 'curl_h2']

NETWORK = [
    {
        'dirname': 'loss-0_delay-0_bw-10',
        'title': '0_Loss'
    },
    {
        'dirname': 'loss-0dot1_delay-0_bw-10',
        'title': '0dot1_Loss'
    },
    {
        'dirname': 'loss-1_delay-0_bw-10',
        'title': '1_Loss'
    },
    {
        'dirname': 'loss-0_delay-50_bw-10',
        'title': '50_Delay'
    },
    {
        'dirname': 'loss-0_delay-100_bw-10',
        'title': '100_Delay'
    },
]

NGTCP2_SCENARIOS = [
    {
        'dirname': 'loss-0_delay-0_bw-10',
        'title': '0ms RTT Delay'
    },
    {
        'dirname': 'loss-0_delay-50_bw-10',
        'title': '50ms RTT Delay'
    },
    {
        'dirname': 'loss-0_delay-60_bw-10',
        'title': '60ms RTT Delay'
    },
    {
        'dirname': 'loss-0_delay-70_bw-10',
        'title': '70ms RTT Delay'
    },
    {
        'dirname': 'loss-0_delay-80_bw-10',
        'title': '80ms RTT Delay'
    },
    {
        'dirname': 'loss-0_delay-90_bw-10',
        'title': '90ms RTT Delay'
    },
    {
        'dirname': 'loss-0_delay-100_bw-10',
        'title': '100ms RTT Delay'
    },
]

GROUPINGS_V0 = [
    {
        'title': 'Extra Loss (1MB Bandwidth)',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-1', 'title': '0%'},
            {'scenario': 'loss-1_delay-0_bw-1', 'title': '1%'},
            {'scenario': 'loss-5_delay-0_bw-1', 'title': '5%'},
        ]
    },
    {
        'title': 'Extra RTT Delay (1MB Bandwidth)',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-1', 'title': '0ms'},
            {'scenario': 'loss-0_delay-50_bw-1', 'title': '50ms'},
            {'scenario': 'loss-0_delay-200_bw-1', 'title': '200ms'},
        ]
    },
    {
        'title': 'Extra Loss (10MB Bandwidth)',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0%'},
            {'scenario': 'loss-1_delay-0_bw-10', 'title': '1%'},
            {'scenario': 'loss-5_delay-0_bw-10', 'title': '5%'},
        ]
    },
    {
        'title': 'Extra RTT Delay (10MB Bandwidth)',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0ms'},
            {'scenario': 'loss-0_delay-50_bw-10', 'title': '50ms'},
            {'scenario': 'loss-0_delay-200_bw-10', 'title': '200ms'},
        ]
    }
]

GROUPINGS_V1 = [
    {
        'title': 'Extra Loss',
        'items': [
            # {'scenario': 'loss-0_delay-0_bw-1', 'title': '0% (1mb bw)'},
            # {'scenario': 'loss-1_delay-0_bw-1', 'title': '1% (1mb bw)'},
            # {'scenario': 'loss-5_delay-0_bw-1', 'title': '5% (1mb bw)'},
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0%'},
            {'scenario': 'loss-0dot1_delay-0_bw-10', 'title': '0.1%'},
            {'scenario': 'loss-1_delay-0_bw-10', 'title': '1%'},
            # {'scenario': 'loss-2dot5_delay-0_bw-10', 'title': '2.5%'},
        ]
    },
    {
        'title': 'Extra RTT Delay',
        'items': [
            # {'scenario': 'loss-0_delay-0_bw-1', 'title': '0ms (1mb bw)'},
            # {'scenario': 'loss-0_delay-50_bw-1', 'title': '50ms (1mb bw)'},
            # {'scenario': 'loss-0_delay-200_bw-1', 'title': '200ms (1mb bw)'},
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0ms'},
            {'scenario': 'loss-0_delay-50_bw-10', 'title': '50ms'},
            {'scenario': 'loss-0_delay-100_bw-10', 'title': '100ms'},
            # {'scenario': 'loss-0_delay-250_bw-10', 'title': '250ms'},
        ]
    },
]

GROUPINGS_V2 = [
    {
        'title': 'Extra Loss',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-1', 'title': '0% (1mb bw)'},
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0% (10mb bw)'},
            {'scenario': 'loss-1_delay-0_bw-1', 'title': '1% (1mb bw)'},
            {'scenario': 'loss-1_delay-0_bw-10', 'title': '1% (10mb bw)'},
            {'scenario': 'loss-5_delay-0_bw-1', 'title': '5% (1mb bw)'},
            {'scenario': 'loss-5_delay-0_bw-10', 'title': '5% (10mb bw)'},
        ]
    },
    {
        'title': 'Extra RTT Delay',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-1', 'title': '0ms (1mb bw)'},
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0ms(10mb bw)'},
            {'scenario': 'loss-0_delay-50_bw-1', 'title': '50ms (1mb bw)'},
            {'scenario': 'loss-0_delay-50_bw-10', 'title': '50ms (10mb bw)'},
            {'scenario': 'loss-0_delay-200_bw-1', 'title': '200ms (1mb bw)'},
            {'scenario': 'loss-0_delay-200_bw-10', 'title': '200ms (10mb bw)'},
        ]
    },
]


def h2_vs_h3_v1(timings: object):
    h2_vs_h3_data = {}
    h2_vs_h3_row_labels = SIZES
    h2_vs_h3_col_labels = NETWORK

    for domain in DOMAINS:
        data = [[] for _ in range(len(SIZES))]

        for dirname in NETWORK:

            for i, size in enumerate(SIZES):
                min_h3_mean = math.inf
                min_h3_client = None

                min_h2_mean = math.inf
                min_h2_client = None

                if dirname not in timings:
                    data[i].append(0)
                    continue

                # get min_mean
                for client, times in timings[dirname][domain][size].items():
                    # skip firefox for now...
                    if client.count('firefox') > 0:
                        continue

                    mean = np.mean(times)

                    # h3 client
                    if client.count('h3') > 0:
                        min_h3_mean = min(min_h3_mean, mean)
                        if min_h3_mean == mean:
                            min_h3_client = client
                    # h2 client
                    else:
                        min_h2_mean = min(min_h2_mean, mean)
                        if min_h2_mean == mean:
                            min_h2_client = client

                # do t-test between min h2 and min h3 clients
                ttest = stats.ttest_ind(
                    timings[dirname][domain][size][min_h2_client],
                    timings[dirname][domain][size][min_h3_client],
                    equal_var=False
                )

                # accept null hypothesis
                if ttest.pvalue >= 0.01:
                    data[i].append(0)
                # reject null hypothesis
                else:
                    diff = (min_h3_mean - min_h2_mean) / min_h2_mean * 100
                    data[i].append(diff)

        h2_vs_h3_data[domain] = data

    for domain in DOMAINS:
        fig, ax = plt.subplots()
        ax.set_title(domain.upper())
        im, cbar = heatmap(
            np.array(h2_vs_h3_data[domain]),
            h2_vs_h3_row_labels,
            h2_vs_h3_col_labels,
            ax=ax,
            cmap="bwr",
            cbarlabel="H3 compared to H2 PLT (%)",
            vmin=-20,
            vmax=20
        )
        fig.tight_layout()
        plt.show()


def h2_vs_h3_v2(timings: object, sizes):

    for domain in DOMAINS:

        for grouping in GROUPINGS_V1:

            h2_vs_h3_data = [[] for _ in range(len(grouping['items']))]
            h2_vs_h3_row_labels = [item['title'] for item in grouping['items']]
            h2_vs_h3_col_labels = sizes
            if domain == 'cloudflare' and sizes == WEBPAGE_SIZES:
                h2_vs_h3_col_labels = sizes[:2]
            bad_cov = 0

            for i, item in enumerate(grouping['items']):

                data = h2_vs_h3_data[i]
                network = item['scenario']

                if network == 'loss-0_delay-101_bw-10' and domain != 'facebook':
                    continue

                for size in sizes:

                    if domain == 'cloudflare' and size == 'large':
                        continue

                    min_h3_mean = math.inf
                    min_h3_client = None

                    min_h2_mean = math.inf
                    min_h2_client = None

                    if network not in timings:
                        data.append(0)
                        continue

                    # get min_mean
                    for client, times in timings[network][domain][size].items():
                        # skip firefox for now...
                        if client.count('firefox') > 0:
                            continue

                        if len(times) != 40:
                            print(network, size, client, len(times))

                        mean = np.mean(times)
                        std = np.std(times)
                        cov = std / mean * 100

                        if cov > 10:
                            bad_cov += 1
                            # print(cov, network, size, client)

                        # h3 client
                        if client.count('h3') > 0:
                            min_h3_mean = min(min_h3_mean, mean)
                            if min_h3_mean == mean:
                                min_h3_client = client
                        # h2 client
                        else:
                            min_h2_mean = min(min_h2_mean, mean)
                            if min_h2_mean == mean:
                                min_h2_client = client

                    # do t-test between min h2 and min h3 clients
                    ttest = stats.ttest_ind(
                        timings[network][domain][size][min_h2_client],
                        timings[network][domain][size][min_h3_client],
                        equal_var=False
                    )

                    # accept null hypothesis
                    if ttest.pvalue >= 0.01:
                        data.append(0)
                    # reject null hypothesis
                    else:
                        diff = (min_h3_mean - min_h2_mean) / min_h2_mean * 100
                        data.append(diff)

            # print(bad_cov)

            print('{} - {}'.format(domain.capitalize(), grouping['title']))
            fig, ax = plt.subplots()
            # ax.set_title()
            # ax.set_ylabel(grouping['title'], fontsize=18, fontweight='bold')
            im, cbar = heatmap(
                np.array(h2_vs_h3_data),
                h2_vs_h3_row_labels,
                h2_vs_h3_col_labels,
                ax=ax,
                cmap="bwr",
                # cbarlabel="% Growth in PLT from H2 to H3",
                vmin=-20,
                vmax=20,
                show_cbar=False,
            )
            annotate_heatmap(
                im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)
            fig.tight_layout()

            condition = None
            if grouping['title'].count('Loss') > 0:
                condition = 'Loss'
            else:
                condition = 'Delay'

            multiple = ''
            if sizes == WEBPAGE_SIZES:
                multiple = '_Multiple'

            plt.savefig(
                '{}/Desktop/graphs/{}_Extra_{}{}'.format(Path.home(), domain.capitalize(), condition, multiple), transparent=True)
            # plt.show()


def h2_vs_h3_v3(timings: object, sizes):
    for domain in ['google', 'facebook', 'cloudflare']:

        h2_vs_h3_data = [[] for _ in range(3)]
        h2_vs_h3_row_labels = ['> 192 KB', '32 KB', '8 KB']
        # h2_vs_h3_row_labels = ['> 192 KB', '8 KB']

        h2_vs_h3_col_labels = sizes

        networks = ['loss-1_delay-0_bw-10',
                    'loss-2_delay-0_bw-10', 'loss-3_delay-0_bw-10']
        # networks = ['loss-1_delay-0_bw-10', 'loss-3_delay-0_bw-10']

        for i, network in enumerate(networks):

            data = h2_vs_h3_data[i]

            for size in sizes:

                min_h3_mean = math.inf
                min_h3_client = None

                min_h2_mean = math.inf
                min_h2_client = None

                if network not in timings:
                    data.append(0)
                    continue

                # get min_mean
                for client, times in timings[network][domain][size].items():
                    mean = np.mean(times)
                    std = np.std(times)

                    # h3 client
                    if client.count('h3') > 0:
                        min_h3_mean = min(min_h3_mean, mean)
                        if min_h3_mean == mean:
                            min_h3_client = client
                    # h2 client
                    else:
                        min_h2_mean = min(min_h2_mean, mean)
                        if min_h2_mean == mean:
                            min_h2_client = client

                # do t-test between min h2 and min h3 clients
                ttest = stats.ttest_ind(
                    timings[network][domain][size][min_h2_client],
                    timings[network][domain][size][min_h3_client],
                    equal_var=False
                )

                # accept null hypothesis
                if ttest.pvalue >= 0.01:
                    data.append(0)
                # reject null hypothesis
                else:
                    diff = (min_h3_mean - min_h2_mean) / min_h2_mean * 100
                    data.append(diff)

        fig, ax = plt.subplots()
        # ax.set_ylabel(grouping['title'], fontsize=18, fontweight='bold')
        im, cbar = heatmap(
            np.array(h2_vs_h3_data),
            h2_vs_h3_row_labels,
            h2_vs_h3_col_labels,
            ax=ax,
            cmap="bwr",
            # cbarlabel="% Growth in PLT from H2 to H3",
            vmin=-20,
            vmax=20,
            show_cbar=False,
        )
        annotate_heatmap(
            im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)
        fig.tight_layout()

        plt.savefig(
            '{}/Desktop/graphs/{}_buffer_size'.format(Path.home(), domain.capitalize()), transparent=True)
        # plt.show()


def facebook_patch(timings: object, sizes):
    domain = 'facebook'
    before = 'loss-0_delay-100_bw-10'
    after = 'loss-0_delay-101_bw-10'

    h2_vs_h3_data = [[], []]
    h2_vs_h3_row_labels = ['before', 'after']
    h2_vs_h3_col_labels = sizes

    for i, network in enumerate([before, after]):
        data = h2_vs_h3_data[i]

        for size in sizes:

            min_h3_mean = math.inf
            min_h3_client = None

            min_h2_mean = math.inf
            min_h2_client = None

            # get min_mean
            for client, times in timings[network][domain][size].items():
                mean = np.mean(times)
                std = np.std(times)

                # h3 client
                if client.count('h3') > 0:
                    min_h3_mean = min(min_h3_mean, mean)
                    if min_h3_mean == mean:
                        min_h3_client = client
                # h2 client
                else:
                    min_h2_mean = min(min_h2_mean, mean)
                    if min_h2_mean == mean:
                        min_h2_client = client

            # do t-test between min h2 and min h3 clients
            ttest = stats.ttest_ind(
                timings[network][domain][size][min_h2_client],
                timings[network][domain][size][min_h3_client],
                equal_var=False
            )

            print(network, size, min_h3_mean)
            # accept null hypothesis
            if ttest.pvalue >= 0.01:
                data.append(0)
            # reject null hypothesis
            else:
                diff = (min_h3_mean - min_h2_mean) / min_h2_mean * 100
                data.append(diff)

    fig, ax = plt.subplots()
    im, cbar = heatmap(
        np.array(h2_vs_h3_data),
        h2_vs_h3_row_labels,
        h2_vs_h3_col_labels,
        ax=ax,
        cmap="bwr",
        # cbarlabel="% Growth in PLT from H2 to H3",
        vmin=-20,
        vmax=20,
        show_cbar=False,
    )
    annotate_heatmap(
        im, valfmt="{x:.1f}%", threshold=5, fontsize=18, fontweight=600)
    fig.tight_layout()

    multiple = ''
    if sizes == WEBPAGE_SIZES:
        multiple = '_multiple'

    plt.savefig(
        '{}/Desktop/graphs/facebook_patch{}'.format(Path.home(), multiple), transparent=True)

    percent_diffs = []

    data = []
    row_labels = []
    col_labels = ['Chrome', 'Proxygen', 'Ngtcp2']

    for i, size in enumerate(SIZES):
        row_labels.append('{}/{}'.format(domain, size))
        row_data = []

        min_mean = math.inf
        min_client = None

        # get min_mean
        for client, times in timings[network][domain][size].items():
            if client.count('h2') > 0:
                continue

            mean = np.mean(times)

            # h3 client
            min_mean = min(min_mean, mean)
            if min_mean == mean:
                min_client = client

        mean_diffs = 0

        # perform t-test on other clients
        for client in CLIENTS:
            if client.count('h2') > 0:
                continue

            times = timings[network][domain][size][client]

            ttest = stats.ttest_ind(
                timings[network][domain][size][min_client],
                times,
                equal_var=False
            )

            # accept null hypothesis
            if ttest.pvalue >= 0.01:
                row_data.append(0)
            # reject null hypothesis
            else:
                mean = np.mean(times)
                diff = (mean - min_mean) / min_mean * 100
                print('facebook patch diff: {}', diff)
                mean_diffs += diff
                row_data.append(diff)

        data.append(row_data)

    fig, ax = plt.subplots(figsize=(10, 5))
    im, cbar = heatmap(
        np.transpose(data),
        col_labels,
        row_labels,
        ax=ax,
        cmap="Reds",
        # cbarlabel="Percent difference",
        vmin=0,
        vmax=30,
        rotation=20,
        show_cbar=True,
    )
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs/H3_facebook_patch'.format(Path.home()), transparent=True)


def client_consistency(timings: object):
    percent_diffs = []

    for obj in NETWORK:
        dirname = obj['dirname']
        title = obj['title']
        data = []
        row_labels = []
        col_labels = ['Chrome', 'Proxygen', 'Ngtcp2']

        for domain in DOMAINS:

            for i, size in enumerate(SIZES):
                row_labels.append('{}/{}'.format(domain, size))
                row_data = []

                min_mean = math.inf
                min_client = None

                # get min_mean
                for client, times in timings[dirname][domain][size].items():
                    # skip firefox for now...
                    if client.count('firefox') > 0:
                        continue

                    if client.count('h2') > 0:
                        continue

                    mean = np.mean(times)

                    # h3 client
                    min_mean = min(min_mean, mean)
                    if min_mean == mean:
                        min_client = client

                # print(title, domain, size, min_mean)

                mean_diffs = 0

                # perform t-test on other clients
                for client in CLIENTS:
                    if client.count('h2') > 0:
                        continue

                    times = timings[dirname][domain][size][client]

                    # skip firefox for now...
                    if client.count('firefox') > 0:
                        continue

                    ttest = stats.ttest_ind(
                        timings[dirname][domain][size][min_client],
                        times,
                        equal_var=False
                    )

                    # accept null hypothesis
                    if ttest.pvalue >= 0.01:
                        row_data.append(0)
                    # reject null hypothesis
                    else:
                        mean = np.mean(times)
                        diff = (mean - min_mean) / min_mean * 100
                        print(title, domain, size, client, diff)
                        mean_diffs += diff
                        row_data.append(diff)

                data.append(row_data)

        fig, ax = plt.subplots(figsize=(10, 5))
        print(title)
        # ax.set_title(title)
        im, cbar = heatmap(
            np.transpose(data),
            col_labels,
            row_labels,
            ax=ax,
            cmap="Reds",
            # cbarlabel="Percent difference",
            vmin=0,
            vmax=20,
            rotation=20,
            show_cbar=True,
        )
        fig.tight_layout()
        plt.savefig(
            '{}/Desktop/graphs/H3_{}'.format(Path.home(), title), transparent=True)
        # plt.show()

    percent_diffs.sort(key=lambda x: x[0], reverse=True)
    # print(percent_diffs)


def ngtcp2_graph(timings):

    data = []
    line_labels = []

    for domain in DOMAINS:

        line_labels.append(domain)
        row_data = []

        for obj in NGTCP2_SCENARIOS:
            dirname = obj['dirname']
            size = '1MB'
            delay = int(dirname.split('_')[1].split('-')[1])

            min_mean = math.inf
            min_client = None

            # get min_mean of other clients
            for client, times in timings[dirname][domain][size].items():
                # skip firefox for now...
                if client.count('firefox') > 0:
                    continue

                if client.count('h2') > 0:
                    continue

                if client.count('ngtcp2_h3') > 0:
                    continue

                mean = np.mean(times)

                # h3 min mean
                min_mean = min(min_mean, mean)
                if min_mean == mean:
                    min_client = client

            # perform t-test on ngtcp2
            client = 'ngtcp2_h3'

            if client not in timings[dirname][domain][size]:
                continue

            times = timings[dirname][domain][size][client]

            ttest = stats.ttest_ind(
                timings[dirname][domain][size][min_client],
                times,
                equal_var=False
            )

            # accept null hypothesis
            if ttest.pvalue >= 0.01:
                row_data.append((delay, 0))
            # reject null hypothesis
            else:
                mean = np.mean(times)
                diff = (mean - min_mean) / min_mean * 100
                row_data.append((delay, diff))

        data.append(row_data)

    fig, ax = plt.subplots(figsize=(12, 9))
    # plt.ylabel('Total KB ACKed')
    plt.xlabel('RTT Delay (ms)', fontsize=20)

    legend = [
        mpatches.Patch(color='green', label='Facebook'),
        mpatches.Patch(color='red', label='Cloudflare'),
        mpatches.Patch(color='blue', label='Google'),
    ]

    for i in range(len(data)):
        if i == 0:
            color = 'green'
        elif i == 1:
            color = 'red'
        else:
            color = 'blue'

        row_data = data[i]

        plt.plot(
            [x[0] for x in row_data],
            [x[1] for x in row_data],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=8,
        )

    ax.tick_params(axis='both', which='major', labelsize=18)
    ax.tick_params(axis='both', which='minor', labelsize=18)

    formatter0 = StrMethodFormatter('{x:,g} %')
    ax.yaxis.set_major_formatter(formatter0)

    plt.xticks(np.array([0, 50, 60, 70, 80, 90, 100]))
    plt.grid(axis='x')
    plt.legend(handles=legend)
    plt.show()
    plt.close(fig=fig)


def check_data_lengths(timings):
    for obj in NETWORK:
        dirname = obj['dirname']
        for domain in DOMAINS:
            for size in SIZES + WEBPAGE_SIZES:

                times = timings[dirname][domain][size]

                for client in CLIENTS:
                    if client not in times:
                        continue

                    mean = np.mean(times[client])
                    std = np.std(times[client])

                    print(std / mean * 100)


def heatmap(data, row_labels, col_labels, ax=None, rotation=0, show_cbar=False,
            cbar_kw={}, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (N, M).
    row_labels
        A list or array of length N with the labels for the rows.
    col_labels
        A list or array of length M with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if not ax:
        ax = plt.gca()

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    cbar = None
    # # Create colorbar
    if show_cbar:
        divider = make_axes_locatable(ax)
        width = axes_size.AxesY(ax, aspect=1./12)
        pad = axes_size.Fraction(1, width)
        cax = divider.append_axes("right", size=width, pad=pad)
        cbar = ax.figure.colorbar(im, cax=cax, ** cbar_kw)
        cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")
        cbar.ax.tick_params(labelsize=16)

    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[1]))
    ax.set_yticks(np.arange(data.shape[0]))
    # ... and label them with the respective list entries.
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(axis='y', labelsize=18)
    ax.tick_params(axis='x', labelsize=16)
    # ax.tick_params(top=False, bottom=True,
    #                labeltop=True, labelbottom=False)

    # Rotate the tick labels and set their alignment.
    if rotation == 0:
        ha = 'center'
    else:
        ha = 'right'

    plt.setp(ax.get_xticklabels(), rotation=rotation, ha=ha,
             rotation_mode="anchor")

    # Turn spines off and create white grid.
    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
                     textcolors=("black", "white"),
                     threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        `matplotlib.ticker.Formatter`.  Optional.
    textcolors
        A pair of colors.  The first is used for values below a threshold,
        the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to `text` used to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a `Text` for each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(
                im.norm(abs(data[i, j])) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts


def main():
    timings = {}

    # 1. Walk har directory and fill in timings
    path = Path.joinpath(
        Path(os.path.dirname(os.path.abspath(__file__))),
        '..',
        'clients',
        'har'
    )

    for dirname in os.listdir(path):
        temp = {}
        for domain in DOMAINS:
            temp[domain] = {}
            for size in SIZES + WEBPAGE_SIZES:
                temp[domain][size] = {}

                experiment_path = Path.joinpath(
                    path,
                    dirname,
                    domain,
                    size
                )

                if not os.path.exists(experiment_path):
                    continue

                for filename in os.listdir(experiment_path):
                    try:
                        with open(Path.joinpath(experiment_path, filename), mode='r') as f:
                            output = json.load(f)

                            temp[domain][size][filename.split('.')[0]] = output
                    except:
                        pass

        timings[dirname] = temp

    # h2_vs_h3_v3(timings, SIZES)
    # facebook_patch(timings, SIZES)
    # facebook_patch(timings, WEBPAGE_SIZES)
    # check_data_lengths(timings)
    # h2_vs_h3_v2(timings, SIZES)
    # h2_vs_h3_v2(timings, WEBPAGE_SIZES)
    # ngtcp2_graph(timings)
    client_consistency(timings)


if __name__ == "__main__":
    main()
