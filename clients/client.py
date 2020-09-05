import argparse
import subprocess
import time
import json
import sys

from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 20
RETRIES = 10
DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']

Path('/tmp/qlog').mkdir(parents=True, exist_ok=True)

# DOMAINS = ['google', 'cloudflare']
# SIZES = ['1MB']

PATHS = {}
with open('paths.json') as f:
    PATHS = json.load(f)


def query(client: str, url: str):
    timings = []

    for i in range(ITERATIONS):
        print('{} - {} - Iteration: {}'.format(client, url, i))

        elapsed = run_process(client, url) * 1000

        timings.append(elapsed)
        print(client, elapsed)

    return timings


def run_process(client: str, url: str):
    url_obj = urlparse(url)
    url_host = url_obj.netloc
    url_path = url_obj.path[1:]
    url_port = '443'

    if client == 'curl_h2':
        return run_subprocess(
            client,
            [
                'curl',
                '--silent',
                '--output', '/dev/null',
                '--connect-timeout', '5',
                '--max-time', '120',
                '--http2', url
            ]
        )

    elif client == 'ngtcp2_h3':
        return run_subprocess(
            client,
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
            client,
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


def run_subprocess(client: str, command: list) -> float:
    output = subprocess.run(
        ['time'] + command,
        capture_output=True
    )

    if client.count('h3') > 0:
        return get_time_from_qlog() / 1000

    output = output.stderr.decode().split('\n')[-2]
    output = output.split()

    return float(output[0])


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
    parser.add_argument('client')
    parser.add_argument('loss')
    parser.add_argument('delay')
    parser.add_argument('bw')

    args = parser.parse_args()

    client = args.client
    loss = args.loss
    delay = args.delay
    bw = args.bw

    # Read endpoints from endpoints.json
    with open('endpoints.json', 'r') as f:
        endpoints = json.load(f)

    for domain in DOMAINS:
        urls = endpoints[domain]
        for size in SIZES:
            dirpath = Path.joinpath(
                Path.cwd(),
                'har',
                'loss-{}_delay-{}_bw-{}'.format(loss, delay, bw),
                domain,
                size,
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

            timings = timings[20:] + result

            with open(filepath, 'w') as f:
                json.dump(timings, f)


if __name__ == "__main__":
    main()
