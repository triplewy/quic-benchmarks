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

    'loss-0dot1_delay-0_bw-10',
    'loss-1_delay-0_bw-10',
    'loss-10_delay-0_bw-10',

    'loss-0_delay-50_bw-10',
    'loss-0_delay-100_bw-10',
]

NETWORK_V2 = [
    {
        'dirnames': [
            'loss-0_delay-0_bw-10',
            'loss-0dot1_delay-0_bw-10',
            'loss-1_delay-0_bw-10',
        ],
        'labels': [
            '0%',
            '0.1%',
            '1%',
        ],
        'title': 'Loss'
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
        'title': 'Delay'
    },
    {
        'dirnames': [
            'loss-0_delay-0_bw-10_multi_800x600',
            'loss-0dot1_delay-0_bw-10_multi_800x600',
            'loss-1_delay-0_bw-10_multi_800x600',
        ],
        'labels': [
            '0%',
            '0.1%',
            '1%',
        ],
        'title': 'Loss_Multi'
    },
    {
        'dirnames': [
            'loss-0_delay-50_bw-10_multi_800x600',
            'loss-0_delay-100_bw-10_multi_800x600',
        ],
        'labels': [
            '50ms',
            '100ms',
        ],
        'title': 'Delay_Multi'
    },
    {
        'dirnames': [
            'loss-0_delay-0_bw-10_multi_800x600',
            'loss-0dot1_delay-0_bw-10_multi_800x600',
            'loss-1_delay-0_bw-10_multi_800x600',
        ],
        'labels': [
            '0%',
            '0.1%',
            '1%',
        ],
        'title': 'Loss_Multi_PLT'
    },
    {
        'dirnames': [
            'loss-0_delay-50_bw-10_multi_800x600',
            'loss-0_delay-100_bw-10_multi_800x600',
        ],
        'labels': [
            '50ms',
            '100ms',
        ],
        'title': 'Delay_Multi_PLT'
    },
    {
        'dirnames': [
            'loss-0_delay-0_bw-10_multi_800x600',
            'loss-0dot1_delay-0_bw-10_multi_800x600',
            'loss-1_delay-0_bw-10_multi_800x600',
        ],
        'labels': [
            '0%',
            '0.1%',
            '1%',
        ],
        'title': 'Loss_Multi_Interactive'
    },
    {
        'dirnames': [
            'loss-0_delay-50_bw-10_multi_800x600',
            'loss-0_delay-100_bw-10_multi_800x600',
        ],
        'labels': [
            '50ms',
            '100ms',
        ],
        'title': 'Delay_Multi_Interactive'
    },
    {
        'dirnames': [
            'revised_loss-0_delay-0_bw-10',
            'revised_loss-0dot1_delay-0_bw-10',
            'revised_loss-1_delay-0_bw-10',
        ],
        'labels': [
            '0%',
            '0.1%',
            '1%',
        ],
        'title': 'Loss_Multi_Revised'
    },
    {
        'dirnames': [
            'revised_loss-0_delay-50_bw-10',
            'revised_loss-0_delay-100_bw-10',
        ],
        'labels': [
            '50ms',
            '100ms',
        ],
        'title': 'Delay_Multi_Revised'
    },
    # {
    #     'dirnames': [
    #         'loss-0_delay-50_bw-10',
    #         'loss-0_delay-100_bw-10',
    #     ],
    #     'labels': [
    #         '50ms',
    #         '100ms',
    #     ],
    #     'title': 'Delay_Multi'
    # },
    # {
    #     'dirnames': [
    #         'loss-0dot1ingress_delay-0_bw-10',
    #         'loss-1ingress_delay-0_bw-10',
    #         'loss-10ingress_delay-0_bw-10',
    #     ],
    #     'labels': [
    #         '0.1%',
    #         '1%',
    #         '10%',
    #     ],
    #     'title': 'Ingress Loss'
    # },
    # {
    #     'dirnames': [
    #         'loss-0dot1egress_delay-0_bw-10',
    #         'loss-1egress_delay-0_bw-10',
    #         'loss-10egress_delay-0_bw-10',
    #     ],
    #     'labels': [
    #         '0.1%',
    #         '1%',
    #         '10%',
    #     ],
    #     'title': 'Egress Loss'
    # },
]


