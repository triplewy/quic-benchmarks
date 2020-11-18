/* eslint-disable no-continue */
/* eslint-disable no-underscore-dangle */
/* eslint-disable no-loop-func */
/* eslint-disable no-prototype-builtins */
/* eslint-disable indent */
/* eslint-disable no-restricted-syntax */
/* eslint-disable no-await-in-loop */
const puppeteer = require('puppeteer');
const PuppeteerHar = require('puppeteer-har');
const argparse = require('argparse');
const Path = require('path');
const fs = require('fs');
const url = require('url');
const short = require('short-uuid');
const Analyze = require('./wprofx/analyze');

const wprofx = new Analyze();

const TRACE_CATEGORIES = [
    '-*',
    'toplevel',
    'blink.console',
    'disabled-by-default-devtools.timeline',
    'devtools.timeline',
    'disabled-by-default-devtools.timeline.frame',
    'devtools.timeline.frame',
    'disabled-by-default-devtools.timeline.stack',
    'disabled-by-default-v8.cpu_profile',
    'disabled-by-default-blink.feature_usage',
    'blink.user_timing',
    'v8.execute',
    'netlog',
];

const RETRIES = 50;

fs.mkdirSync('/tmp/netlog', { recursive: true });

const deleteFolderRecursive = (path) => {
    if (fs.existsSync(path)) {
        fs.readdirSync(path).forEach((file) => {
            const curPath = Path.join(path, file);
            if (fs.lstatSync(curPath).isDirectory()) { // recurse
                deleteFolderRecursive(curPath);
            } else { // delete file
                fs.unlinkSync(curPath);
            }
        });
        fs.rmdirSync(path);
    }
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const toFixedNumber = (num, digits) => {
    const pow = 10 ** digits;
    return Math.round(num * pow) / pow;
};

const chromeArgs = (urls) => {
    const args = [
        '--no-sandbox',
        '--headless',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--user-data-dir=/tmp/chrome-profile',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        '--log-net-log=/tmp/netlog/chrome.json',
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

    console.log(`${urlString}`);

    let gotoUrl;
    if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-100KB') {
        gotoUrl = `file://${Path.join(__dirname, 'html', '100kb.html')}`;
    } else if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-1MB') {
        gotoUrl = `file://${Path.join(__dirname, 'html', '1mb.html')}`;
    } else if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-5MB') {
        gotoUrl = `file://${Path.join(__dirname, 'html', '5mb.html')}`;
    } else {
        gotoUrl = urlString;
    }

    for (let j = 0; j < RETRIES; j += 1) {
        // Restart browser for each iteration to make things fair...
        deleteFolderRecursive('/tmp/chrome-profile');
        const args = chromeArgs(isH3 ? [urlString] : null);
        const browser = await puppeteer.launch({
            args,
        });

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
            const time = entry.time - entry.timings.blocked - entry.timings._queued - entry.timings.dns;
            console.log(entry.response.httpVersion, time);

            if (isH3 && entry.response.httpVersion === 'h3-29') {
                timings.push(time);
                break;
            }

            if (!isH3 && entry.response.httpVersion === 'h2') {
                timings.push(time);
                break;
            }
        } catch (error) {
            console.log(j);
            if (j === RETRIES - 1) {
                console.error('Exceeded retries');
                throw error;
            }
        } finally {
            await browser.close();
        }
    }

    return timings;
};

