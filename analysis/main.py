import os
import json
import math
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size
from pathlib import Path
from pprint import pprint
from scipy import stats

DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']
CLIENTS = ['chrome_h3', 'proxygen_h3',
           'ngtcp2_h3', 'chrome_h2', 'curl_h2']
NETWORK = [
    'loss-0_delay-0_bw-1',
    'loss-1_delay-0_bw-1',
    'loss-5_delay-0_bw-1',
    'loss-0_delay-50_bw-1',
    'loss-0_delay-200_bw-1',
    'loss-1_delay-200_bw-1',
    'loss-0_delay-0_bw-10',
    'loss-1_delay-0_bw-10',
    'loss-5_delay-0_bw-10',
    'loss-0_delay-50_bw-10',
    'loss-0_delay-200_bw-10',
    'loss-1_delay-200_bw-10',
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
            {'scenario': 'loss-1_delay-0_bw-10', 'title': '1%'},
            {'scenario': 'loss-5_delay-0_bw-10', 'title': '5%'},
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
            {'scenario': 'loss-0_delay-200_bw-10', 'title': '200ms'},
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
                if ttest.pvalue >= 0.05:
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


def h2_vs_h3_v2(timings: object):

    for domain in DOMAINS:

        for grouping in GROUPINGS_V1:

            h2_vs_h3_data = [[] for _ in range(len(grouping['items']))]
            h2_vs_h3_row_labels = [item['title'] for item in grouping['items']]
            h2_vs_h3_col_labels = SIZES
            bad_cov = 0

            for i, item in enumerate(grouping['items']):

                data = h2_vs_h3_data[i]
                network = item['scenario']

                for size in SIZES:
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

                        if len(times) != 20:
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
                    if ttest.pvalue >= 0.05:
                        data.append(0)
                    # reject null hypothesis
                    else:
                        diff = (min_h3_mean - min_h2_mean) / min_h2_mean * 100
                        data.append(diff)

            # print(bad_cov)

            fig, ax = plt.subplots()
            ax.set_title(
                '{} - {}'.format(domain.capitalize(), grouping['title']))
            im, cbar = heatmap(
                np.array(h2_vs_h3_data),
                h2_vs_h3_row_labels,
                h2_vs_h3_col_labels,
                ax=ax,
                cmap="bwr",
                cbarlabel="% Growth in PLT from H2 to H3",
                vmin=-20,
                vmax=20
            )
            annotate_heatmap(im, valfmt="{x:.1f}%", threshold=10)
            fig.tight_layout()
            plt.show()


def client_consistency(timings: object):
    percent_diffs = []

    for dirname in timings.keys():

        data = []
        row_labels = []
        col_labels = CLIENTS

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

                    mean = np.mean(times)

                    # h3 client
                    min_mean = min(min_mean, mean)
                    if min_mean == mean:
                        min_client = client

                mean_diffs = 0

                # perform t-test on other clients
                for client in CLIENTS:
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
                    if ttest.pvalue >= 0.05:
                        row_data.append(0)
                    # reject null hypothesis
                    else:
                        mean = np.mean(times)
                        diff = (mean - min_mean) / min_mean * 100
                        mean_diffs += diff
                        row_data.append(diff)

                # print(min_client, min_mean, diff)
                # percent_diffs.append(
                #     (
                #         diff,
                #         '{}/{}/{}'.format(dirname, domain, size),
                #         min_client
                #     )
                # )
                data.append(row_data)

        fig, ax = plt.subplots()
        ax.set_title(dirname)
        im, cbar = heatmap(
            np.array(data),
            row_labels,
            col_labels,
            ax=ax,
            cmap="Reds",
            cbarlabel="Percent difference",
            vmin=0,
            vmax=20
        )
        fig.tight_layout()
        plt.show()

    percent_diffs.sort(key=lambda x: x[0], reverse=True)
    print(percent_diffs)


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
            for size in SIZES:
                temp[domain][size] = {}

                experiment_path = Path.joinpath(
                    path,
                    dirname,
                    domain,
                    size
                )

                for filename in os.listdir(experiment_path):
                    with open(Path.joinpath(experiment_path, filename), mode='r') as f:
                        output = json.load(f)

                        temp[domain][size][filename.split('.')[0]] = output

        timings[dirname] = temp

    h2_vs_h3_v2(timings)
    h2_vs_h3_v1(timings)

    client_consistency(timings)


def heatmap(data, row_labels, col_labels, ax=None,
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

    # Create colorbar
    divider = make_axes_locatable(ax)
    width = axes_size.AxesY(ax, aspect=1./15)
    pad = axes_size.Fraction(0.5, width)
    cax = divider.append_axes("right", size=width, pad=pad)
    cbar = ax.figure.colorbar(im, cax=cax, ** cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[1]))
    ax.set_yticks(np.arange(data.shape[0]))
    # ... and label them with the respective list entries.
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)

    # Let the horizontal axes labeling appear on top.
    # ax.tick_params(top=False, bottom=True,
    #                labeltop=True, labelbottom=False)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right",
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


if __name__ == "__main__":
    main()
