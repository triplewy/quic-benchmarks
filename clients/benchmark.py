import sys
import json
import time
import argparse
import random
import subprocess

from urllib.parse import urlparse
from pathlib import Path

ITERATIONS = 25
RETRIES = 10
CLIENTS = ['proxygen_h3', 'ngtcp2_h3', 'chrome']
DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']


PATHS = {}
with open('paths.json') as f:
    PATHS = json.load(f)

Path('/tmp/logs').mkdir(parents=True, exist_ok=True)
Path('/tmp/qlog').mkdir(parents=True, exist_ok=True)


def shuffle_clients():
    arr = ['proxygen_h3', 'ngtcp2_h3', 'chrome']
    random.shuffle(arr)
    return arr


def shuffle_domains():
    arr = ['facebook', 'cloudflare', 'google']
    random.shuffle(arr)
    return arr


def query(client: str, url: str):
    timings = []

    for i in range(ITERATIONS):
        print('{} - {} - Iteration: {}'.format(client, url, i))

        elapsed = run_process(client, url)

        timings.append(elapsed)
        print(client, elapsed)

    return timings


def run_process(client: str, url: str):
    url_obj = urlparse(url)
    url_host = url_obj.netloc
    url_path = url_obj.path[1:]
    url_port = '443'

    if client == 'ngtcp2_h3':
        return run_subprocess(
            [
                '{}'.format(PATHS['ngtcp2']),
                '--quiet',
                '--exit-on-all-streams-close',
                '--max-data=1073741824',
                '--max-stream-data-uni=1073741824',
                '--max-stream-data-bidi-local=1073741824',
                '--qlog-file=/tmp/qlog/.qlog',
                url_host,
                url_port,
                url
            ]
        )
    elif client == 'proxygen_h3':
        if url_host.count(':') > 0:
            [host, port] = url_host.split(':')
        else:
            host = url_host
            port = 443

        return run_subprocess(
            [
                '{}'.format(PATHS['proxygen']),
                '--log_response=false',
                '--mode=client',
                '--stream_flow_control=1073741824',
                '--conn_flow_control=1073741824',
                '--use_draft=true',
                '--draft-version=29',
                '--qlogger_path=/tmp/qlog',
                '--host={}'.format(host),
                '--port={}'.format(port),
                '--path=/{}'.format(url_path),
                '--v=0',
            ]
        )
    else:
        raise 'Invalid client'


def run_subprocess(command: list) -> float:
    subprocess.run(command)

    return get_time_from_qlog()


def get_time_from_qlog() -> float:
    with open('/tmp/qlog/.qlog', mode='r') as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        start = int(events[0][0])

        last = len(events) - 1
        while len(events[last]) == 0:
            last -= 1

        end = int(events[last][0])

        if time_units == 'ms':
            return end - start

        return end / 1000 - start / 1000


def main():
    # Get network scenario from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('loss')
    parser.add_argument('delay')
    parser.add_argument('bw')

    args = parser.parse_args()

    loss = args.loss
    delay = args.delay
    bw = args.bw

    endpoints = {}

    # Read endpoints from endpoints.json
    with open('endpoints.json', 'r') as f:
        endpoints = json.load(f)

    print('{} loss, {} delay, {} bw'.format(loss, delay, bw))

    for client in shuffle_clients():

        if client == 'chrome':
            subprocess.run(['node', 'chrome.js', loss, delay, bw])
            continue

        for domain in shuffle_domains():

            urls = endpoints[domain]

            for size in SIZES:
                dirpath = Path.joinpath(
                    Path.cwd(),
                    'har',
                    'loss-{}_delay-{}_bw-{}'.format(loss, delay, bw),
                    domain,
                    size
                )
                Path(dirpath).mkdir(parents=True, exist_ok=True)

                filepath = Path.joinpath(
                    dirpath,
                    "{}.json".format(client)
                )

                timings = []
                try:
                    with open(filepath, 'r') as f:
                        timings = json.load(f)
                except:
                    pass

                result = query(client, urls[size])

                timings += result

                with open(filepath, 'w') as f:
                    json.dump(timings, f)


if __name__ == "__main__":
    main()
