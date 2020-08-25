/* eslint-disable no-underscore-dangle */
/* eslint-disable no-loop-func */
/* eslint-disable no-prototype-builtins */
/* eslint-disable indent */
/* eslint-disable no-restricted-syntax */
/* eslint-disable no-await-in-loop */
const puppeteer = require('puppeteer-core');
const PuppeteerHar = require('puppeteer-har');

const argparse = require('argparse');
const path = require('path');
const fs = require('fs');

const ITERATIONS = 10;
const RETRIES = 5;
const DOMAINS = ['facebook', 'cloudflare', 'google'];
const sizes = ['100KB', '1MB', '5MB'];

const firefoxArgs = (isH3) => {
    if (isH3) {
        return [
            '--profile',
            '/Users/alexyu/Library/Caches/Firefox/Profiles/3w5xom8x.default-nightly',
        ];
    }

    return [
        '--profile',
        '/Users/alexyu/Library/Application Support/Firefox/Profiles/mn8ljutx.H2',
    ];
};

const runFirefox = async (urlString, isH3) => {
    const timings = [];

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);

        // Restart browser for each iteration to make things fair...
        fs.rmdirSync('/tmp/firefox-profile', { recursive: true });
        const args = firefoxArgs(isH3);
        const browser = await puppeteer.launch({
            product: 'firefox',
            headless: true,
            executablePath: '/Applications/Firefox Nightly.app/Contents/MacOS/firefox',
            args,
        });

        for (let j = 0; j < RETRIES; j += 1) {
            try {
                const page = await browser.newPage();

                // list of events for converting to HAR
                const events = [];

                // event types to observe
                const observe = [
                    'Page.loadEventFired',
                    'Page.domContentEventFired',
                    'Page.frameStartedLoading',
                    'Page.frameAttached',
                    'Network.requestWillBeSent',
                    'Network.requestServedFromCache',
                    'Network.dataReceived',
                    'Network.responseReceived',
                    'Network.resourceChangedPriority',
                    'Network.loadingFinished',
                    'Network.loadingFailed',
                ];

                const client = await page.target().createCDPSession();
                await client.send('Page.enable');
                await client.send('Network.enable');
                observe.forEach((method) => {
                    client.on(method, (params) => {
                        events.push({ method, params });
                    });
                });

                await page.goto(urlString, {
                    timeout: 120000,
                });

                await page.close();

                let start;
                let end;
                let protocol;

                events.forEach((event) => {
                    if (event.method === 'Network.requestWillBeSent' && event.params.request.url === urlString) {
                        start = event.params.timestamp;
                    } else if (event.method === 'Network.responseReceived' && event.params.response.url === urlString) {
                        protocol = event.params.response.protocol;
                    } else if (event.method === 'Page.loadEventFired' && start !== undefined && end === undefined) {
                        end = event.params.timestamp;
                    }
                });

                if (start === undefined || end === undefined) {
                    throw Error('No start or end time found');
                }

                const time = (end - start) * 1000;

                console.log(protocol, time);

                if (isH3 && protocol !== 'h3') {
                    throw Error('Incorrect network protocol');
                }

                if (!isH3 && protocol !== 'h2') {
                    throw Error('Incorrect network protocol');
                }

                timings.push(time);
                break;
            } catch (error) {
                console.log(error);
                if (j === RETRIES - 1) {
                    console.error('Exceeded retries');
                    throw error;
                }
            }
        }

        await browser.close();
    }

    return timings;
};

const runBenchmark = async (loss, delay, bw, isH3) => {
    // Read endpoints from endpoints.json
    const endpoints = JSON.parse(fs.readFileSync('endpoints.json', 'utf8'));

    for (const domain of DOMAINS) {
        if (endpoints.hasOwnProperty(domain)) {
            const urls = endpoints[domain];
            for (const size of sizes) {
                // Create directory
                const dir = path.join('har', `loss-${loss}_delay-${delay}_bw-${bw}`, domain, size);
                fs.mkdirSync(dir, { recursive: true });

                // Read from file if exists
                const file = path.join(dir, `firefox_${isH3 ? 'h3' : 'h2'}.json`);
                let timings = [];
                try {
                    timings = JSON.parse(fs.readFileSync(file, 'utf8'));
                } catch (error) {
                    console.error(error);
                }

                // Run benchmark
                const result = await runFirefox(urls[size], isH3);

                // Concat result times to existing data
                timings.push(...result);

                // Save data
                fs.writeFileSync(file, JSON.stringify(timings));
            }
        }
    }
};

