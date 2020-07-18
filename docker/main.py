import sys
import json
import subprocess
import os
import argparse
import docker
import numpy as np

from pathlib import Path
from glob import glob
from urllib.parse import urlparse

clients = ['mvfst', 'aioquic', 'ngtcp2', 'quiche', 'picoquic', 'quant']
docker_client = docker.from_env()


def run(client: str, url: str, qlog_dir: str, iterations: int, output: str = None):
    times = {}

    if client == 'all':
        for client in clients:
            times[client] = run_docker(client, url, qlog_dir, iterations)
    else:
        times[client] = run_docker(client, url, qlog_dir, iterations)

    for client, arr in times.items():
        min_time = round(np.min(arr), 2)
        max_time = round(np.max(arr), 2)
        median = round(np.median(arr), 2)
        mean = round(np.mean(arr), 2)
        std = round(np.std(arr), 2)
        print(
            '''{0}
{1: <10} {2: <10} {3: <10} {4: <10} {5: <10}
{6: <10} {7: <10} {8: <10} {9: <10} {10: <10}
            '''.format(client,
                       'Mean', 'Std.Dev.', 'Min', 'Median', 'Max',
                       mean, std, min_time, median, max_time))

    if output is not None:
        with open(output, 'w') as f:
            json.dump(times, f)