const runBenchmark = async (urlString, dir, isH3) => {
    // Run benchmark
    const result = await runChrome(urlString, isH3);

    // Create directory
    if (dir !== undefined) {
        let timings = [];

        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir);
        }

        // Read from file if exists
        const file = Path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}_single.json`);
        try {
            timings = JSON.parse(fs.readFileSync(file, 'utf8'));
        } catch (error) {
            //
        }

        // Concat result times to existing data
        timings.push(...result);

        // Save data
        fs.writeFileSync(file, JSON.stringify(timings));
    }
};

const runChromeWeb = async (obj, isH3) => {
    const {
        domains, size, url: urlString,
    } = obj;

    const timings = [];

    // Repeat test ITERATIONS times
    console.log(`${urlString}`);

    for (let j = 0; j < RETRIES; j += 1) {
        // Restart browser for each iteration to make things fair...
        deleteFolderRecursive('/tmp/chrome-profile');
        const args = chromeArgs(isH3 ? domains : null);
        const browser = await puppeteer.launch({
            headless: true,
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
                continue;
            }

            if (payloadMb < size) {
                console.log(`Retrieved less than expected payload.Expected: ${size}, Got: ${payloadMb} `);
                if (j === RETRIES - 1) {
                    throw Error('Exceeded retries');
                }
                continue;
            }

            entries.sort((a, b) => (a._requestTime * 1000 + a.time) - (b._requestTime * 1000 + b.time));

            const start = entries[0]._requestTime * 1000;
            const end = entries[entries.length - 1]._requestTime * 1000 + entries[entries.length - 1].time;
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

    return timings;
};

const runChromeTracing = async (urlString, isH3, dir) => {
    const domains = [urlString];

    console.log(`${urlString}`);

    let chromeDir;

    if (dir !== undefined) {
        chromeDir = Path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}`);
    }

    if (chromeDir !== undefined && !fs.existsSync(chromeDir)) {
        fs.mkdirSync(chromeDir);
    }


    for (let j = 0; j < RETRIES; j += 1) {
        // Restart browser for each iteration to make things fair...
        deleteFolderRecursive('/tmp/chrome-profile', { recursive: true });
        const args = chromeArgs(isH3 ? domains : null);
        const browser = await puppeteer.launch({
            headless: true,
            args,
        });

        try {
            const page = await browser.newPage();
            const har = await new PuppeteerHar(page);

            await har.start();
            await page.tracing.start({ categories: TRACE_CATEGORIES });

            await page.goto(urlString, {
                timeout: 120000,
            });

            const harResult = await har.stop();
            const tracing = await page.tracing.stop();

            await page.close();

            const { entries } = harResult.log;

            const numH2 = entries.filter((entry) => entry.response.httpVersion === 'h2').length;
            const numH3 = entries.filter((entry) => entry.response.httpVersion === 'h3-29').length;
            const payloadBytes = entries.reduce((acc, entry) => acc + entry.response._transferSize, 0);
            const payloadMb = toFixedNumber((payloadBytes / 1048576), 2);

            console.log(`Size: ${payloadMb} mb`);

            if (isH3 && numH2 > 0) {
                domains.push(...entries.filter((entry) => entry.response.httpVersion === 'h2').map((entry) => entry.request.url));
                console.log(`Not enough h3 resources, h2: ${numH2}, h3: ${numH3} `);
                if (j === RETRIES - 1) {
                    throw Error('Exceeded retries');
                }
                continue;
            }

            entries.sort((a, b) => (a._requestTime * 1000 + a.time) - (b._requestTime * 1000 + b.time));

            const start = entries[0]._requestTime * 1000;
            const end = entries[entries.length - 1]._requestTime * 1000 + entries[entries.length - 1].time;
            const time = end - start;

            const data = JSON.parse(tracing.toString());
            const res = await wprofx.analyzeTrace(data.traceEvents);

            res.size = payloadMb;

            if (chromeDir !== undefined) {
                fs.writeFileSync(Path.join(chromeDir, `${short.generate()}.json`), JSON.stringify(res));
            }

            return res;
        } catch (error) {
            console.error(error);
            if (j === RETRIES - 1) {
                console.error('Exceeded retries');
                throw error;
            }
        } finally {
            await browser.close();
        }
    }
};

const runBenchmarkWeb = async (urlString, dir, isH3) => {
    if (dir !== undefined && !fs.existsSync(dir)) {
        fs.mkdirSync(dir);
    }

    const fields = [
        'networkingTimeCp',
        'loadingTimeCp',
        'scriptingTimeCp',
        'firstMeaningfulPaint',
        'firstContentfulPaint',
        'firstPaint',
        'loadEventEnd',
        'domContentLoadedEventEnd',
        'size',
    ];

    const res = await runChromeTracing(urlString, isH3, dir);

    if (dir !== undefined) {
        let timings = {};

        // Read from file if exists
        const file = Path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}_multiple.json`);
        try {
            timings = JSON.parse(fs.readFileSync(file, 'utf8'));
        } catch (error) {
            //
        }

        fields.forEach((field) => {
            if (!timings.hasOwnProperty(field)) {
                timings[field] = [];
            }
            timings[field].push(res[field]);
        });

        // Save data
        fs.writeFileSync(file, JSON.stringify(timings));
    }
 };

(async () => {
    const parser = new argparse.ArgumentParser();

    parser.add_argument('url');
    parser.add_argument('--dir');
    parser.add_argument('--single', { action: argparse.BooleanOptionalAction, help: 'is single object (i.e an image resource vs a web-page)' });
    parser.add_argument('--h3', { action: argparse.BooleanOptionalAction, help: 'Use h3' });
    const cliArgs = parser.parse_args();

    const {
        url: urlString,
        dir,
        single,
        h3,
    } = cliArgs;

    if (single) {
        if (h3) {
            // H3 - single object
            console.log('Chrome: H3 - single object');
            await runBenchmark(urlString, dir, true);
        } else {
            // H2 - single object
            console.log('Chrome: H2 - single object');
            await runBenchmark(urlString, dir, false);
        }
    } else if (h3) {
        // H3 - multi object
        console.log('Chrome: H3 - multi object');
        await runBenchmarkWeb(urlString, dir, true);
    } else {
        // H2 - multi object
        console.log('Chrome: H2 - multi object');
        await runBenchmarkWeb(urlString, dir, false);
    }
})();
