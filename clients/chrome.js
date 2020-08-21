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

const ITERATIONS = 10;
const RETRIES = 5;
const DOMAINS = ['facebook', 'cloudflare', 'google'];
const sizes = ['100KB', '1MB', '5MB'];

const chromeArgs = (urlString) => {
    const args = [
        '--user-data-dir=/tmp/chrome-profile',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        // '--log-net-log=/tmp/netlog',
    ];

    if (urlString !== '') {
        const urlObject = url.parse(urlString);

        args.push(
            '--enable-quic',
            '--quic-version=h3-29',
            `--origin-to-force-quic-on=${urlObject.host}:443`,
        );
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
        fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
        const args = chromeArgs(isH3 ? urlString : '');
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

                const result = entries.filter((entry) => entry.request.url === urlString);

                if (result.length !== 1) {
                    console.error('Invalid HAR');
                    throw Error;
                }

                const entry = result[0];

                await page.close();

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
            for (const size of sizes) {
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

(async () => {
    // Get network scenario from command line arguments
    const parser = new argparse.ArgumentParser();

    parser.add_argument('loss');
    parser.add_argument('delay');
    parser.add_argument('bw');

    const cliArgs = parser.parse_args();

    const { loss, delay, bw } = cliArgs;

    // Benchmark H2 first
    console.log('Chrome: benchmarking H2');

    await runBenchmark(loss, delay, bw, false);

    // Test H3 - Chrome
    console.log('Chrome: benchmarking H3');

    await runBenchmark(loss, delay, bw, true);
})();
