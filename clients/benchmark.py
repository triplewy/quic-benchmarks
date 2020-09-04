import random
import subprocess

SCENARIOS = [
    ('0', '0'),
    ('0dot1', '0'),
    ('1', '0'),
    ('0', '50'),
    ('0', '100'),
]


def shuffle():
    arr = [1, 2, 3, 4]
    random.shuffle(arr)
    return arr


def benchmark(loss: str, delay: str):
    if loss == '0dot1':
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--loss', '0.1%' '--direction', 'incoming'])
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--loss', '0.1%', '--direction', 'outgoing'])
    elif loss == '1':
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--loss', '1%' '--direction', 'incoming'])
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--loss', '1%', '--direction', 'outgoing'])
    elif delay == '50':
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--delay', '50ms' '--direction', 'incoming'])
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--delay', '50ms', '--direction', 'outgoing'])
    elif delay == '100':
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--delay', '100ms' '--direction', 'incoming'])
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--delay', '100ms', '--direction', 'outgoing'])
    else:
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--direction', 'incoming'])
        subprocess.run(['sudo', 'tcset', 'ens192', '--rate',
                        '100mbps', '--direction', 'outgoing'])

    order = shuffle()

    for num in order:
        # chrome
        if order == 1:
            args = [
                'node',
                'chrome.js',
                loss,
                delay,
                '100'
            ]
        # curl
        elif order == 2:
            args = [
                'python3',
                'client.py',
                'curl_h2',
                loss,
                delay,
                '100'
            ]
        # ngtcp2
        elif order == 3:
            args = [
                'python3',
                'client.py',
                'ngtcp2_h3',
                loss,
                delay,
                '100'
            ]
        # proxygen
        else:
            args = [
                'python3',
                'client.py',
                'proxygen_h3',
                loss,
                delay,
                '100'
            ]

    subprocess.run(args)

    # Delete all tc rules
    subprocess.run(
        'sudo',
        'tcdel',
        'ens192',
        '--all',
    )


def main():
    for _ in range(2):
        for (loss, delay) in SCENARIOS:
            benchmark(loss, delay)


if __name__ == "__main__":
    main()
