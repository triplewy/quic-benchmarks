import json
import time
import sys

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 1
RETRIES = 1

fb_urls = [
    'https://scontent.xx.fbcdn.net/speedtest-0B',
    # 'https://scontent.xx.fbcdn.net/speedtest-1KB',
    # 'https://scontent.xx.fbcdn.net/speedtest-10KB',
    # 'https://scontent.xx.fbcdn.net/speedtest-100KB',
    # 'https://scontent.xx.fbcdn.net/speedtest-500KB',
    # 'https://scontent.xx.fbcdn.net/speedtest-1MB',
    # 'https://scontent.xx.fbcdn.net/speedtest-2MB',
    # 'https://scontent.xx.fbcdn.net/speedtest-5MB',
    'https://scontent.xx.fbcdn.net/speedtest-10MB',
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


def query_file(driver, url: str, force_quic: bool):
    timings = {
        'total': [],
    }

    url_obj = urlparse(url)
    driver.get('https://{}'.format(url_obj.netloc))

    for i in range(ITERATIONS):
        print('{} - ITERATION: {}'.format(url, i))
        time.sleep(1)
        for i in range(RETRIES):
            try:
                if i >= 1:
                    print('retrying')
                start = time.time()
                result = driver.execute_script("""
                async function triggerExport(url) {
                    const res = await fetch(url);
                    console.log(res)
                    const text = await res.text();
                    return text;
                };
                return triggerExport(arguments[0]);""", url)
                print('len(result): {}'.format(len(result)))
                elapsed = (time.time() - start) * 1000
                break
            except:
                if i == RETRIES - 1:
                    raise "Failed"

        timings['total'].append(elapsed)

    if force_quic:
        har_dir = Path.joinpath(
            Path.home(),
            'quic-benchmarks',
            'browser',
            'har',
            'firefox',
            'h3',
            url_obj.netloc
        )
    else:
        har_dir = Path.joinpath(
            Path.home(),
            'quic-benchmarks',
            'browser',
            'har',
            'firefox',
            'h2',
            url_obj.netloc
        )

    Path(har_dir).mkdir(parents=True, exist_ok=True)

    har_path = Path.joinpath(
        har_dir,
        "{}.json".format(url_obj.path[1:])
    )

    with open(har_path, 'w') as har_file:
        json.dump(timings, har_file)


def query(driver, url: str, force_quic: bool, loss: int):
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

    if force_quic:
        har_dir = Path.joinpath(
            Path.home(),
            'quic-benchmarks',
            'browser',
            'har',
            'loss_{}'.format(loss),
            'firefox',
            'h3',
            url_result.netloc
        )
    else:
        har_dir = Path.joinpath(
            Path.home(),
            'quic-benchmarks',
            'browser',
            'har',
            'loss_{}'.format(loss),
            'firefox',
            'h2',
            url_result.netloc
        )

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
        time.sleep(1)
        for i in range(RETRIES):
            try:
                if i >= 1:
                    print('retrying')
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

        timings['total'].append(entry['time'])

        for (k, v) in entry['timings'].items():
            if k not in timings:
                continue
            timings[k].append(v)

        with open(har_path, 'w') as har_file:
            json.dump(timings, har_file)


loss = int(sys.argv[1])

# # Test Firefox H2
# with webdriver.Firefox(firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options) as driver:
#     # for url in ms_urls:
#     #     query_file(driver, url, False)

#     for url in fb_urls:
#         # Test H2
#         query(driver, url, False, loss)

#     # for url in cf_urls:
#     #     query(driver, url, False)

# Test Firefox H3
with webdriver.Firefox(firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options) as driver:
    # for url in ms_urls:
    #     query_file(driver, url, True)

    # for url in fb_urls:
    #     query(driver, url, True, loss)

    for url in cf_urls:
        query(driver, url, True, loss)

    # for url in aio_urls:
    #     query(driver, url, True, loss)

    time.sleep(600)
