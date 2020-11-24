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

const toFixedNumber = (num, digits) => {
    const pow = 10 ** digits;
    return Math.round(num * pow) / pow;
};

const getRequestDag = (entries) => {
    const dag = {};

    entries.sort((a, b) => (a._requestTime - b._requestTime));

    const start = entries[0]._requestTime;

    entries.forEach((entry) => {
        const entryUrl = entry.request.url;
        const entryInitiator = entry._initiator;

        dag[entryUrl] = [];

        if (entryInitiator !== undefined) {
            dag[entryInitiator].push({ url: entryUrl, startTime: entry._requestTime - start });
        }
    });

    return dag;
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

const runChromeTracing = async (urlString, isH3) => {
    const domains = [urlString];

    console.log(`${urlString}`);


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

            const dag = getRequestDag(entries);

            console.log(dag);

            const data = JSON.parse(tracing.toString());
            const res = await wprofx.analyzeTrace(data.traceEvents);

            res.size = payloadMb;
            res.time = time;

            console.log(res.criticalPath);

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

    return null;
};

(async () => {
    const parser = new argparse.ArgumentParser();

    parser.add_argument('url');
    parser.add_argument('--h3', { action: argparse.BooleanOptionalAction, help: 'Use h3' });

    const cliArgs = parser.parse_args();

    const {
        url: urlString,
        h3,
    } = cliArgs;

    if (h3) {
        // H3 - multi object
        console.log('Chrome: H3 - multi object');
        await runChromeTracing(urlString, true);
    } else {
        // H2 - multi object
        console.log('Chrome: H2 - multi object');
        await runChromeTracing(urlString, false);
    }
})();
