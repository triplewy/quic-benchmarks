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
from glob import glob

DOCKER_CLIENT = docker.from_env()

DOCKER_CONFIG = {}
with open(Path.joinpath(Path(__file__).parent.absolute(), 'docker.json'), mode='r') as f:
    DOCKER_CONFIG = json.load(f)

LOCAL_CONFIG = {}
with open(Path.joinpath(Path(__file__).parent.absolute(), 'local.json'), mode='r') as f:
    LOCAL_CONFIG = json.load(f)

ENDPOINTS = {}
with open(Path.joinpath(Path(__file__).parent.absolute(), 'endpoints.json'), mode='r') as f:
    ENDPOINTS = json.load(f)

CONFIG = {}
with open(Path.joinpath(Path(__file__).parent.absolute(), 'config.json'), mode='r') as f:
    CONFIG = json.load(f)

RETRIES = 10
ITERATIONS = CONFIG['iterations']['value']
LOCAL = CONFIG['local']['value']
DATA_PATH = Path.joinpath(
    Path(__file__).parent.absolute(), CONFIG['data_path']['value'])

TMP_DIR = Path.joinpath(DATA_PATH, 'tmp')
TIME_DIR = Path.joinpath(DATA_PATH, 'timings')
QLOG_DIR = Path.joinpath(DATA_PATH, 'qlogs')

TMP_DIR.mkdir(parents=True, exist_ok=True)
TIME_DIR.mkdir(parents=True, exist_ok=True)
QLOG_DIR.mkdir(parents=True, exist_ok=True)

TMP_QLOG = Path.joinpath(TMP_DIR, 'qlog')
TMP_QLOG.mkdir(parents=True, exist_ok=True)


DOMAINS = CONFIG['domains']
SIZES = CONFIG['sizes']['single']


def benchmark(client: str, url: str, timedir: str, qlogdir: str):
    timings = []

    timings_path = Path.joinpath(timedir, '{}.json'.format(client))
    try:
        with open(timings_path, 'r') as f:
            timings = json.load(f)
    except:
        pass

    dirpath = Path.joinpath(qlogdir, client)
    Path(dirpath).mkdir(parents=True, exist_ok=True)

    for i in range(len(timings), ITERATIONS):
        print('{} - {} - Iteration: {}'.format(client, url, i))

        if LOCAL:
            elapsed = run_subprocess(client, url, dirpath, i)
        else:
            elapsed = run_docker(client, url, dirpath, i)

        elapsed *= 1000
        timings.append(elapsed)
        print(client, elapsed)
        time.sleep(1)

    with open(timings_path, 'w') as f:
        json.dump(timings, f)

    # Get median of timings
    median_index = np.argsort(timings)[len(timings)//2]

    # Remove qlogs of all runs except median
    for f in os.listdir(dirpath):
        filename_arr = f.split('.')
        i = int(filename_arr[0].split('_')[-1])
        if i != median_index:
            os.remove(Path.joinpath(dirpath, f))


def run_subprocess(client: str, url: str, dirpath: str, i: int) -> float:
    # Parse URL object
    url_obj = urlparse(url)
    url_host = url_obj.netloc
    url_path = url_obj.path
    if url_host.count(':') > 0:
        [url_host, url_port] = url_host.split(':')
    else:
        url_port = '443'

    if client not in LOCAL_CONFIG:
        raise Exception('client {} is not valid'.format(client))

    # Modify commands
    commands = []
    for command in LOCAL_CONFIG[client]:
        command = command.replace('{qlog_dir}', str(TMP_QLOG))
        command = command.replace('{url}', url)
        command = command.replace('{host}', url_host)
        command = command.replace('{path}', url_path)
        command = command.replace('{port}', url_port)
        commands.append(command)

    output = subprocess.run(
        commands,
        capture_output=True
    )

    if client == 'curl_h2':
        out_arr = output.stdout.decode().split('\n')[:-1]
        dns_time = float(out_arr[0].split(':')[1])
        total_time = float(out_arr[1].split(':')[1])
        return total_time - dns_time

    if len(os.listdir(TMP_QLOG)) == 0:
        raise 'no qlog created'

    oldpath = Path.joinpath(TMP_QLOG, os.listdir(TMP_QLOG)[0])

    res = get_time_from_qlog(oldpath)

    if dirpath is None:
        os.remove(oldpath)
    else:
        with open(oldpath, mode='r') as old:
            newpath = Path.joinpath(dirpath, '{}_{}.qlog'.format(client, i))
            with open(newpath, mode='w') as new:
                new.write(old.read())
        os.remove(oldpath)

    return res


def run_docker(client: str, url: str, dirpath: str, i: int) -> float:
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

    if 'cap_add' in docker_config:
        args['cap_add'] = docker_config['cap_add']

    if 'security_opt' in docker_config:
        args['security_opt'] = docker_config['security_opt']

    container = DOCKER_CLIENT.containers.run(
        image,
        **args
    )
    container.wait()
    out = container.logs()
    out = out.decode('utf-8')
    print(out)
    container.remove()

    if client == 'curl_h2':
        out_arr = out.split('\n')[:-1]
        dns_time = float(out_arr[0].split(':')[1])
        total_time = float(out_arr[1].split(':')[1])
        return total_time - dns_time

    if len(os.listdir('/tmp/qlog')) == 0:
        raise 'no qlog created'

    logpath = Path.joinpath(
        Path('/tmp/qlog'), os.listdir('/tmp/qlog')[0])

    time = None

    if client.count('chrome') > 0:
        with open(logpath, mode='r') as f:
            out = json.load(f)
            if client.count('multiple') == 0:
                time = out[0] / 1000
            else:
                time = out[0]['other']['networkingTimeCp'] / 1000
    else:
        time = get_time_from_qlog(logpath)

    if dirpath is None:
        os.remove(logpath)
    elif client.count('chrome') > 0:
        filepath = Path.joinpath(dirpath, '{}_{}.json'.format(client, i))
        os.rename(logpath, filepath)
    else:
        filepath = Path.joinpath(dirpath, '{}_{}.qlog'.format(client, i))
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
    parser.add_argument('--dir')

    args = parser.parse_args()

    if args.dir is not None:
        dirpath = Path(args.dir)
    else:
        raise 'dir is not defined'

    clients = CONFIG['clients']
    random.shuffle(clients)

    # Not using chrome via python script for now
    clients = [x for x in clients if x.count('chrome') == 0]

    for domain in DOMAINS:
        for size in SIZES:

            timedir = Path.joinpath(TIME_DIR, dirpath, domain, size)
            timedir.mkdir(parents=True, exist_ok=True)

            qlogdir = Path.joinpath(QLOG_DIR, dirpath, domain, size)
            qlogdir.mkdir(parents=True, exist_ok=True)

            for client in clients:
                url = ENDPOINTS[domain][size]
                benchmark(client, url, timedir, qlogdir)


if __name__ == "__main__":
    main()
