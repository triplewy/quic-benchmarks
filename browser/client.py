import subprocess
import time
import json

from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 10

fb_urls = [
    'https://scontent.xx.fbcdn.net/speedtest-0B',
    'https://scontent.xx.fbcdn.net/speedtest-1KB',
    'https://scontent.xx.fbcdn.net/speedtest-10KB',
    'https://scontent.xx.fbcdn.net/speedtest-100KB',
    'https://scontent.xx.fbcdn.net/speedtest-500KB',
    'https://scontent.xx.fbcdn.net/speedtest-1MB',
    'https://scontent.xx.fbcdn.net/speedtest-2MB',
    'https://scontent.xx.fbcdn.net/speedtest-5MB',
    'https://scontent.xx.fbcdn.net/speedtest-10MB',
]

cloudfare_urls = [
    'https://cloudflare-quic.com/1MB.png',
    'https://cloudflare-quic.com/5MB.png',
]

ms_urls = [
    'https://quic.westus.cloudapp.azure.com/1MBfile.txt',
    'https://quic.westus.cloudapp.azure.com/5000000.txt',
    'https://quic.westus.cloudapp.azure.com/10000000.txt',
]

f5_urls = [
    'https://f5quic.com:4433/50000',
    'https://f5quic.com:4433/5000000',
    'https://f5quic.com:4433/10000000',
]


def query(urls: list, client: str):
    for h in ['h2', 'h3']:
        for url in urls:
            times = {
                'total': []
            }

            url_obj = urlparse(url)
            url_host = url_obj.netloc
            url_path = url_obj.path[1:]

            if url_host == 'f5quic.com:4433' and h == 'h2':
                continue

            for i in range(ITERATIONS):
                print('{} - {} - Iteration: {}'.format(h, url, i))
                start = time.time()

                if client == 'curl':
                    if h == 'h2':
                        subprocess.run(
                            ['curl', '--output', '/dev/null', '--http2', url],
                        )
                    else:
                        subprocess.run(
                            ['curl', '--output', '/dev/null', '--http3', url],
                        )
                elif client == 'hq':
                    if h == 'h2':
                        continue
                    else:
                        if url_host.count(':') > 0:
                            [host, port] = url_host.split(':')
                        else:
                            host = url_host
                            port = 443

                        subprocess.run(
                            [
                                './hq',
                                '--log_response=false',
                                '--mode=client',
                                '--draft_version=27',
                                '--host={}'.format(host),
                                '--port={}'.format(port),
                                '--path=/{}'.format(url_path),
                                '--v=0',
                                '>',
                                '/dev/null'
                            ],
                        )

                # Python measures time in seconds
                elapsed = time.time() - start
                elapsed *= 1000
                times['total'].append(elapsed)

            results_dir = Path.joinpath(
                Path.cwd(), 'har', client, h, url_host)
            Path(results_dir).mkdir(parents=True, exist_ok=True)
            results_file = Path.joinpath(
                results_dir, '{}.json'.format(url_path))
            print(results_file)
            with open(results_file, 'w') as f:
                print(times)
                json.dump(times, f)


def main():
    for urls in [f5_urls]:
        for client in ['hq']:
            query(urls, client)


if __name__ == "__main__":
    main()
