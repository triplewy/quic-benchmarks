import os
import json
import math
import argparse
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

from matplotlib.ticker import StrMethodFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size
from pathlib import Path
from scipy import stats
from glob import glob

CONFIG = {}
with open(Path.joinpath(Path(__file__).parent.absolute(), '..', 'config.json'), mode='r') as f:
    CONFIG = json.load(f)

DOMAINS = CONFIG['domains']
SINGLE_SIZES = CONFIG['sizes']['single']
MULTI_SIZES = CONFIG['sizes']['multi']
CLIENTS = CONFIG['clients']

DATA_PATH = Path.joinpath(Path(__file__).parent.absolute(),
                          '..', CONFIG['data_path']['value'])
GRAPHS_PATH = Path.joinpath(Path(__file__).parent.absolute(),
                            '..', CONFIG['graphs_path']['value'])

GRAPHS_PATH.mkdir(parents=True, exist_ok=True)

NETWORK = [
    'loss-0_delay-0_bw-10',
    'loss-0_delay-0_bw-100',

    'LTE',

    'loss-0dot1_delay-0_bw-100',
    'loss-1_delay-0_bw-100',
    'loss-1burst_delay-0_bw-100',
    'loss-0_delay-50_bw-100',
    'loss-0_delay-100_bw-100',
    'loss-0_delay-100jitter_bw-100',

    'loss-0dot1_delay-0_bw-10',
    'loss-1_delay-0_bw-10',
    'loss-1burst_delay-0_bw-10',
    'loss-0_delay-50_bw-10',
    'loss-0_delay-100_bw-10',
    'loss-0_delay-100jitter_bw-10',


]

NETWORK_V2 = [
    {
        'dirnames': [
            'LTE',
            'loss-0_delay-0_bw-10',
            'loss-0_delay-0_bw-100',
        ],
        'labels': [
            'LTE',
            '10mbps',
            '100mbps'
        ],
        'title': 'varying_bandwidth'
    },
    {
        'dirnames': [
            'loss-0dot1_delay-0_bw-10',
            'loss-1_delay-0_bw-10',
        ],
        'labels': [
            '0.1%',
            '1%',
        ],
        'title': '10mbps_Loss'
    },
    {
        'dirnames': [
            'loss-0_delay-50_bw-10',
            'loss-0_delay-100_bw-10',
        ],
        'labels': [
            '50ms',
            '100ms',
        ],
        'title': '10mbps_Delay'
    },
    # {
    #     'dirnames': [
    #         'loss-0_delay-0_bw-100',
    #         'loss-0dot1_delay-0_bw-100',
    #         'loss-0dot1burstingress_delay-0_bw-100',
    #         'loss-0dot1burstegress_delay-0_bw-100',
    #         'loss-0dot1burst_delay-0_bw-100',
    #         'loss-1_delay-0_bw-100',
    #         'loss-1burstingress_delay-0_bw-100',
    #         'loss-1burstegress_delay-0_bw-100',
    #         'loss-1burst_delay-0_bw-100',
    #     ],
    #     'title': '100mbps_Loss_single'
    # },
    # {
    #     'dirnames': [
    #         'loss-0_delay-0_bw-100',
    #         'loss-0_delay-50_bw-100',
    #         'loss-1_delay-50_bw-100',
    #         'loss-0_delay-100_bw-100',
    #         'loss-0_delay-100jitter_bw-100',
    #     ],
    #     'title': '100mbps_Delay_single'
    # },
    # {
    #     'dirnames': [
    #         'revised_loss-0_delay-0_bw-10',
    #         'revised_loss-0dot1_delay-0_bw-10',
    #         'revised_loss-1_delay-0_bw-10',
    #     ],
    #     'title': '10mbps_Loss_multiple'
    # },
    # {
    #     'dirnames': [
    #         'revised_loss-0_delay-0_bw-10',
    #         'revised_loss-0_delay-50_bw-10',
    #         'revised_loss-0_delay-100_bw-10',
    #     ],
    #     'title': '10mbps_Delay_multiple'
    # },
    # {
    #     'dirnames': [
    #         'loss-0_delay-0_bw-100',
    #         'loss-0dot1_delay-0_bw-100',
    #         'loss-1_delay-0_bw-100',
    #         'loss-1burst_delay-0_bw-100'
    #     ],
    #     'title': '100mbps_Loss_multiple'
    # },
    # {
    #     'dirnames': [
    #         'loss-0_delay-0_bw-100',
    #         'loss-0_delay-50_bw-100',
    #         'loss-0_delay-100_bw-100',
    #     ],
    #     'title': '100mbps_Delay_multiple'
    # },
]

