/* eslint-disable no-underscore-dangle */
/* eslint-disable no-loop-func */
/* eslint-disable no-prototype-builtins */
/* eslint-disable indent */
/* eslint-disable no-restricted-syntax */
/* eslint-disable no-await-in-loop */
const puppeteer = require('puppeteer-core');
const PuppeteerHar = require('puppeteer-har');

const argparse = require('argparse');
const fs = require('fs');
const url = require('url');
const math = require('mathjs');

const RETRIES = 5;

const paths = JSON.parse(fs.readFileSync('paths.json', 'utf8'));

const chromeArgs = (urlString) => {
    const args = [
        '--user-data-dir=/tmp/chrome-profile',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        '--log-net-log=/tmp/netlog/chrome.json',
        '--enable-quic',
        '--quic-version=h3-29',
        '--ignore-certificate-errors',
        '--ignore-urlfetcher-cert-requests',
    ];


    const urlObject = url.parse(urlString);
    let { port } = urlObject;
    if (port === null) {
        port = 443;
    }
    args.push(`--origin-to-force-quic-on=${urlObject.host}:${port}`);

    return args;
};

const runChrome = async (urlString) => {
    let time;

    // fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
    const args = chromeArgs(urlString);
    const browser = await puppeteer.launch({
        headless: true,
        executablePath: paths.chrome,
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

            await page.close();

            const result = entries.filter((entry) => entry.request.url === urlString);

            if (result.length !== 1) {
                console.error('Invalid HAR', result);
                throw Error;
            }

            const entry = result[0];

            if (entry.response.httpVersion === 'h3-29') {
                time = entry.time;
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

    return time / 1000;
};

(async () => {
    // Get network scenario from command line arguments
    const parser = new argparse.ArgumentParser();

    parser.add_argument('-n', '--num');
    parser.add_argument('url');

    const cliArgs = parser.parse_args();

    const num = parseInt(cliArgs.num, 10);
    const urlString = cliArgs.url;

    const times = [];
    for (let i = 0; i < num; i += 1) {
        const time = await runChrome(urlString);
        times.push(time);
    }

    const mean = math.mean(times).toFixed(3);
    const std = math.std(times).toFixed(3);
    const min = math.min(times).toFixed(3);
    const max = math.max(times).toFixed(3);
    const median = math.median(times).toFixed(3);

    console.log(`Mean: ${mean}, Std Dev: ${std}, Min: ${min}, Max: ${max}, Median: ${median}`);
})();
