import argparse
import subprocess
import time
import json
import sys

from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 25
RETRIES = 10
DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']


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
            [
                '{}/ngtcp2/examples/client'.format(Path.home()),
                '--quiet',
                '--exit-on-all-streams-close',
                '--max-data=1073741824',
                '--max-stream-data-uni=1073741824',
                '--max-stream-data-bidi-local=1073741824',
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
                '{}/proxygen-clone/proxygen/_build/proxygen/httpserver/hq'.format(
                    Path.home()),
                '--log_response=false',
                '--mode=client',
                '--stream_flow_control=1073741824',
                '--conn_flow_control=1073741824',
                '--use_draft=true',
                '--draft-version=29',
                '--host={}'.format(host),
                '--port={}'.format(port),
                '--path=/{}'.format(url_path),
                '--v=0',
            ]
        )
    else:
        raise 'Invalid client'


def run_subprocess(command: list) -> float:
    output = subprocess.run(
        ['time'] + command,
        capture_output=True
    )

    output = output.stderr.decode().split('\n')[-2]
    output = output.split()

    return float(output[0])


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

            timings += result

            with open(filepath, 'w') as f:
                json.dump(timings, f)


if __name__ == "__main__":
    main()
