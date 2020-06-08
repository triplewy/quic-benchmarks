import json
import time

from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from pathlib import Path
from urllib.parse import urlparse

ITERATIONS = 10
RETRIES = 5

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

cf_urls = [
    'https://cloudflare-quic.com/1MB.png',
    'https://cloudflare-quic.com/5MB.png',
]

h2_profile = webdriver.FirefoxProfile()
h2_profile.set_preference('browser.cache.disk.enable', False)
h2_profile.set_preference('browser.cache.memory.enable', False)
h2_profile.set_preference('browser.cache.offline.enable', False)
h2_profile.set_preference('network.http.use-cache', False)
h2_profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')
h2_profile.add_extension(
    '/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi')

h3_profile = webdriver.FirefoxProfile()
h3_profile.set_preference('browser.cache.disk.enable', False)
h3_profile.set_preference('browser.cache.memory.enable', False)
h3_profile.set_preference('browser.cache.offline.enable', False)
h3_profile.set_preference('network.http.use-cache', False)
h3_profile.set_preference('network.http.http3.enabled', True)
h3_profile.set_preference('devtools.toolbox.selectedTool', 'netmonitor')
h3_profile.add_extension(
    '/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi')

binary = FirefoxBinary(
    firefox_path='/Applications/Firefox Nightly.app/Contents/MacOS/firefox')

firefox_options = FirefoxOptions()
firefox_options.add_argument('-devtools')


def query(driver, url: str, force_quic: bool):
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
                    console.log('here')
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

        url_result = urlparse(url)

        if force_quic:
            har_dir = Path.joinpath(
                Path.home(),
                'quic-benchmarks',
                'browser',
                'har',
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
                'firefox',
                'h2',
                url_result.netloc
            )

        Path(har_dir).mkdir(parents=True, exist_ok=True)

        har_path = Path.joinpath(
            har_dir,
            "{}.json".format(url_result.path[1:])
        )

        with open(har_path, 'w') as har_file:
            json.dump(timings, har_file)


# Test Firefox H2
with webdriver.Firefox(firefox_binary=binary, firefox_profile=h2_profile, options=firefox_options) as driver:
    for url in fb_urls:
        # Test H2
        query(driver, url, False)

    for url in cf_urls:
        query(driver, url, False)

# Test Firefox H3
with webdriver.Firefox(firefox_binary=binary, firefox_profile=h3_profile, options=firefox_options) as driver:
    for url in fb_urls:
        # Test H3
        query(driver, url, True)

    for url in cf_urls:
        query(driver, url, True)