def facebook_patch(timings: object, sizes):
    for obj in [
            {
                'dirnames': ['loss-0_delay-50_bw-10', 'loss-0_delay-100_bw-10'],
                'labels': ['50ms', '100ms'],
                'title': 'Facebook_Patch_Before'
            },
            {
                'dirnames': ['loss-0_delay-51_bw-10', 'loss-0_delay-101_bw-10'],
                'labels': ['50ms', '100ms'],
                'title': 'Facebook_Patch_After'
            }
    ]:
        dirnames = obj['dirnames']
        col_labels = obj['labels']
        title = obj['title']

        data = []
        row_labels = []

        for domain in ['facebook']:

            for i, size in enumerate(sizes):
                row_labels.append('{}/{}'.format(domain, size))
                row_data = []

                for dirname in dirnames:

                    min_h3_median = math.inf
                    min_h3_client = None

                    min_h2_median = math.inf
                    min_h2_client = None

                    if dirname in timings:
                        for client, times in timings[dirname][domain][size].items():

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

                data.append(row_data)

        print(title)
        fig, ax = plt.subplots(figsize=(4, len(dirnames) + 1))

        print(data)
        im, cbar = heatmap(
            np.transpose(data),
            col_labels,
            row_labels,
            ax=ax,
            cmap="bwr",
            # cbarlabel="Percent difference",
            vmin=-25,
            vmax=25,
            rotation=20,
            # show_cbar=True if i == len(axs) - 1 else False,
        )
        annotate_heatmap(
            im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)

        fig.tight_layout()
        plt.savefig(Path.joinpath(
            GRAPHS_PATH, f'H2vsH3_{title}'), transparent=True)
        plt.close()

    # domain = 'facebook'
    # before = 'loss-0_delay-100_bw-10'
    # after = 'loss-0_delay-101_bw-10'

    # h2_vs_h3_data = [[], []]
    # h2_vs_h3_row_labels = ['before', 'after']
    # h2_vs_h3_col_labels = sizes

    # for i, network in enumerate([before, after]):
    #     data = h2_vs_h3_data[i]

    #     for size in sizes:

    #         min_h3_median = math.inf
    #         min_h3_client = None

    #         min_h2_median = math.inf
    #         min_h2_client = None

    #         # get min_median
    #         for client, times in timings[network][domain][size].items():
    #             median = np.median(times)

    #             # h3 client
    #             if client.count('h3') > 0:
    #                 min_h3_median = min(min_h3_median, median)
    #                 if min_h3_median == median:
    #                     min_h3_client = client
    #             # h2 client
    #             else:
    #                 min_h2_median = min(min_h2_median, median)
    #                 if min_h2_median == median:
    #                     min_h2_client = client

    #         diff = (min_h3_median - min_h2_median) / min_h2_median * 100
    #         data.append(diff)

    # fig, ax = plt.subplots()
    # im, cbar = heatmap(
    #     np.array(h2_vs_h3_data),
    #     h2_vs_h3_row_labels,
    #     h2_vs_h3_col_labels,
    #     ax=ax,
    #     cmap="bwr",
    #     # cbarlabel="% Growth in PLT from H2 to H3",
    #     vmin=-20,
    #     vmax=20,
    #     show_cbar=False,
    # )
    # annotate_heatmap(
    #     im, valfmt="{x:.1f}%", threshold=5, fontsize=24, fontweight=600)
    # fig.tight_layout()

    # multiple = ''
    # if sizes == MULTI_SIZES:
    #     multiple = '_multiple'

    # plt.savefig(
    #     '{}/Desktop/graphs_revised/facebook_patch{}'.format(Path.home(), multiple), transparent=True)

    # percent_diffs = []

    # data = []
    # row_labels = []
    # col_labels = [x.split('_')[0] for x in CLIENTS if x.count('h3') > 0]

    # for i, size in enumerate(SINGLE_SIZES):
    #     row_labels.append('{}/{}'.format(domain, size))
    #     row_data = []

    #     min_median = math.inf
    #     min_client = None

    #     # get min_mean
    #     for client, times in timings[network][domain][size].items():
    #         if client.count('h2') > 0:
    #             continue

    #         median = np.median(times)

    #         # h3 client
    #         min_median = min(min_median, median)
    #         if min_median == median:
    #             min_client = client

    #     for client in CLIENTS:
    #         if client.count('h2') > 0:
    #             continue

    #         times = timings[network][domain][size][client]

    #         median = np.median(times)
    #         diff = (median - min_median) / min_median * 100
    #         row_data.append(diff)

    #     data.append(row_data)

    # fig, ax = plt.subplots(figsize=(10, 5))
    # im, cbar = heatmap(
    #     np.transpose(data),
    #     col_labels,
    #     row_labels,
    #     ax=ax,
    #     cmap="Reds",
    #     # cbarlabel="Percent difference",
    #     vmin=0,
    #     vmax=30,
    #     rotation=20,
    #     show_cbar=True,
    # )
    # fig.tight_layout()
    # plt.savefig(
    #     '{}/Desktop/graphs_revised/H3_facebook_patch'.format(Path.home()), transparent=True)


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
            show_cbar=False,
        )
        annotate_heatmap(
            im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)
        fig.tight_layout()
        plt.savefig(Path.joinpath(
            GRAPHS_PATH, 'H3_{}'.format(dirname)), transparent=True)
        plt.close()
        # plt.show()


def h2_vs_h3(timings: object):
    for obj in NETWORK_V2:
        dirnames = obj['dirnames']
        col_labels = obj['labels']
        title = obj['title']

        data = []
        row_labels = []

        if title.count('Multi') > 0:
            sizes = MULTI_SIZES
        else:
            sizes = SINGLE_SIZES

        if title.count('PLT') > 0:
            metric = 'plt'
        elif title.count('Interactive') > 0:
            metric = 'interactive'
        else:
            metric = 'speed-index'

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
                            # k2, p = stats.normaltest(times)
                            # alpha = 0.05
                            # # print("p = {:g}".format(p))
                            # if p < alpha:
                            #     pass
                            #     # print("The null hypothesis can be rejected")
                            # else:
                            #     pass
                            #     # print("The null hypothesis cannot be rejected")

                            if size in MULTI_SIZES:
                                median = np.median(
                                    list(filter(None, times[metric]))) if metric in times else 1
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
        fig, axs = plt.subplots(1, 3, figsize=(12, len(dirnames) + 1), gridspec_kw={
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
                im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)

        for ax in axs.flat:
            ax.label_outer()

        fig.tight_layout()
        plt.savefig(Path.joinpath(
            GRAPHS_PATH, f'H2vsH3_{title}'), transparent=True)
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

    facebook_patch(timings, SINGLE_SIZES)
    # facebook_patch(timings, MULTI_SIZES)
    # h2_vs_h3(timings)
    # client_consistency(timings)
    # client_consistency_proxygen(timings)


if __name__ == "__main__":
    main()