SI_GROUPINGS = [
    {
        'title': 'Extra Loss',
        'items': [
            {'scenario': 'revised_loss-0_delay-0_bw-10', 'title': '0%'},
            {'scenario': 'revised_loss-0dot1_delay-0_bw-10', 'title': '0.1%'},
            {'scenario': 'revised_loss-1_delay-0_bw-10', 'title': '1%'},
        ]
    },
    {
        'title': 'Extra Delay',
        'items': [
            {'scenario': 'revised_loss-0_delay-0_bw-10', 'title': '0ms'},
            {'scenario': 'revised_loss-0_delay-50_bw-10', 'title': '50ms'},
            {'scenario': 'revised_loss-0_delay-100_bw-10', 'title': '100ms'},
        ]
    }
]

GROUPINGS_V1 = [
    {
        'title': 'Extra Loss',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0%'},
            {'scenario': 'loss-0dot1_delay-0_bw-10', 'title': '0.1%'},
            {'scenario': 'loss-1_delay-0_bw-10', 'title': '1%'},
        ]
    },
    {
        'title': 'Extra RTT Delay',
        'items': [
            {'scenario': 'loss-0_delay-0_bw-10', 'title': '0ms'},
            {'scenario': 'loss-0_delay-50_bw-10', 'title': '50ms'},
            {'scenario': 'loss-0_delay-100_bw-10', 'title': '100ms'},
        ]
    }
]


def h2_vs_h3_v2(timings: object, sizes):

    for domain in DOMAINS:

        for grouping in GROUPINGS_V1:

            h2_vs_h3_data = [[] for _ in range(len(grouping['items']))]
            h2_vs_h3_row_labels = [item['title'] for item in grouping['items']]
            h2_vs_h3_col_labels = sizes

            bad_cov = 0

            for i, item in enumerate(grouping['items']):

                data = h2_vs_h3_data[i]
                network = item['scenario']

                if network == 'loss-0_delay-101_bw-10' and domain != 'facebook':
                    continue

                for size in sizes:

                    min_h3_median = math.inf
                    min_h3_mean = math.inf
                    min_h3_client = None

                    min_h2_median = math.inf
                    min_h2_mean = math.inf
                    min_h2_client = None

                    if network not in timings:
                        data.append(0)
                        continue

                    # get min_mean
                    for client, times in timings[network][domain][size].items():
                        if len(times) != 40:
                            print(network, size, client, len(times))

                        median = np.median(times)
                        mean = np.mean(times)
                        std = np.std(times)
                        cov = std / mean * 100

                        if cov > 10:
                            bad_cov += 1

                        # h3 client
                        if client.count('h3') > 0:
                            min_h3_mean = min(min_h3_mean, mean)
                            if min_h3_mean == mean:
                                min_h3_client = client
                            min_h3_median = min(min_h3_median, median)
                        # h2 client
                        else:
                            min_h2_mean = min(min_h2_mean, mean)
                            if min_h2_mean == mean:
                                min_h2_client = client
                            min_h2_median = min(min_h2_median, median)

                    # do t-test between min h2 and min h3 clients
                    ttest = stats.ttest_ind(
                        timings[network][domain][size][min_h2_client],
                        timings[network][domain][size][min_h3_client],
                        equal_var=False
                    )

                    pvalue = ttest.pvalue
                    pvalue = 0

                    # accept null hypothesis
                    if pvalue >= 0.01:
                        data.append(0)
                    # reject null hypothesis
                    else:
                        # diff = (min_h3_mean - min_h2_mean) / min_h2_mean * 100
                        # data.append(diff)

                        diff = (min_h3_median - min_h2_median) / \
                            min_h2_median * 100
                        data.append(diff)

            # print(bad_cov)

            print('{} - {}'.format(domain.capitalize(), grouping['title']))
            fig, ax = plt.subplots()
            # ax.set_title()
            ax.set_ylabel(grouping['title'], fontsize=18, labelpad=20)
            ax.set_xlabel('Object sizes', fontsize=18, labelpad=20)

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
            if sizes == MULTI_SIZES:
                multiple = '_Multiple'

            plt.savefig(
                '{}/Desktop/graphs_revised/{}_Extra_{}{}'.format(Path.home(), domain.capitalize(), condition, multiple), transparent=True)
            # plt.show()


