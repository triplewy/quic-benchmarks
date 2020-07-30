import json
import time
import sys

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 10
RETRIES = 20

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

insta_urls = [
    'https://www.instagram.com'
]

cf_urls = [
    'https://cloudflare-quic.com/1MB.png',
    'https://cloudflare-quic.com/5MB.png',
]

ms_urls = [
    'https://quic.westus.cloudapp.azure.com/1MBfile.txt',
    'https://quic.westus.cloudapp.azure.com/5000000.txt',
    'https://quic.westus.cloudapp.azure.com/10000000.txt',
]

aio_urls = [
    'https://quic.aiortc.org/10485760'  # 10MB
]

h2_profile = webdriver.FirefoxProfile()
h2_profile.set_preference('browser.cache.disk.enable', False)
h2_profile.set_preference('browser.cache.memory.enable', False)
h2_profile.set_preference('browser.cache.offline.enable', False)
h2_profile.set_preference('network.http.use-cache', False)
h2_profile.set_preference('network.http.http3.enabled', False)
h2_profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')
h2_profile.add_extension(
    '/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi')

h3_profile = webdriver.FirefoxProfile()
h3_profile.set_preference('browser.cache.disk.enable', False)
h3_profile.set_preference('browser.cache.memory.enable', False)
h3_profile.set_preference('browser.cache.offline.enable', False)
h3_profile.set_preference('network.http.use-cache', False)
h3_profile.set_preference('network.http.http3.enabled', True)
h3_profile.set_preference('network.http.http3.support_draft28', True)
h3_profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')
h3_profile.add_extension(
    '/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi')

binary = FirefoxBinary(
    firefox_path='/Applications/Firefox Nightly.app/Contents/MacOS/firefox')

firefox_options = FirefoxOptions()
firefox_options.add_argument('-devtools')


def query(driver, url: str, force_quic: bool, loss: int, delay: int, bw: int):
    timings = {
        'total': [],
        'blocked': [],
        'dns': [],
        'connect': [],
        'send': [],
        'wait': [],
        'receive': [],
        'ssl': [],
        '_queued': [],
    }

    url_result = urlparse(url)

    base_dir = Path.joinpath(
        Path.home(),
        'quic-benchmarks',
        'browser',
        'har',
        'loss-{}_delay-{}_bw-{}'.format(loss, delay, bw),
        'firefox'
    )

    if force_quic:
        har_dir = Path.joinpath(base_dir, 'h3', url_result.netloc)
    else:
        har_dir = Path.joinpath(base_dir, 'h2', url_result.netloc)

    Path(har_dir).mkdir(parents=True, exist_ok=True)

    har_path = Path.joinpath(
        har_dir,
        "{}.json".format(url_result.path[1:])
    )

    driver.set_page_load_timeout(300)

    try:
        with open(har_path, 'r') as har_file:
            timings = json.load(har_file)
    except:
        pass

    for i in range(ITERATIONS):
        print('{} - ITERATION: {}'.format(url, i))
        time.sleep(0.5)
        for i in range(RETRIES):
            try:
                if i >= 1:
                    print('retrying')
                    driver.close()
                    driver = webdriver.Firefox(
                        firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options)

                driver.get(url)
                har = driver.execute_script("""
                async function triggerExport() {
                    const result = await HAR.triggerExport();
                    return result;
                };
                return triggerExport();""")
                break
            except:
                if i == RETRIES - 1:
                    raise "Failed"

        entries = har['entries']
        entries = list(
            filter(lambda x: x['request']['url'] == url, entries))

        if len(entries) != 1:
            continue

        entry = entries[0]

        print(entry['response']['httpVersion'], entry['time'])
        timings['total'].append(entry['time'])

        for (k, v) in entry['timings'].items():
            if k not in timings:
                continue
            timings[k].append(v)

        with open(har_path, 'w') as har_file:
            json.dump(timings, har_file)


loss = int(sys.argv[1])
delay = int(sys.argv[2])
bw = int(sys.argv[3])

# Test Firefox H2
with webdriver.Firefox(firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options) as driver:
    # for url in ms_urls:
    #     query_file(driver, url, False)

    for url in fb_urls:
        query(driver, url, False, loss, delay, bw)

    # for url in cf_urls:
    #     query(driver, url, False)

    # for url in insta_urls:
    #     query(driver, url, False, loss, bw)


# Test Firefox H3
with webdriver.Firefox(firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options) as driver:
    # for url in ms_urls:
    #     query_file(driver, url, True)

    for url in fb_urls:
        query(driver, url, True, loss, delay, bw)

    # for url in insta_urls:
    #     query(driver, url, True, loss, bw)

    # for url in cf_urls:
    #     query(driver, url, True, loss)

    # for url in aio_urls:
    #     query(driver, url, True, loss)
