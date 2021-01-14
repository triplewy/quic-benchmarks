import argparse
import json
import numpy as np

from glob import glob


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir')

    args = parser.parse_args()

    dirpath = args.dir

    files = glob('{}/**/*.json'.format(dirpath), recursive=True)
    files.sort(reverse=True)

    tcp_mss = None
    quic_mss = None

    for metrics_file in files:
        with open(metrics_file, mode='r') as f:
            metrics = json.load(f)

            init_cwnd_bytes = [x['init_cwnd_bytes'] for x in metrics]
            init_cwnd_mss = [x['init_cwnd_mss'] for x in metrics]

            median_index = np.argsort(init_cwnd_bytes)[
                len(init_cwnd_bytes)//2]

            median_bytes = init_cwnd_bytes[median_index]
            median_mss = init_cwnd_mss[median_index]

            if median_mss > 0:
                if metrics_file.count('h2') > 0 and tcp_mss is None:
                    tcp_mss = median_bytes / median_mss
                if metrics_file.count('h3') > 0 and quic_mss is None:
                    quic_mss = median_bytes / median_mss
            else:
                mss = tcp_mss if metrics_file.count('h2') > 0 else quic_mss
                median_mss = median_bytes / mss

            print(metrics_file, median_mss, median_bytes)


if __name__ == "__main__":
    main()
