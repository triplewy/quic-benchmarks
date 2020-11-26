import argparse
import json
import numpy as np

from pathlib import Path
from collections import Counter
from glob import glob


def analysis(filename: str):

    with open(filename, mode='r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    dirname = Path(args.dir)

    for chrome in ['chrome_h2', 'chrome_h3']:
        files = glob(
            '{}/**/*.json'.format(Path.joinpath(dirname, chrome)), recursive=True)

        counter = Counter()
        cp_network_starts = []
        fcps = []
        networkingTimeCps = []
        loadingTimeCps = []
        scriptingTimeCps = []

        for f in files:
            out = analysis(f)

            cp_network = [x for x in out['criticalPath']
                          if x['activityId'].count('Networking') > 0]
            cp_network_start = [x['startTime'] for x in cp_network]
            cp_network_starts.append(cp_network_start)

            entries = out['entries']

            fcps.append(out['firstContentfulPaint'])
            networkingTimeCps.append(out['networkingTimeCp'])
            loadingTimeCps.append(out['loadingTimeCp'])
            scriptingTimeCps.append(out['scriptingTimeCp'])

            counter[len(cp_network_start)] += 1

        print(chrome, 'cp_network counter', counter)

        agg_cp_network_starts = [[] for _ in range(max(list(counter.keys())))]

        for i in range(len(agg_cp_network_starts)):
            for cp_network_start in cp_network_starts:
                if i >= len(cp_network_start):
                    continue
                agg_cp_network_starts[i].append(cp_network_start[i])

        agg_cp_network_starts_medians = [None] * len(agg_cp_network_starts)

        for i in range(len(agg_cp_network_starts)):
            agg_cp_network_starts_medians[i] = np.median(
                agg_cp_network_starts[i])

        print('agg_cp_network_starts_medians', agg_cp_network_starts_medians)
        print('firstContentfulPaint', np.median(fcps))
        print('networkingTimeCp', np.median(networkingTimeCps))
        print('loadingTimeCp', np.median(loadingTimeCps))
        print('scriptingTimeCp', np.median(scriptingTimeCps))


if __name__ == "__main__":
    main()
