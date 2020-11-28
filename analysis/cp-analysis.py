import argparse
import json
import numpy as np
import math

from pathlib import Path
from collections import Counter
from glob import glob


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
    parser = argparse.ArgumentParser()
    parser.add_argument("dir")

    args = parser.parse_args()

    dirname = Path(args.dir)

    for chrome in ['chrome_h2', 'chrome_h3']:
        files = glob(
            '{}/**/*.json'.format(Path.joinpath(dirname, chrome)), recursive=True)

        outs = []
        fcps = []
        fmps = []
        networkTimes = []

        num_c_paints = Counter()
        num_m_paints = Counter()

        for f in files:
            out = analysis(f)
            outs.append(out)

            fcp = out['firstContentfulPaint']
            fmp = out['firstMeaningfulPaint']

            num_c_paints[len(
                [x for x in out['loading'].values() if x['endTime'] <= fcp])] += 1
            num_m_paints[len(
                [x for x in out['loading'].values() if x['endTime'] <= fmp])] += 1

            entries = out['entries']
            entries.sort(key=lambda x: x['_requestTime'] * 1000 + x['time'])

            fcps.append(fcp)
            fmps.append(fmp)

            networkTimes.append(entries[-1]['_requestTime'] * 1000 +
                                entries[-1]['time'] - entries[0]['_requestTime'] * 1000)

        fcpIndex = np.argsort(fcps)[len(fcps)//2]
        fmpIndex = np.argsort(fmps)[len(fmps)//2]
        ntIndex = np.argsort(networkTimes)[len(networkTimes)//2]
        print(
            f'firstContentfulPaint: {fcps[fcpIndex]}, index: {fcpIndex}, networkTime: {networkTimes[fcpIndex]}')
        print(
            f'firstMeaningfulPaint: {fmps[fmpIndex]}, index: {fmpIndex}, networkTime: {networkTimes[fmpIndex]}')

        print(f'fcpPaints: {num_c_paints}, fmpPaints: {num_m_paints}')

        min_c_types = None
        min_m_types = None

        for out in outs:
            if out['firstContentfulPaint'] == fcps[fcpIndex]:
                c_types = get_event_types(out, 'firstContentfulPaint')
                if min_c_types is None:
                    min_c_types = c_types
                min_c_types = dict_union(min_c_types, c_types)

            if out['firstMeaningfulPaint'] == fmps[fmpIndex]:
                m_types = get_event_types(out, 'firstMeaningfulPaint')
                if min_m_types is None:
                    min_m_types = m_types
                min_m_types = dict_union(min_m_types, m_types)

        print('contentful_counter', min_c_types)
        print('meaningful_counter', min_m_types)
    # associate(outs[fcpIndex])
    # associate(outs[fmpIndex])


if __name__ == "__main__":
    main()
