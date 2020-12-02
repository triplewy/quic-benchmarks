import argparse
import json
import numpy as np
import math
import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

from matplotlib.ticker import StrMethodFormatter
from mpl_toolkits.axes_grid1 import make_axes_locatable, axes_size
from pathlib import Path
from collections import Counter
from glob import glob

ANALYSIS_DIR = Path.joinpath(
    Path(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'analysis_data'
)

HAR_DIR = Path.joinpath(
    Path(os.path.dirname(os.path.abspath(__file__))),
    '..',
    'har'
)

NETWORK = [
    'revised_loss-0_delay-0_bw-10',
    'revised_loss-0dot1_delay-0_bw-10',
    'revised_loss-1_delay-0_bw-10',
    'revised_loss-0_delay-50_bw-10',
    'revised_loss-0_delay-100_bw-10'
]


def facebook_0dot1():
    domain = 'facebook'
    size = 'large'
    network = 'revised_loss-0dot1_delay-0_bw-10'

    data = {'LCP': {}}

    for chrome in ['chrome_h2', 'chrome_h3']:
        # get speed index file
        si_path = Path.joinpath(
            HAR_DIR, network, domain, size, f'{chrome}.json')
        har = None
        with open(si_path) as f:
            har = json.load(f)

        si = har['speed-index']
        siIndex = np.argsort(si)[len(si)//2]
        si_value = si[siIndex]
        fcp_value = har['first-contentful-paint'][siIndex]
        fmp_value = har['first-meaningful-paint'][siIndex]
        lcp_value = har['largest-contentful-paint'][siIndex]

        # data['SI'][chrome] = si_value
        # data['FCP'][chrome] = fcp_value
        # data['FMP'][chrome] = fmp_value
        data['LCP'][chrome] = lcp_value

        fmp_or_lcp = max(fmp_value, lcp_value)

        # get respective trace file
        analysis_path = Path.joinpath(
            ANALYSIS_DIR, network, domain, size, chrome, f'trace-{siIndex}.json')

        with open(analysis_path) as f:
            out = json.load(f)
            fcp = out['firstContentfulPaint']
            fmp = out['firstMeaningfulPaint']
            entries = out['entries']
            entries.sort(
                key=lambda x: x['_requestTime'] * 1000 + x['time'])
            start = sorted(entries, key=lambda x: x['_requestTime'])[
                0]['_requestTime'] * 1000
            end_entry = sorted(
                entries, key=lambda x: x['_requestTime'] * 1000 + x['time'])[-1]
            end = end_entry['_requestTime'] * 1000 + end_entry['time']

            wprfox_diff = fcp_value - fcp
            print(
                f'{chrome}, siIndex: {siIndex}, si: {si_value}, fcp: {fcp_value}, fmp: {fmp_value}, lcp: {lcp_value}')
            print('{}, {}'.format(chrome, len(out['painting'])))

            # graph painting events
            sub_data = []
            for k, v in out['painting'].items():
                x = v['endTime'] + wprfox_diff
                y = int(k.split('_')[1])
                sub_data.append([x, y])
            data[chrome] = sub_data

    fig, ax = plt.subplots(figsize=(12, 6))

    legend = [
        mpatches.Patch(color='red', label='Chrome H2'),
        mpatches.Patch(color='blue', label='Chrome H3'),
    ]

    for chrome in ['chrome_h2', 'chrome_h3']:
        color = 'red' if chrome == 'chrome_h2' else 'blue'
        points = data[chrome]
        ax.plot(
            [x[0] for x in points],
            [x[1] for x in points],
            color=color,
            marker='o',
            linestyle='-',
            linewidth=1,
            markersize=4,
        )

        textPos = len(points) - 6 if chrome == 'chrome_h2' else len(points) - 5
        ax.axvline(data['LCP'][chrome], color=color)
        plt.text(data['LCP'][chrome] + 1, textPos, 'LCP',
                 rotation=-90, color=color, size=16)
        # ax.axvline(big_image[chrome]['start'], color=color)
        # plt.text(big_image[chrome]['start'] + 1, textPos - 18, '[Start] Main image',
        #          rotation=-90, color=color, size=14)
        # ax.axvline(big_image[chrome]['end'], color=color)
        # plt.text(big_image[chrome]['end'] + 1, textPos - 18, '[End] Main image',
        #          rotation=-90, color=color, size=14)

    plt.ylabel('Painting Event Index', fontsize=18, labelpad=10)
    plt.xlabel('Time (ms)', fontsize=18, labelpad=10)
    ax.tick_params(axis='both', which='major', labelsize=16)
    ax.tick_params(axis='both', which='minor', labelsize=16)
    plt.rcParams["legend.fontsize"] = 16
    plt.legend(handles=legend)
    plt.show()


def facebook():
    domain = 'facebook'
    size = 'large'

    heatmap_data = []
    row_labels = {
        'SI': 'Speed Index',
        'css': 'css: mean end time',
        'img1': 'img1: end time',
        'img2': 'img2: end time',
    }
    row_data = ['SI', 'css', 'img1', 'img2']
    data_labels = ['SI', 'FCP', 'FMP', 'LCP',
                   'html', 'css', 'img1', 'img2', 'img3']
    col_labels = ['0% Loss', '0.1% Loss',
                  '1% Loss', '50ms Delay', '100ms Delay']

    for network in NETWORK:

        data = {k: {} for k in data_labels}

        for chrome in ['chrome_h2', 'chrome_h3']:
            # get speed index file
            si_path = Path.joinpath(
                HAR_DIR, network, domain, size, f'{chrome}.json')
            har = None
            with open(si_path) as f:
                har = json.load(f)

            si = har['speed-index']
            siIndex = np.argsort(si)[len(si)//2]
            si_value = si[siIndex]
            fcp_value = har['first-contentful-paint'][siIndex]
            fmp_value = har['first-meaningful-paint'][siIndex]
            lcp_value = har['largest-contentful-paint'][siIndex]

            data['SI'][chrome] = si_value
            data['FCP'][chrome] = fcp_value
            data['FMP'][chrome] = fmp_value
            data['LCP'][chrome] = lcp_value

            fmp_or_lcp = max(fmp_value, lcp_value)

            # get respective trace file
            analysis_path = Path.joinpath(
                ANALYSIS_DIR, network, domain, size, chrome, f'trace-{siIndex}.json')

            with open(analysis_path) as f:
                out = json.load(f)
                fcp = out['firstContentfulPaint']
                fmp = out['firstMeaningfulPaint']
                entries = out['entries']
                entries.sort(
                    key=lambda x: x['_requestTime'] * 1000 + x['time'])
                start = sorted(entries, key=lambda x: x['_requestTime'])[
                    0]['_requestTime'] * 1000
                end_entry = sorted(
                    entries, key=lambda x: x['_requestTime'] * 1000 + x['time'])[-1]
                end = end_entry['_requestTime'] * 1000 + end_entry['time']

                wprfox_diff = fcp_value - fcp
                print(
                    f'{chrome}, siIndex: {siIndex}, si: {si_value}, fcp: {fcp_value}, fmp: {fmp_value}, lcp: {lcp_value}')
                print('{}, {}'.format(chrome, len(out['painting'])))

                # graph painting events
                sub_data = []
                for k, v in out['painting'].items():
                    x = v['endTime'] + wprfox_diff
                    y = int(k.split('_')[1])
                    sub_data.append([x, y])
                data[chrome] = sub_data

                css = []
                for entry in entries:
                    if entry['response']['content']['mimeType'].count('image') == 0 \
                            and entry['response']['content']['mimeType'].count('css') == 0 \
                            and entry['response']['content']['mimeType'].count('html') == 0:
                        continue

                    request_start = entry['_requestTime'] * 1000 - start
                    request_end = request_start + entry['time']

                    if request_end >= fmp_or_lcp:
                        continue

                    if entry['request']['url'].startswith('https://scontent-bos3-1.xx.fbcdn.net/v/t39.2365-6/q85/s1225x1225/118295177_605348203497393_2957051395862871078_n.jpg'):
                        data['img1'][chrome] = request_end

                    if entry['request']['url'].startswith('https://scontent-bos3-1.xx.fbcdn.net/v/t39.8562-6/102526897_633611183895090_5100185621465399296_n.svg'):
                        data['img2'][chrome] = request_end

                    if entry['request']['url'].startswith('https://scontent-bos3-1.xx.fbcdn.net/v/t39.2365-6/109297962_278452039914962_4234169221247603965_n.svg'):
                        data['img3'][chrome] = request_end

                    if entry['response']['content']['mimeType'].count('css') > 0:
                        print(entry['request']['url'])
                        css.append(request_end)

                    if entry['request']['url'] == 'https://www.facebook.com/business/marketing-partners/':
                        data['html'][chrome] = request_end

                data['css'][chrome] = np.mean(css)

        diffs = []
        for key in row_labels:
            h2_val = data[key]['chrome_h2']
            h3_val = data[key]['chrome_h3']
            diffs.append((h3_val - h2_val) / h2_val * 100)
        heatmap_data.append(diffs)

    fig, ax = plt.subplots(figsize=(9, 6))
    # ax.set_title()
    ax.set_xlabel('Network Conditions', fontsize=18, labelpad=20)

    im, cbar = heatmap(
        np.transpose(heatmap_data),
        [row_labels[x] for x in row_data],
        col_labels,
        ax=ax,
        cmap="bwr",
        # cbarlabel="% Growth in time from H2 to H3",
        vmin=-20,
        vmax=20,
        rotation=20,
        show_cbar=False,
    )

    annotate_heatmap(
        im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)
    fig.tight_layout()
    plt.savefig(
        '{}/Desktop/graphs_revised/facebook_image_times'.format(Path.home()), transparent=True)
    plt.show()

    # fig, ax = plt.subplots(figsize=(12, 6))

    # legend = [
    #     mpatches.Patch(color='red', label='Chrome H2'),
    #     mpatches.Patch(color='blue', label='Chrome H3'),
    # ]

    # for chrome in ['chrome_h2', 'chrome_h3']:
    #     color = 'red' if chrome == 'chrome_h2' else 'blue'
    #     points = data[chrome]
    #     ax.plot(
    #         [x[0] for x in points],
    #         [x[1] for x in points],
    #         color=color,
    #         marker='o',
    #         linestyle='-',
    #         linewidth=1,
    #         markersize=4,
    #     )

    #     textPos = len(points) - 6 if chrome == 'chrome_h2' else len(points) - 5
    #     ax.axvline(lcps[chrome], color=color)
    #     plt.text(lcps[chrome] + 1, textPos, 'LCP',
    #              rotation=-90, color=color, size=16)
    #     ax.axvline(fcps[chrome], color=color)
    #     plt.text(fcps[chrome] + 1, textPos, 'FCP',
    #              rotation=-90, color=color, size=16)
    #     ax.axvline(big_image[chrome]['start'], color=color)
    #     plt.text(big_image[chrome]['start'] + 1, textPos - 18, '[Start] Main image',
    #              rotation=-90, color=color, size=14)
    #     ax.axvline(big_image[chrome]['end'], color=color)
    #     plt.text(big_image[chrome]['end'] + 1, textPos - 18, '[End] Main image',
    #              rotation=-90, color=color, size=14)

    # plt.ylabel('Painting Event Index', fontsize=18, labelpad=10)
    # plt.xlabel('Time (ms)', fontsize=18, labelpad=10)
    # ax.tick_params(axis='both', which='major', labelsize=16)
    # ax.tick_params(axis='both', which='minor', labelsize=16)
    # plt.rcParams["legend.fontsize"] = 16
    # plt.legend(handles=legend)
    # plt.show()


def cloudflare():
    # graph dimensions
    # rows: startTime, endTime
    # columns: network conditions
    img_url = 'https://blog.cloudflare.com/content/images/2020/04/image8-3.png'
    domain = 'cloudflare'
    size = 'large'
    data = []
    row_labels = ['startTime', 'endTime']
    col_labels = ['0% Loss', '0.1% Loss',
                  '1% Loss', '50ms Delay', '100ms Delay']

    for network in NETWORK:
        h2_start = None
        h2_end = None
        h3_start = None
        h3_end = None

        for chrome in ['chrome_h2', 'chrome_h3']:
            # get speed index files
            si_path = Path.joinpath(
                HAR_DIR, network, domain, size, f'{chrome}.json')
            si = []
            with open(si_path) as f:
                out = json.load(f)
                si = out['speed-index']

            siIndex = np.argsort(si)[len(si)//2]

            analysis_path = Path.joinpath(
                ANALYSIS_DIR, network, domain, size, chrome, f'trace-{siIndex}.json')

            startTime = None
            endTime = None

            with open(analysis_path) as f:
                out = json.load(f)
                entries = out['entries']
                entries.sort(key=lambda x: x['_requestTime'])
                start = entries[0]['_requestTime'] * 1000

                for entry in entries:
                    if entry['request']['url'] == img_url:
                        startTime = entry['_requestTime'] * 1000 - start
                        endTime = startTime + entry['time']

            if chrome == 'chrome_h2':
                h2_start = startTime
                h2_end = endTime
            else:
                h3_start = startTime
                h3_end = endTime

        start_diff = (h3_start - h2_start) / h2_start * 100
        end_diff = (h3_end - h2_end) / h2_end * 100
        data.append([start_diff, end_diff])

    fig, ax = plt.subplots(figsize=(8, 4))
    # ax.set_title()
    ax.set_ylabel('Image Resource', fontsize=18, labelpad=20)
    ax.set_xlabel('Network Conditions', fontsize=18, labelpad=20)

    im, cbar = heatmap(
        np.transpose(data),
        row_labels,
        col_labels,
        ax=ax,
        cmap="bwr",
        # cbarlabel="% Growth in time from H2 to H3",
        vmin=-40,
        vmax=40,
        rotation=20,
        show_cbar=False,
    )

    annotate_heatmap(
        im, valfmt="{x:.1f}%", threshold=5, fontsize=16, fontweight=600)
    fig.tight_layout()

    plt.savefig(
        '{}/Desktop/graphs_revised/cloudflare_image_times'.format(Path.home()), transparent=True)
    plt.show()


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


def analysis(filename: str):

    with open(filename, mode='r') as f:
        return json.load(f)


def get_event_types(out: dict, key: str):
    time = out[key]
    networking = out['networking']
    events = []

    for event in networking.values():
        if event['endTime'] < time:
            events.append(event)

    counter = Counter()
    for event in events:
        counter[event['mimeType']] += 1

    return counter


def dict_union(d1: dict, d2: dict):
    res = {}
    for k in d1.keys():
        if k in d2:
            res[k] = min(d1[k], d2[k])
    return res


def main():
    # cloudflare()
    facebook_0dot1()

    parser = argparse.ArgumentParser()
    parser.add_argument("analysis_dir")
    parser.add_argument("har_dir")

    args = parser.parse_args()

    analysis_dir = Path(args.analysis_dir)
    har_dir = Path(args.har_dir)

    for chrome in ['chrome_h2', 'chrome_h3']:

        har = None
        with open(Path.joinpath(har_dir, f'{chrome}.json')) as f:
            har = json.load(f)

        si = har['speed-index']
        siIndex = np.argsort(si)[len(si)//2]

        print(f'median speed index: {si[siIndex]}, median index: {siIndex}')
        print('fcp: {}, fmp: {}, lcp: {}'.format(
            har['first-contentful-paint'][siIndex],
            har['first-meaningful-paint'][siIndex],
            har['largest-contentful-paint'][siIndex],
        ))

        with open(Path.joinpath(analysis_dir, chrome, f'trace-{siIndex}.json')) as f:
            out = json.load(f)

            print('fcp: {}, fmp: {}'.format(
                out['firstContentfulPaint'], out['firstMeaningfulPaint']))

            entries = out['entries']

            h2 = []
            h3 = []
            for entry in entries:
                if entry['response']['httpVersion'] == 'h3-29':
                    h3.append(entry)
                else:
                    h2.append(entry)

            # print([(x['request']['url'], x['response']['content']['mimeType'])
            #        for x in h2])
            # print([(x['request']['url'], x['response']['content']['mimeType'])
            #        for x in h3])
        # files = glob(
        #     '{}/**/*.json'.format(Path.joinpath(analysis_dir, chrome)), recursive=True)

        # outs = []
        # fcps = []
        # fmps = []
        # networkTimes = []

        # num_c_paints = Counter()
        # num_m_paints = Counter()

        # for f in files:
        #     out = analysis(f)
        #     outs.append(out)

        #     fcp = out['firstContentfulPaint']
        #     fmp = out['firstMeaningfulPaint']

        #     num_c_paints[len(
        #         [x for x in out['loading'].values() if x['endTime'] <= fcp])] += 1
        #     num_m_paints[len(
        #         [x for x in out['loading'].values() if x['endTime'] <= fmp])] += 1

        #     entries = out['entries']
        #     entries.sort(key=lambda x: x['_requestTime'] * 1000 + x['time'])

        #     fcps.append(fcp)
        #     fmps.append(fmp)

        #     networkTimes.append(entries[-1]['_requestTime'] * 1000 +
        #                         entries[-1]['time'] - entries[0]['_requestTime'] * 1000)

        # fcpIndex = np.argsort(fcps)[len(fcps)//2]
        # fmpIndex = np.argsort(fmps)[len(fmps)//2]
        # ntIndex = np.argsort(networkTimes)[len(networkTimes)//2]
        # print(
        #     f'firstContentfulPaint: {fcps[fcpIndex]}, index: {fcpIndex}, networkTime: {networkTimes[fcpIndex]}')
        # print(
        #     f'firstMeaningfulPaint: {fmps[fmpIndex]}, index: {fmpIndex}, networkTime: {networkTimes[fmpIndex]}')

        # print(f'fcpPaints: {num_c_paints}, fmpPaints: {num_m_paints}')

        # min_c_types = None
        # min_m_types = None

        # for out in outs:
        #     if out['firstContentfulPaint'] == fcps[fcpIndex]:
        #         c_types = get_event_types(out, 'firstContentfulPaint')
        #         if min_c_types is None:
        #             min_c_types = c_types
        #         min_c_types = dict_union(min_c_types, c_types)

        #     if out['firstMeaningfulPaint'] == fmps[fmpIndex]:
        #         m_types = get_event_types(out, 'firstMeaningfulPaint')
        #         if min_m_types is None:
        #             min_m_types = m_types
        #         min_m_types = dict_union(min_m_types, m_types)

        # print('contentful_counter', min_c_types)
        # print('meaningful_counter', min_m_types)


if __name__ == "__main__":
    main()