def h2_vs_h3_v4(timings: object, groupings, sizes, useSI: bool):

    for domain in DOMAINS:

        for grouping in groupings:

            h2_vs_h3_data = [[] for _ in range(len(grouping['items']))]
            h2_vs_h3_row_labels = [item['title'] for item in grouping['items']]
            h2_vs_h3_col_labels = sizes

            for i, item in enumerate(grouping['items']):

                data = h2_vs_h3_data[i]
                network = item['scenario']

                for size in sizes:

                    min_h3_median = math.inf
                    min_h3_client = None

                    min_h2_median = math.inf
                    min_h2_client = None

                    if network not in timings:
                        data.append(0)
                        continue

                    # get min_median
                    for client, times in timings[network][domain][size].items():
                        if useSI:
                            times = times['speed-index']
                        else:
                            times = times['time']

                        median = np.median(times)

                        # h3 client
                        if client.count('h3') > 0:
                            min_h3_median = min(min_h3_median, median)
                            if min_h3_median == median:
                                min_h3_client = client
                        # h2 client
                        else:
                            min_h2_median = min(min_h2_median, median)
                            if min_h2_median == median:
                                min_h2_client = client

                    diff = (min_h3_median - min_h2_median) / \
                        min_h2_median * 100
                    data.append(diff)

            print('{} - {}'.format(domain.capitalize(), grouping['title']))
            fig, ax = plt.subplots()
            # ax.set_title()
            ax.set_ylabel(grouping['title'], fontsize=18, labelpad=20)
            ax.set_xlabel('Object sizes', fontsize=18, labelpad=20)

            im, cbar = heatmap(
                np.array(h2_vs_h3_data),
                h2_vs_h3_row_labels,
                h2_vs_h3_col_labels,
                ax=ax,
                cmap="bwr",
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
            if sizes == MULTI_SIZES:
                multiple = '_Multiple'

            si = ''
            if useSI:
                si = '_SI'

            plt.savefig(
                '{}/Desktop/graphs_revised/{}_Extra_{}{}{}'.format(Path.home(), domain.capitalize(), condition, multiple, si), transparent=True)
            plt.close()


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
    if sizes == MULTI_SIZES:
        multiple = '_multiple'

    plt.savefig(
        '{}/Desktop/graphs/facebook_patch{}'.format(Path.home(), multiple), transparent=True)

    percent_diffs = []

    data = []
    row_labels = []
    col_labels = [x.split('_')[0] for x in CLIENTS if x.count('h3') > 0]

    for i, size in enumerate(SINGLE_SIZES):
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
    for network in NETWORK:
        dirname = network
        data = []
        row_labels = []
        col_labels = [x.split('_')[0] for x in CLIENTS if x.count('h3') > 0]

        for domain in DOMAINS:

            for i, size in enumerate(SINGLE_SIZES):
                row_labels.append('{}/{}'.format(domain, size))
                row_data = []

                min_median = math.inf
                min_client = None

                # get min_median
                for client, times in timings[dirname][domain][size].items():
                    if client.count('h2') > 0:
                        continue

                    median = np.median(times)

                    # h3 client
                    min_median = min(min_median, median)
                    if min_median == median:
                        min_client = client

                # perform t-test on other clients
                for client in CLIENTS:
                    if client.count('h2') > 0:
                        continue

                    if client not in timings[dirname][domain][size]:
                        row_data.append(0)
                        continue

                    times = timings[dirname][domain][size][client]

                    ttest = stats.ttest_ind(
                        timings[dirname][domain][size][min_client],
                        times,
                        equal_var=False
                    )

                    pvalue = ttest.pvalue
                    pvalue = 0

                    # accept null hypothesis
                    if pvalue >= 0.01:
                        row_data.append(0)
                    # reject null hypothesis
                    else:
                        median = np.median(times)
                        diff = (median - min_median) / min_median * 100
                        row_data.append(diff)

                data.append(row_data)

        fig, ax = plt.subplots(figsize=(10, 5))
        print(network)
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
        plt.savefig(Path.joinpath(
            GRAPHS_PATH, 'H3_{}'.format(dirname)), transparent=True)
        plt.close()
        # plt.show()


def h2_vs_h3_v5(timings: object):
    for obj in NETWORK_V2:
        dirnames = obj['dirnames']
        col_labels = obj['labels']
        title = obj['title']

        data = []
        row_labels = []

        if title.count('multiple') > 0:
            sizes = MULTI_SIZES
        else:
            sizes = SINGLE_SIZES

        for domain in DOMAINS:

            sub_data = []
            sub_row_labels = []

            for i, size in enumerate(sizes):
                sub_row_labels.append('{}/{}'.format(domain, size))
                row_data = []

                for dirname in dirnames:

                    min_h3_median = math.inf
                    min_h3_client = None

                    min_h2_median = math.inf
                    min_h2_client = None

                    if dirname in timings:
                        for client, times in timings[dirname][domain][size].items():

                            if size in MULTI_SIZES:
                                median = np.median(times['speed-index'])
                            else:
                                median = np.median(times)

                            # h3 client
                            if client.count('h3') > 0:
                                min_h3_median = min(min_h3_median, median)
                                if min_h3_median == median:
                                    min_h3_client = client
                            # h2 client
                            else:
                                min_h2_median = min(min_h2_median, median)
                                if min_h2_median == median:
                                    min_h2_client = client

                    diff = (min_h3_median - min_h2_median) / \
                        min_h2_median * 100
                    row_data.append(diff)

                sub_data.append(row_data)

            data.append(sub_data)
            row_labels.append(sub_row_labels)

        print(title)
        fig, axs = plt.subplots(1, 3, figsize=(12, 4), gridspec_kw={
            'wspace': 0, 'hspace': 0})

        for i, ax in enumerate(axs):
            ax.set_aspect('equal')
            im, cbar = heatmap(
                np.transpose(data[i]),
                col_labels,
                row_labels[i],
                ax=ax,
                cmap="bwr",
                # cbarlabel="Percent difference",
                vmin=-25,
                vmax=25,
                rotation=20,
                # show_cbar=True if i == len(axs) - 1 else False,
            )
            annotate_heatmap(
                im, valfmt="{x:.1f}%", threshold=8, fontsize=16, fontweight=600)

        for ax in axs.flat:
            ax.label_outer()

        fig.tight_layout()
        plt.savefig(Path.joinpath(
            GRAPHS_PATH, 'H2vsH3_{}'.format(title)), transparent=True)
        plt.close()


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
            if im.norm(abs(data[i, j])) > threshold:
                kw.update(color=textcolors[int(
                    im.norm(abs(data[i, j])) > threshold)])
                text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
                texts.append(text)
            else:
                texts.append('')
    return texts


def main():
    timings = {}

    # 1. Walk timings directory and fill in timings
    path = Path.joinpath(DATA_PATH, 'timings')

    for dirname in os.listdir(path):
        temp = {}
        for domain in DOMAINS:
            temp[domain] = {}
            for size in SINGLE_SIZES + MULTI_SIZES:
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

    # facebook_patch(timings, SIZES)
    # facebook_patch(timings, MULTI_SIZES)
    h2_vs_h3_v5(timings)
    # h2_vs_h3_v2(timings, SIZES)
    # h2_vs_h3_v4(timings, SI_GROUPINGS, MULTI_SIZES, True)
    client_consistency(timings)


if __name__ == "__main__":
    main()
