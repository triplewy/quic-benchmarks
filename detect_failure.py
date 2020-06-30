import subprocess
import shutil
import os

from pathlib import Path
from optparse import OptionParser


def proxygen():
    dir_path = Path.joinpath(
        Path.home(), 'quic-benchmarks', 'qlog', 'proxygen')

    i = 0

    while True:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        try:
            os.remove(Path.joinpath(Path.home(), 'quic-benchmarks',
                                    'qlog', 'proxygen', '.qlog'))
        except OSError:
            pass

        print('iteration: ', i)

        output = subprocess.run(
            [
                '{}/proxygen/proxygen/_build/proxygen/httpserver/hq'.format(
                    Path.home()),
                '--log_response=false',
                '--mode=client',
                '--stream_flow_control=1073741824',
                '--conn_flow_control=1073741824',
                '--use_draft=true',
                '--protocol=h3-29',
                '--host=scontent.xx.fbcdn.net',
                '--port=443',
                '--path=/speedtest-0B',
                '--qlogger_path={}/quic-benchmarks/qlog/proxygen'.format(
                    Path.home()),
                '--v=4',
            ],
            capture_output=True
        )
        print(output.stderr.decode())
        stderr = output.stderr.decode()

        if stderr.count('E06') > 0:
            print('Detected error')
            return

        i += 1


def ngtcp2():
    dir_path = Path.joinpath(
        Path.home(), 'quic-benchmarks', 'qlog', 'ngtcp2')

    i = 0

    while True:
        shutil.rmtree(dir_path, ignore_errors=True)
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print('iteration: ', i)

        output = subprocess.run(
            [
                '{}/ngtcp2/examples/client'.format(Path.home()),
                '--quiet',
                '--exit-on-all-streams-close',
                '--max-data=1073741824',
                '--max-stream-data-uni=1073741824',
                '--max-stream-data-bidi-local=1073741824',
                '--cc=cubic',
                '--qlog-dir={}/quic-benchmarks/qlog/ngtcp2'.format(
                    Path.home()),
                'scontent.xx.fbcdn.net',
                '443',
                'https://scontent.xx.fbcdn.net/speedtest-0B',
            ],
            capture_output=True
        )
        print(str(output.stderr))
        stderr = str(output.stderr)

        if stderr.count('E06') > 0:
            print('Detected error')
            return

        i += 1


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
        "--proxygen", action="store_true", dest="toggle_proxygen")
    parser.add_option(
        "--ngtcp2", action="store_true", dest="toggle_ngtcp2")

    (options, args) = parser.parse_args()

    if options.toggle_proxygen:
        print('Checking proxygen...')
        proxygen()

    if options.toggle_ngtcp2:
        print('Checking ngtcp2...')
        ngtcp2()
