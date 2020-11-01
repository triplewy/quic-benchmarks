import argparse
import subprocess
import time
import json
import sys
import pathlib
import docker
import os
import random
import numpy as np

from pathlib import Path
from urllib.parse import urlparse
from docker.types import LogConfig

DOCKER_CLIENT = docker.from_env()

DOCKER_CONFIG = {}
CONFIG = {}
ENDPOINTS = {}

with open(Path.joinpath(pathlib.Path(__file__).parent.absolute(), '..', 'docker.json'), mode='r') as f:
    DOCKER_CONFIG = json.load(f)

with open(Path.joinpath(pathlib.Path(__file__).parent.absolute(), '..', 'config.json'), mode='r') as f:
    CONFIG = json.load(f)

with open(Path.joinpath(pathlib.Path(__file__).parent.absolute(), '..', 'endpoints.json'), mode='r') as f:
    ENDPOINTS = json.load(f)

ITERATIONS = CONFIG['iterations']
RETRIES = 10

Path('/tmp/qlog').mkdir(parents=True, exist_ok=True)


def query(client: str, url: str, dirpath: str):
    timings = []

    for i in range(ITERATIONS):
        print('{} - {} - Iteration: {}'.format(client, url, i))

        elapsed = run_docker(client, url, Path.joinpath(
            dirpath, '{}_{}.qlog'.format(client, i))) * 1000

        timings.append(elapsed)
        print(client, elapsed)

    return timings


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


def run_docker(client: str, url: str, filepath: str) -> float:
    # Parse URL object
    url_obj = urlparse(url)
    url_host = url_obj.netloc
    url_path = url_obj.path
    if url_host.count(':') > 0:
        [url_host, url_port] = url_host.split(':')
    else:
        url_port = '443'

    docker_config = DOCKER_CONFIG.get(client)

    if docker_config is None:
        raise Exception('client {} is not valid'.format(client))

    image = docker_config['image']

    # Check if image exists
    try:
        DOCKER_CLIENT.images.get(image)
    except docker.errors.ImageNotFound:
        print('Pulling docker image: {}'.format(image))
        DOCKER_CLIENT.images.pull(image)
    except Exception as e:
        raise e

    # Modify commands
    commands = []
    for command in docker_config['commands']:
        command = command.replace('{url}', url)
        command = command.replace('{host}', url_host)
        command = command.replace('{path}', url_path)
        command = command.replace('{port}', url_port)
        commands.append(command)

    args = {
        'detach': True,
        'auto_remove': False,
        'volumes': {
            '/tmp/qlog': {
                'bind': '/logs',
                'mode': 'rw',
            }
        },
        'log_config': LogConfig(type=LogConfig.types.JSON, config={'max-size': '1g'}),
        'command': commands
    }

    if 'entrypoint' in docker_config:
        args['entrypoint'] = docker_config['entrypoint']

    container = DOCKER_CLIENT.containers.run(
        image,
        **args
    )
    container.wait()
    out = container.logs()
    out = out.decode('utf-8')

    if client == 'curl':
        out_arr = out.split('\n')[:-1]
        dns_time = float(out_arr[0].split(':')[1])
        total_time = float(out_arr[1].split(':')[1])
        return total_time - dns_time

    if len(os.listdir('/tmp/qlog')) == 0:
        raise 'no qlog created'

    logpath = Path.joinpath(
        Path('/tmp/qlog'), os.listdir('/tmp/qlog')[0])

    time = get_time_from_qlog(logpath)

    os.rename(logpath, filepath)

    return time


def get_time_from_qlog(qlog: str) -> float:
    with open(qlog, mode='r') as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        start = None
        end = 0

        for event in events:
            if not event:
                continue

            if time_units == 'ms':
                ts = int(event[0])
            elif time_units == 'us':
                ts = int(event[0]) / 1000
            else:
                ts = int(event[0]) / 1000

            event_type = event[2]
            event_data = event[3]

            if event_type.lower() == 'packet_sent' and start is None:
                start = ts

            if event_type.lower() == 'packet_received':
                end = max(end, ts)

        return (end - start) / 1000


def main():
    # Get network scenario from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--dir')

    args = parser.parse_args()

    url = args.url
    dirpath = Path(args.dir)

    clients = DOCKER_CONFIG.keys()
    random.shuffle(clients)

    for client in clients:
        res = query(client, url, Path.joinpath(dirpath, client))

        print('mean: {}, std: {}'.format(np.mean(timings), np.std(timings)))

        if dirpath is not None:
            filepath = Path.joinpath(dirpath, client)
            timings = []
            try:
                with open(filepath, 'r') as f:
                    timings = json.load(f)
            except:
                pass

            timings += res

            with open(filepath, 'w') as f:
                json.dump(timings, f)


if __name__ == "__main__":
    main()
