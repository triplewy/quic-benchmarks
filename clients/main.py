import json
import time
import sys
import argparse

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 10
RETRIES = 20
DOMAINS = ['facebook', 'cloudflare', 'google']
SIZES = ['100KB', '1MB', '5MB']

h2_profile = webdriver.FirefoxProfile()
h2_profile.set_preference('browser.cache.disk.enable', False)
h2_profile.set_preference('browser.cache.memory.enable', False)
h2_profile.set_preference('browser.cache.offline.enable', False)
h2_profile.set_preference('browser.cache.disk.capacity', -1)
h2_profile.set_preference('browser.cache.memory.capacity', -1)
h2_profile.set_preference('browser.cache.offline.capacity', -1)
h2_profile.set_preference('devtools.cache.disabled', True)
h2_profile.set_preference('network.http.use-cache', False)
h2_profile.set_preference('network.http.http3.enabled', False)
h2_profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')
h2_profile.add_extension(
    '/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi')

h3_profile = webdriver.FirefoxProfile()
h3_profile.set_preference('browser.cache.disk.enable', False)
h3_profile.set_preference('browser.cache.memory.enable', False)
h3_profile.set_preference('browser.cache.offline.enable', False)
h3_profile.set_preference('browser.cache.disk.capacity', -1)
h3_profile.set_preference('browser.cache.memory.capacity', -1)
h3_profile.set_preference('browser.cache.offline.capacity', -1)
h3_profile.set_preference('devtools.cache.disabled', True)
h3_profile.set_preference('network.http.use-cache', False)
h3_profile.set_preference('network.http.http3.enabled', True)
h3_profile.set_preference('network.http.http3.support_draft28', True)
h3_profile.set_preference(
    'network.http.http3.alt-svc-mapping-for-testing', True)
h3_profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')
h3_profile.add_extension(
    '/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi')

binary = FirefoxBinary(
    firefox_path='/Applications/Firefox Nightly.app/Contents/MacOS/firefox')

firefox_options = FirefoxOptions()
firefox_options.add_argument('-devtools')


def query(url: str, isH3: bool):
    timings = []

    for i in range(ITERATIONS):
        print('{} - ITERATION: {}'.format(url, i))

        if isH3:
            driver = webdriver.Firefox(
                firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options)
        else:
            driver = webdriver.Firefox(
                firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options)

        driver.set_page_load_timeout(60)

        for j in range(RETRIES):
            try:
                if j >= 1:
                    print('retrying')
                    if isH3:
                        if j > 0 and j % 3 == 0:
                            driver.close()
                            driver = webdriver.Firefox(
                                firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options)
                    else:
                        driver.close()
                        driver = webdriver.Firefox(
                            firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options)

                driver.get(url)
                har = driver.execute_script("""
                async function triggerExport() {
                    const result = await HAR.triggerExport();
                    return result;
                };
                return triggerExport();""")

                entries = har['entries']
                entries = list(
                    filter(lambda x: x['request']['url'] == url, entries))

                if len(entries) != 1:
                    print('invalid HAR')
                    continue

                entry = entries[0]

                print(entry['response']['httpVersion'], entry['time'])

                httpVersion = entry['response']['httpVersion']

                if isH3 and httpVersion == 'HTTP/3':
                    timings.append(entry['time'])
                    break

                if not isH3 and httpVersion == 'HTTP/2':
                    timings.append(entry['time'])
                    break

            except:
                if j == RETRIES - 1:
                    raise "Failed"

        driver.close()

    return timings


def benchmark(loss: str, delay: str, bw: str, isH3: bool):
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

            if isH3:
                filepath = Path.joinpath(
                    dirpath,
                    "firefox_h3.json"
                )
            else:
                filepath = Path.joinpath(
                    dirpath,
                    "firefox_h2.json"
                )

            timings = []
            try:
                with open(filepath, 'r') as f:
                    timings = json.load(f)
            except:
                pass

            result = query(urls[size], isH3)

            timings += result

            with open(filepath, 'w') as f:
                json.dump(timings, f)


def query_web(obj: object, isH3: bool):
    url = obj['url']
    timings = []

    for i in range(ITERATIONS):
        print('{} - ITERATION: {}'.format(url, i))

        if isH3:
            driver = webdriver.Firefox(
                firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options)
        else:
            driver = webdriver.Firefox(
                firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options)

        driver.set_page_load_timeout(60)

        for j in range(RETRIES):
            try:
                if j >= 1:
                    print('retrying')
                    if isH3:
                        if j % 2 != 0:
                            driver.close()
                            driver = webdriver.Firefox(
                                firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options)
                    else:
                        driver.close()
                        driver = webdriver.Firefox(
                            firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options)

                # start = time.time()
                driver.get(url)
                # elapsed = time.time() - start
                har = driver.execute_script("""
                async function triggerExport() {
                    const result = await HAR.triggerExport();
                    return result;
                };
                return triggerExport();""")

                entries = har['entries']
                numH2 = len(
                    [entry for entry in entries if entry.response.httpVersion == 'HTTP/2'])
                numH3 = len(
                    [entry for entry in entries if entry.response.httpVersion == 'HTTP/3'])

                if isH3 and numH3 / len(entries) < 0.9:
                    print('Not enough h3 resources')
                    continue

                entries.sort(key=lambda x: x._requestTime + x.time)

                start = entries[0]._requestTime
                end = entries[-1]._requestTime + entries[-1].time
                elapsed = end - start

                print('Total: {}, h2: {}, h3: {}, time: {}',
                      len(entries), numH2, numH3, elapsed)
                timings.append(elapsed)
                break
            except:
                if j == RETRIES - 1:
                    raise "Failed"

        driver.close()

    return timings


def benchmark_web(loss: str, delay: str, bw: str, isH3: bool):
    # Read endpoints from endpoints.json
    with open('endpoints.json', 'r') as f:
        endpoints = json.load(f)

    for domain in DOMAINS:
        urls = endpoints[domain]
        size = 'web'
        dirpath = Path.joinpath(
            Path.cwd(),
            'har',
            'loss-{}_delay-{}_bw-{}'.format(loss, delay, bw),
            domain,
            size,
        )
        Path(dirpath).mkdir(parents=True, exist_ok=True)

        if isH3:
            filepath = Path.joinpath(
                dirpath,
                "firefox_h3.json"
            )
        else:
            filepath = Path.joinpath(
                dirpath,
                "firefox_h2.json"
            )

        timings = []
        try:
            with open(filepath, 'r') as f:
                timings = json.load(f)
        except:
            pass

        result = query_web(urls[size], isH3)

        timings += result

        with open(filepath, 'w') as f:
            json.dump(timings, f)


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

    # H2 - single object
    benchmark(loss, delay, bw, False)

    # H3 - single object
    benchmark(loss, delay, bw, True)

    # # H2 - multi object
    # benchmark_web(loss, delay, bw, False)

    # # H3 - multi object
    # benchmark_web(loss, delay, bw, True)


if __name__ == "__main__":
    main()
