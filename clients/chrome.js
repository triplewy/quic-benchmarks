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
const url = require('url');

const ITERATIONS = 25;
const RETRIES = 5;
const DOMAINS = ['facebook', 'google', 'cloudflare'];
const SIZES = ['100KB', '1MB', '5MB'];
const WEBPAGE_SIZES = ['small', 'medium', 'large'];

// const DOMAINS = ['google'];
// const WEBPAGE_SIZES = ['small'];
// const SIZES = ['100KB'];

const paths = JSON.parse(fs.readFileSync('paths.json', 'utf8'));

const chromeArgs = (urls) => {
    const args = [
        '--user-data-dir=/tmp/chrome-profile',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        // '--log-net-log=/tmp/netlog/chrome.json',
    ];

    if (urls !== null && urls.length > 0) {
        args.push(
            '--enable-quic',
            '--quic-version=h3-29',
        );

        const origins = urls.map((urlString) => {
            const urlObject = url.parse(urlString);
            return `${urlObject.host}:443`;
        });

        args.push(`--origin-to-force-quic-on=${origins.join(',')}`);
    } else {
        args.push(
            '--disable-quic',
        );
    }

    return args;
};

const runChrome = async (urlString, isH3) => {
    const timings = [];

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);

        // Restart browser for each iteration to make things fair...
        // fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
        const args = chromeArgs(isH3 ? [urlString] : null);
        const browser = await puppeteer.launch({
            headless: true,
            executablePath: paths.chrome,
            args,
        });

        let gotoUrl = urlString;
        if (urlString.includes('scontent')) {
            if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-100KB') {
                gotoUrl = `file://${paths['100KB']}`;
            } else if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-1MB') {
                gotoUrl = `file://${paths['1MB']}`;
            } else {
                gotoUrl = `file://${paths['5MB']}`;
            }
        }

        for (let j = 0; j < RETRIES; j += 1) {
            try {
                const page = await browser.newPage();
                const har = await new PuppeteerHar(page);

                await har.start();
                await page.goto(gotoUrl, {
                    timeout: 120000,
                });

                const harResult = await har.stop();
                const { entries } = harResult.log;

                await page.close();

                const result = entries.filter((entry) => entry.request.url === urlString);

                if (result.length !== 1) {
                    console.error('Invalid HAR', result);
                    throw Error;
                }

                const entry = result[0];

                console.log(entry.response.httpVersion, entry.time);

                if (isH3 && entry.response.httpVersion === 'h3-29') {
                    timings.push(entry.time);
                    break;
                }

                if (!isH3 && entry.response.httpVersion === 'h2') {
                    timings.push(entry.time);
                    break;
                }
            } catch (error) {
                console.log(j);
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
            for (const size of SIZES) {
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
                const result = await runChrome(urls[size], isH3);

                // Concat result times to existing data
                timings.push(...result);

                // Save data
                fs.writeFileSync(file, JSON.stringify(timings));
            }
        }
    }
};

const runChromeWeb = async (obj, isH3) => {
    const {
        domains, size, url: urlString,
    } = obj;

    const timings = [];

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i} `);

        for (let j = 0; j < RETRIES; j += 1) {
            // Restart browser for each iteration to make things fair...
            fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
            const args = chromeArgs(isH3 ? domains : null);
            const browser = await puppeteer.launch({
                headless: true,
                executablePath: paths.chrome,
                args,
            });

            try {
                const page = await browser.newPage();
                const har = await new PuppeteerHar(page);

                await har.start();
                await page.goto(urlString, {
                    timeout: 120000,
                });

                const harResult = await har.stop();
                const { entries } = harResult.log;

                await page.close();

                const numH2 = entries.filter((entry) => entry.response.httpVersion === 'h2').length;
                const numH3 = entries.filter((entry) => entry.response.httpVersion === 'h3-29').length;
                const payloadBytes = entries.reduce((acc, entry) => acc + entry.response._transferSize, 0);
                const payloadMb = (payloadBytes / 1048576).toFixed(2);

                console.log(`Size: ${payloadMb} mb`);

                if (isH3 && numH2 > 0) {
                    console.log(entries.filter((entry) => entry.response.httpVersion === 'h2').map((entry) => entry.request.url));
                    console.log(`Not enough h3 resources, h2: ${numH2}, h3: ${numH3} `);
                    if (j === RETRIES - 1) {
                        throw Error('Exceeded retries');
                    }
                    // eslint-disable-next-line no-continue
                    continue;
                }


                if (payloadMb < size) {
                    console.log(`Retrieved less than expected payload.Expected: ${size}, Got: ${payloadMb} `);
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

                console.log(`Total: ${entries.length}, h2: ${numH2}, h3: ${numH3}, time: ${time} `);

                timings.push(time);
                break;
            } catch (error) {
                if (j === RETRIES - 1) {
                    console.error('Exceeded retries');
                    throw error;
                }
            } finally {
                await browser.close();
            }
        }
    }

    return timings;
};

const runBenchmarkWeb = async (loss, delay, bw, isH3) => {
    // Read endpoints from endpoints.json
    const endpoints = JSON.parse(fs.readFileSync('endpoints.json', 'utf8'));

    for (const domain of DOMAINS) {
        if (endpoints.hasOwnProperty(domain)) {
            const urls = endpoints[domain];

            for (const size of WEBPAGE_SIZES) {
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

    // H2 - single object
    console.log('Chrome: H2 - single object');
    await runBenchmark(loss, delay, bw, false);

    // H3 - single object
    console.log('Chrome: H3 - single object');
    await runBenchmark(loss, delay, bw, true);

    // H2 - multi object
    console.log('Chrome: H2 - multi object');
    await runBenchmarkWeb(loss, delay, bw, false);

    // H3 - multi object
    console.log('Chrome: H3 - multi object');
    await runBenchmarkWeb(loss, delay, bw, true);
})();