const runChromeWeb = async (obj, isH3) => {
    const urlString = obj.url;

    const timings = [];

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);

        // Restart browser for each iteration to make things fair...
        fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
        const args = firefoxArgs(isH3);
        const browser = await puppeteer.launch({
            headless: false,
            executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
            args,
        });

        for (let j = 0; j < RETRIES; j += 1) {
            try {
                const page = await browser.newPage();
                const har = await new PuppeteerHar(page);

                await har.start();
                await page.goto(urlString, {
                    timeout: 120000,
                });

                const harResult = await har.stop();
                const { entries } = harResult.log;

                const numH2 = entries.filter((entry) => entry.response.httpVersion === 'h2').length;
                const numH3 = entries.filter((entry) => entry.response.httpVersion === 'h3-29').length;

                await page.close();

                if (isH3 && numH3 / entries.length < 0.9) {
                    console.log('Not enough h3 resources');
                    if (j === RETRIES - 1) {
                        throw Error('Exceeded retries');
                    }
                    // eslint-disable-next-line no-continue
                    continue;
                }

                entries.sort((a, b) => (a._requestTime + a.time) - (b._requestTime + b.time));

                const start = entries[0]._requestTime;
                const end = entries[entries.length - 1]._requestTime + entries[entries.length - 1].time;
                const time = end - start;

                console.log(`Total: ${entries.length}, h2: ${numH2}, h3: ${numH3}, time: ${time}`);

                timings.push(time);
                break;
            } catch (error) {
                if (j === RETRIES - 1) {
                    console.error('Exceeded retries');
                    throw error;
                }
            }
        }

        await browser.close();
    }

    return timings;
};

const runBenchmarkWeb = async (loss, delay, bw, isH3) => {
    // Read endpoints from endpoints.json
    const endpoints = JSON.parse(fs.readFileSync('endpoints.json', 'utf8'));

    for (const domain of DOMAINS) {
        if (endpoints.hasOwnProperty(domain)) {
            const urls = endpoints[domain];
            const size = 'web';

            // Create directory
            const dir = path.join('har', `loss-${loss}_delay-${delay}_bw-${bw}`, domain, size);
            fs.mkdirSync(dir, { recursive: true });

            // Read from file if exists
            const file = path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
            let timings = [];
            try {
                timings = JSON.parse(fs.readFileSync(file, 'utf8'));
            } catch (error) {
                console.error(error);
            }

            // Run benchmark
            const result = await runChromeWeb(urls[size], isH3);

            // Concat result times to existing data
            timings.push(...result);

            // Save data
            fs.writeFileSync(file, JSON.stringify(timings));
        }
    }
};

(async () => {
    // Get network scenario from command line arguments
    const parser = new argparse.ArgumentParser();

    parser.add_argument('loss');
    parser.add_argument('delay');
    parser.add_argument('bw');

    const cliArgs = parser.parse_args();

    const { loss, delay, bw } = cliArgs;

    // // H2 - single object
    // console.log('Firefox: H2 - single object');
    // await runBenchmark(loss, delay, bw, false);

    // H3 - single object
    console.log('Firefox: H3 - single object');
    await runBenchmark(loss, delay, bw, true);

    // // H2 - multi object
    // console.log('Chrome: H2 - multi object');
    // await runBenchmarkWeb(loss, delay, bw, false);

    // // H3 - multi object
    // console.log('Chrome: H3 - multi object');
    // await runBenchmarkWeb(loss, delay, bw, true);
})();
