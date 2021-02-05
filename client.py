import argparse
import subprocess
import time
import json
import sys
import pathlib
import docker
import os
import shutil
import random
import numpy as np
import datetime
import shutil

from typing import List
from pathlib import Path
from urllib.parse import urlparse
from docker.types import LogConfig
from glob import glob

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
PCAP_DIR = Path.joinpath(DATA_PATH, 'pcaps')
METRICS_DIR = Path.joinpath(DATA_PATH, 'metrics')

TMP_DIR.mkdir(parents=True, exist_ok=True)
TIME_DIR.mkdir(parents=True, exist_ok=True)
QLOG_DIR.mkdir(parents=True, exist_ok=True)
PCAP_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)

TMP_QLOG = Path.joinpath(TMP_DIR, 'qlog')
TMP_QLOG.mkdir(parents=True, exist_ok=True)

TMP_PCAP = Path.joinpath(TMP_DIR, 'pcap')
TMP_PCAP.mkdir(parents=True, exist_ok=True)

DOMAINS = CONFIG['domains']
SIZES = CONFIG['sizes']['single']
ENV = os.environ.copy()


def remove_files(dirname: str):
    for filename in os.listdir(dirname):
        file_path = os.path.join(dirname, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def record_pcap(url_host: str):
    process = subprocess.Popen([
        'tshark',
        '-i',
        'en0',
        '-f',
        f'host {url_host} and tcp',
        '-w',
        Path.joinpath(TMP_PCAP, 'out.pcapng')
    ])
    time.sleep(2)
    return process


def benchmark(client: str, url: str, dirs: List[str], log: bool):
    timedir, qlogdir, pcapdir, metricsdir = dirs['time'], dirs['qlog'], dirs['pcap'], dirs['metrics']

    timings = []
    metrics = []

    for dirpath in [timedir, metricsdir]:
        exist_path = Path.joinpath(dirpath, '{}.json'.format(client))
        try:
            with open(exist_path, 'r') as f:
                out = json.load(f)
                if dirpath == timedir:
                    timings = out
                else:
                    metrics = out
        except:
            pass

    if client.count('h3') > 0:
        dirpath = Path.joinpath(qlogdir, client)
        Path(dirpath).mkdir(parents=True, exist_ok=True)
    else:
        dirpath = Path.joinpath(pcapdir, client)
        Path(dirpath).mkdir(parents=True, exist_ok=True)

    for i in range(len(timings), ITERATIONS):
        for j in range(RETRIES):

            if j == RETRIES - 1:
                raise Exception('Retries exceeded')

            try:
                if str(timedir).count('LTE'):
                    time.sleep(10)

                print('{} - {} - Iteration: {}'.format(client, url, i))

                if LOCAL:
                    res = run_subprocess(client, url, dirpath, i, log)
                else:
                    res = run_docker(client, url, dirpath, i)

                metrics.append(res)
                elapsed = res['time'] * 1000
                timings.append(elapsed)
                print(client, res, elapsed)
                break
            except Exception as e:
                print(e)

    # Write timings and metrics to disk
    for dump_dir in [timedir, metricsdir]:
        exist_path = Path.joinpath(dump_dir, '{}.json'.format(client))
        with open(exist_path, 'w') as f:
            if dump_dir == timedir:
                dump = timings
            else:
                dump = metrics

            json.dump(dump, f)

    # Get median of timings
    median_index = np.argsort(timings)[len(timings)//2]

    # Remove qlogs or pcaps of all runs except median
    for f in os.listdir(dirpath):
        filename_arr = f.split('.')
        i = int(filename_arr[0].split('_')[-1])
        if i != median_index:
            os.remove(Path.joinpath(dirpath, f))

    # Delete sslkeylog if it exists
    sslkeylog = Path.joinpath(TMP_DIR, 'sslkeylog')
    if os.path.exists(sslkeylog):
        os.remove(sslkeylog)


def run_subprocess(client: str, url: str, dirpath: str, i: int, log: bool) -> dict:
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
        if '{qlog_dir}' in command:
            if log:
                command = command.replace('{qlog_dir}', str(TMP_QLOG))
            else:
                continue

        command = command.replace('{url}', url)
        command = command.replace('{host}', url_host)
        command = command.replace('{path}', url_path)
        command = command.replace('{port}', url_port)
        commands.append(command)

    process = None
    if client.count('h2') > 0 and log:
        # tcpdump does not include network emulation stuff so info is not useful
        # Commenting below for now
        # ENV['SSLKEYLOGFILE'] = Path.joinpath(TMP_DIR, 'sslkeylog')
        # process = record_pcap(url_host)
        pass

    start = datetime.datetime.now()
    output = subprocess.run(
        commands,
        capture_output=True,
        env=ENV
    )
    end = datetime.datetime.now()
    duration = end - start

    result = {}

    if client == 'curl_h2':
        if process is not None:
            time.sleep(1)
            process.kill()
            time.sleep(1)
            tshark_output = subprocess.run([
                'tshark',
                '-r',
                Path.joinpath(TMP_PCAP, 'out.pcapng'),
                '-T',
                'json',
                '-o',
                f'tls.keylog_file: {Path.joinpath(TMP_DIR, "sslkeylog")}',
                '-j',
                "Timestamps tcp tcp.flags http2 http2.stream"
            ], capture_output=True)

            with open(Path.joinpath(dirpath, f'{client}_{i}.json'), mode='w') as f:
                json.dump(json.loads(tshark_output.stdout.decode()), f)

            result = process_pcap(Path.joinpath(dirpath, f'{client}_{i}.json'))

        out_arr = output.stdout.decode().split('\n')[:-1]
        dns_time = float(out_arr[0].split(':')[1])
        total_time = float(out_arr[1].split(':')[1])
        result['time'] = total_time - dns_time
        return result

    if not log:
        result['time'] = duration
        return result

    if len(os.listdir(TMP_QLOG)) == 0:
        raise 'no qlog created'

    oldpath = Path.joinpath(TMP_QLOG, os.listdir(TMP_QLOG)[0])

    try:
        result = process_qlog(oldpath)

        if dirpath is not None:
            with open(oldpath, mode='r') as old:
                newpath = Path.joinpath(
                    dirpath, '{}_{}.qlog'.format(client, i))
                with open(newpath, mode='w') as new:
                    new.write(old.read())

        remove_files(TMP_QLOG)
        return result
    except Exception as e:
        remove_files(TMP_QLOG)
        raise e


def run_docker(client: str, url: str, dirpath: str, i: int) -> float:
    DOCKER_CLIENT = docker.from_env()

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
        time = process_qlog(logpath)

    if dirpath is None:
        os.remove(logpath)
    elif client.count('chrome') > 0:
        filepath = Path.joinpath(dirpath, '{}_{}.json'.format(client, i))
        os.rename(logpath, filepath)
    else:
        filepath = Path.joinpath(dirpath, '{}_{}.qlog'.format(client, i))
        os.rename(logpath, filepath)

    return time


def process_qlog(qlog: str) -> dict:
    with open(qlog, mode='r') as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        fin = False
        start = None
        end = 0
        init_rtt = None
        first_data_pkt_ts = None
        init_cwnd_mss = 0
        init_cwnd_bytes = 0

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

            if start is None:
                continue

            if event_type.lower() == 'packet_received':
                if init_rtt is None:
                    init_rtt = ts - start

                end = max(end, ts)

                if 'frames' not in event_data:
                    continue

                frames = event_data['frames']

                for frame in frames:
                    if frame['frame_type'].lower() == 'stream':
                        if frame['stream_id'] != '0':
                            continue

                        length = int(frame['length'])

                        if first_data_pkt_ts is None:
                            first_data_pkt_ts = ts

                        if ts <= first_data_pkt_ts + init_rtt:
                            init_cwnd_mss += 1
                            init_cwnd_bytes += length

        return {
            'time': (end - start) / 1000,
            'init_cwnd_mss': init_cwnd_mss,
            'init_cwnd_bytes': init_cwnd_bytes
        }


def process_pcap(pcap: str) -> float:
    delay = 0
    # pcap could be posix path
    if str(pcap).count('delay-50ms') > 0:
        delay = 50
    elif str(pcap).count('delay-100ms') > 0:
        delay = 100

    with open(pcap, mode='r') as f:
        data = json.load(f)

        start = None
        init_rtt = None

        h2_headers_received = False
        first_data_pkt_time = None
        init_cwnd_mss = 0
        init_cwnd_bytes = 0

        # Associate each ACK offset with a timestamp
        for packet in data:
            tcp = packet['_source']['layers']['tcp']
            h2 = packet['_source']['layers'].get('http2', {})
            srcport = tcp['tcp.srcport']
            time = float(tcp['Timestamps']['tcp.time_relative']) * 1000

            if srcport != '443' and start is None:
                start = time

            if start is None:
                continue

            # receive packet
            if srcport == '443':
                if init_rtt is None:
                    init_rtt = time - start + delay

                if not isinstance(h2, dict):
                    continue

                stream_id = h2.get('http2.stream', {}).get(
                    'http2.streamid', None)

                # Find packet received with h2 headers. All packets received after that are data packets
                if not h2_headers_received:
                    if stream_id == '1':
                        h2_headers_received = True
                    continue

                if first_data_pkt_time is None:
                    first_data_pkt_time = time

                bytes_len = int(tcp['tcp.len'])

                if time <= first_data_pkt_time + init_rtt:
                    init_cwnd_mss += 1
                    init_cwnd_bytes += bytes_len

    return {
        'init_cwnd_mss': init_cwnd_mss,
        'init_cwnd_bytes': init_cwnd_bytes
    }


def main():
    # Get network scenario from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir')
    parser.add_argument('--log', dest='log',
                        action='store_true', default=False)

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

            dirs = {}
            for name in ['time', 'qlog', 'pcap', 'metrics']:
                if name == 'time':
                    dirname = TIME_DIR
                elif name == 'qlog':
                    dirname = QLOG_DIR
                elif name == 'pcap':
                    dirname = PCAP_DIR
                else:
                    dirname = METRICS_DIR

                tmp_dir = Path.joinpath(dirname, dirpath, domain, size)
                tmp_dir.mkdir(parents=True, exist_ok=True)
                dirs[name] = tmp_dir

            pcapdir = Path.joinpath(PCAP_DIR, dirpath, domain, size)
            pcapdir.mkdir(parents=True, exist_ok=True)

            for client in clients:
                url = ENDPOINTS[domain][size]
                benchmark(client, url, dirs, args.log)


if __name__ == "__main__":
    main()
