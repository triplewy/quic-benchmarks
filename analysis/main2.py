import os
import json
import math
import argparse
import numpy as np

from pathlib import Path
from scipy import stats
from glob import glob


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir')

    args = parser.parse_args()

    dirpath = Path(args.dir)

    files = glob('{}/**/*.qlog'.format(dirpath), recursive=True)

    timings = {}

    h2_min = (None, math.inf)
    h3_min = (None, math.inf)

    for filepath in files:
        with open(filepath, mode='r') as f:
            times = json.load(f)

            timings[filepath] = times

            mean = np.mean(times)

            # h3 client
            if filepath.count('h3') > 0:
                if mean < h3_min[1]:
                    h3_min = (filepath, mean)
            # h2 client
            else:
                if mean < h2_min[1]:
                    h2_min = (filepath, mean)

    # do t-test between min h2 and min h3 clients
    if h2_min[0] is not None and h3_min[0] is not None:
        ttest = stats.ttest_ind(
            timings[h2_min[0]],
            timings[h3_min[0]],
            equal_var=False
        )

        # accept null hypothesis
        if ttest.pvalue >= 0.01:
            print('H2 and H3 performance are equivalent')
        # reject null hypothesis
        else:
            diff = (h3_min[1] - h2_min[1]) / h2_min[1] * 100
            print('H3 differs from H2 by: {}%'.format(diff))

    h3_timings = [(k, v) for k, v in timings.items() if k.count('h3') > 0]

    # do t-test between h3 clients
    if len(h3_timings) > 1:
        for k, v in h3_timings:
            ttest = stats.ttest_ind(
                timings[k],
                timings[h3_min[0]],
                equal_var=False
            )

            # accept null hypothesis
            if ttest.pvalue >= 0.01:
                print('H3 clients performance are equivalent')
            # reject null hypothesis
            else:
                diff = (v - h3_min[1]) / h3_min[1] * 100
                print('H3 clients differs by: {}%'.format(diff))


if __name__ == "__main__":
    main()
