import os
import json
import math
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from pathlib import Path
from pprint import pprint
from scipy import stats

DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']
CLIENTS = ['chrome_h3', 'proxygen_h3',
           'ngtcp2_h3', 'chrome_h2', 'curl_h2']


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

    # 2. Walk har directory again and calculate min means, t-tests
    percent_diffs = []
    for dirname in timings.keys():
        data = []
        row_labels = []
        col_labels = CLIENTS

        for domain in DOMAINS:
            for size in SIZES:
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

                    min_mean = min(min_mean, mean)
                    if mean == min_mean:
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

                print(min_client, min_mean, diff)
                percent_diffs.append(
                    (
                        diff,
                        '{}/{}/{}'.format(dirname, domain, size),
                        min_client
                    )
                )
                data.append(row_data)

        fig, ax = plt.subplots()
        ax.set_title(dirname)
        im, cbar = heatmap(np.array(data), row_labels, col_labels, ax=ax,
                           cmap="Reds", cbarlabel="Percent difference")
        fig.tight_layout()
        plt.show()

    percent_diffs.sort(key=lambda x: x[0], reverse=True)
    print(percent_diffs)


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
    im = ax.imshow(data, **kwargs, vmin=0, vmax=50)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
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
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Turn spines off and create white grid.
    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


if __name__ == "__main__":
    main()