def run_docker(client: str, url: str, qlog_dir: str, iterations: int):
    """Runs the client process once and exports qlog to the qlog directory

    Args:
        client (str): [description]
        url (str): [description]
        qlog_dir (str): [description]
    """

    # Make sure qlog_dir + client exists
    qlog_dir = Path.joinpath(Path(qlog_dir), client)
    Path(qlog_dir).mkdir(parents=True, exist_ok=True)

    url_obj = urlparse(url)
    url_host = url_obj.netloc
    url_path = url_obj.path
    url_port = '443'

    print('Running {}...'.format(client))

    if client == 'mvfst':
        cmd = '''-c \'for _ in {{1..{}}}; do \
            /proxygen/proxygen/_build/proxygen/httpserver/hq \
            --log_response=false \
            --mode=client \
            --stream_flow_control=1073741824 \
            --conn_flow_control=1073741824 \
            --use_draft=true \
            --protocol=h3-29 \
            --qlogger_path=/qlog \
            --host={} \
            --port={} \
            --path={} \
            --v=0; done\''''.format(iterations, url_host, url_port, url_path)

        container = docker_client.containers.run(
            image='lnicco/mvfst-qns',
            name='mvfst',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    elif client == 'aioquic':
        cmd = '''-c \'for _ in {{1..{}}}; do \
            python3 \
            /aioquic/examples/http3_client.py \
            --max-data=1073741824 \
            --max-stream-data=1073741824 \
            --quic-log=/qlog \
            {}; done\''''.format(iterations, url)

        container = docker_client.containers.run(
            image='aiortc/aioquic-qns',
            name='aioquic',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    elif client == 'ngtcp2':
        cmd = '''-c \'for _ in {{1..{}}}; do \
            client \
            --quiet \
            --exit-on-all-streams-close \
            --max-data=1073741824 \
            --max-stream-data-uni=1073741824 \
            --max-stream-data-bidi-local=1073741824 \
            --cc=cubic \
            --qlog-dir=/qlog \
            {} \
            {} \
            {}; done\''''.format(iterations, url_host, url_port, url)

        container = docker_client.containers.run(
            image='ngtcp2/ngtcp2-interop',
            name='ngtcp2',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    elif client == 'quiche':
        cmd = '''-c \'for _ in {{1..{}}}; do \
            /quiche/quiche-client \
            --max-data=1073741824 \
            --max-stream-data=1073741824 \
            {} \
            > /dev/null; done\''''.format(iterations, url)

        container = docker_client.containers.run(
            image='cloudflare/quiche-qns',
            name='quiche',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            environment=['QLOGDIR=/qlog', 'RUST_LOG=info'],
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    elif client == 'quant':
        cmd = '''-c \'for _ in {{1..{}}}; do \
            /usr/local/bin/client \
            -3 \
            -i eth0 \
            -t 150 \
            -x 50 \
            -e 0xff00001d \
            -q /qlog \
            {}; done\''''.format(iterations, url)

        container = docker_client.containers.run(
            image='ntap/quant:latest',
            name='quant',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    elif client == 'picoquic':
        cmd = '''-c \'mkdir -p /logs && for _ in {{1..{}}}; do \
            /picoquic/picoquicdemo \
            -b /logs/client_log.bin \
            {} \
            {} \
            {} && \
            /picoquic/picolog_t \
            -f qlog \
            -o /qlog /logs/client_log.bin && \
            rm /logs/client_log.bin; done\''''.format(iterations, url_host, url_port, url_path)

        container = docker_client.containers.run(
            image='privateoctopus/picoquic:latest',
            name='picoquic',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            environment=['QLOGDIR=/qlog'],
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    elif client == 'neqo':
        cmd = '''-c \'for _ in {{1..{}}}; do \
            /neqo/target/neqo-client \
            --qlog-dir=/qlog \
            {} > /dev/null; done\''''.format(iterations, url)

        container = docker_client.containers.run(
            image='neqoquic/neqo-qns:latest',
            name='neqo',
            command=cmd,
            detach=True,
            auto_remove=True,
            entrypoint='/bin/bash',
            environment=['RUST_LOG='],
            volumes={qlog_dir: {'bind': '/qlog', 'mode': 'rw'}},
        )

    else:
        raise 'Invalid client'

    for chunk in container.logs(stdout=True, stderr=True, stream=True):
        chunk = chunk.decode()
        chunk = chunk.strip('\r\n')
        print(chunk)

    return [qlog_duration(qlog) for qlog in Path(qlog_dir).glob('**/*.qlog')]


def run_firefox(client: str, url: str, qlog_dir: str, iterations: int):
    """[summary]

    Args:
        client (str): [description]
        url (str): [description]
        qlog_dir (str): [description]
        iterations (int): [description]
    """
    pass


def qlog_duration(filename: str) -> float:
    """Reads a qlog file and returns the duration from the start to connection close

    Args:
        filename (str): file path of the qlog file

    Returns:
        float: total duration
    """

    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        vantage = traces['vantage_point']
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'
        start = int(events[0][0])

        end_index = len(events) - 1
        while end_index >= 0:
            if not events[end_index] or len(events[end_index]) != 4:
                end_index -= 1
                continue

            event_data = events[end_index][3]
            if 'frames' not in event_data:
                end_index -= 1
                continue

            found = False
            for frame in event_data['frames']:
                if frame['frame_type'] == 'connection_close':
                    found = True
                    break

            if found:
                break

            end_index -= 1

        if end_index == 0:
            end = int(events[-1][0])
        else:
            end = int(events[end_index][0])

        if time_units == 'ms':
            return end - start

        return end / 1000 - start / 1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--client',
        default='all',
        choices=['all'] + clients,
        help='QUIC clients to benchmark. \'all\' benchmarks all clients at once'
    )
    parser.add_argument(
        '--url',
        help='QUIC server URL endpoint',
        required=True,
    )
    parser.add_argument(
        '--qlog-dir',
        help='directory path to save qlogs',
        default='/tmp/qlog',
    )
    parser.add_argument(
        '--output',
        help='path to save results'
    )
    parser.add_argument(
        '--n',
        help='number of iterations to run',
        type=int,
        default=10,
    )

    args = parser.parse_args()

    client = args.client
    url = args.url
    qlog_dir = args.qlog_dir
    iterations = args.n
    output = args.output

    run(client, url, qlog_dir, iterations, output=output)


if __name__ == '__main__':
    main()
