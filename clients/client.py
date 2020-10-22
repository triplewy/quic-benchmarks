import argparse
import subprocess
import time
import json
import sys
import pathlib

from pathlib import Path
from urllib.parse import urlparse

CONFIG = None
ENDPOINTS = None

with open(Path.joinpath(pathlib.Path(__file__).parent.absolute(), '..', 'config.json'), mode='r') as f:
    CONFIG = json.load(f)

with open(Path.joinpath(pathlib.Path(__file__).parent.absolute(), '..', 'endpoints.json'), mode='r') as f:
    ENDPOINTS = json.load(f)

PATHS = CONFIG['paths']
ITERATIONS = CONFIG['iterations']
RETRIES = 10
DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']

Path('/tmp/qlog').mkdir(parents=True, exist_ok=True)
script_dir = Path(__file__).parent.absolute()


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
                PATHS['curl'],
                '--insecure',
                '-s',
                '-w', '@{}/curl-format.txt'.format(script_dir),
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
                PATHS['ngtcp2'],
                '--quiet',
                '--exit-on-all-streams-close',
                '--max-data=1073741824',
                '--max-stream-data-uni=1073741824',
                '--max-stream-data-bidi-local=1073741824',
                '--group=X25519',
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
                PATHS['proxygen'],
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
        command,
        capture_output=True
    )

    if client.count('h3') > 0:
        return get_time_from_qlog() / 1000

    output = output.stdout.decode().split('\n')
    dns = float(output[0].split(':')[1])
    total = float(output[-1].split(':')[1])

    return total - dns


def get_time_from_qlog() -> float:
    with open('/tmp/qlog/.qlog', mode='r') as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        start = None
        end = None

        for event in events:
            if not event:
                continue

            if time_units == 'ms':
                ts = int(event[0])
            else:
                ts = int(event[0]) / 1000

            event_type = event[2]
            event_data = event[3]

            if event_type.lower() == 'packet_sent' and start is None:
                start = ts

        last = len(events) - 1
        while len(events[last]) == 0:
            last -= 1

        end = int(events[last][0]) if time_units == 'ms' else int(
            events[last][0]) / 1000

        return end - start


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

    for domain in DOMAINS:
        urls = ENDPOINTS[domain]
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

            # timings += result
            timings = result

            with open(filepath, 'w') as f:
                json.dump(timings, f)


if __name__ == "__main__":
    main()
