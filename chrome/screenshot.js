/* eslint-disable no-console */
/* eslint-disable max-len */
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
const lighthouse = require('lighthouse');
const chromeHar = require('chrome-har');
const Analyze = require('./wprofx/analyze');

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

const LIGHTHOUSE_CATEGORIES = [
    'screenshot-thumbnails',
    'final-screenshot',
    'speed-index',
];

const RETRIES = 50;

const CONFIG = JSON.parse(fs.readFileSync(Path.join(__dirname, '..', 'endpoints.json'), 'utf8'));
const DOMAINS = ['google', 'facebook', 'cloudflare'];
// const DOMAINS = ['cloudflare'];
const SIZES = ['small', 'medium', 'large'];
// const SIZES = ['medium'];

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

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const hasAltSvc = (entry) => {
    const { headers } = entry.response;
    for (const header of headers) {
        if (header.name === 'alt-svc' && header.value.includes('h3-29')) {
            return true;
        }
    }
    return false;
};

const chromeArgs = (urls, isH3) => {
    const args = [
        '--no-sandbox',
        '--headless',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--user-data-dir=/tmp/chrome-profile',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        `--log-net-log=/tmp/netlog/${isH3 ? 'H3' : 'H2'}-chrome.json`,
    ];

    if (urls !== null && urls.length > 0) {
        args.push(
            '--enable-quic',
            '--quic-version=h3-29',
        );

        const origins = new Set();
        urls.forEach((urlString) => {
            const urlObject = url.parse(urlString);
            origins.add(`${urlObject.host}:443`);
        });
        args.push(`--origin-to-force-quic-on=${Array.from(origins).join(',')}`);
    } else {
        args.push(
            '--disable-quic',
        );
    }

    return args;
};

const runChromeWeb = async (urlString, isH3) => {
    const domains = [urlString];

    console.log(`${urlString}`);

    for (let i = 0; i < 3; i += 1) {
        for (let j = 0; j < RETRIES; j += 1) {
            // Restart browser for each iteration to make things fair...
            deleteFolderRecursive('/tmp/chrome-profile');
            const args = chromeArgs(isH3 ? domains : null, isH3);
            const browser = await puppeteer.launch({
                headless: true,
                defaultViewport: null,
                args,
            });

            try {
                const { lhr: { audits }, artifacts, report } = await lighthouse(
                    urlString,
                    {
                        port: (new URL(browser.wsEndpoint())).port,
                        output: 'html',
                    },
                    {
                        extends: 'lighthouse:default',
                        settings: {
                            additionalTraceCategories: TRACE_CATEGORIES.join(','),
                            onlyAudits: LIGHTHOUSE_CATEGORIES,
                            throttlingMethod: 'provided',
                            emulatedFormFactor: 'none',
                        },
                    },
                );

                if ('pageLoadError-defaultPass' in artifacts.devtoolsLogs) {
                    await sleep(10000);
                    throw Error('Webpage throttling');
                }

                const { log: { entries } } = chromeHar.harFromMessages(artifacts.devtoolsLogs.defaultPass);

                const h2Resources = new Set(entries.filter((entry) => entry.response.httpVersion === 'h2')
                    .map((entry) => entry.request.url));
                const h3Resources = new Set(entries.filter((entry) => entry.response.httpVersion === 'h3-29')
                    .map((entry) => entry.request.url));
                const altSvc = new Set(entries.filter((entry) => hasAltSvc(entry))
                    .map((entry) => entry.request.url));

                const numH2 = h2Resources.size;
                const numH3 = h3Resources.size;

                const difference = new Set([...altSvc].filter((x) => !h3Resources.has(x)));

                const payloadBytes = entries.reduce((acc, entry) => acc + entry.response._transferSize, 0);
                const payloadMb = (payloadBytes / 1048576).toFixed(2);
                console.log(`Size: ${payloadMb} mb`);

                if (isH3 && difference.size > 0) {
                    console.log(difference);
                    if (urlString === 'https://www.facebook.com/') {
                        domains.push(...entries.filter((entry) => entry.response.httpVersion !== 'h3').map((entry) => entry.request.url));
                    } else {
                        domains.push(...difference);
                    }
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

                console.log(`Total: ${entries.length}, h2: ${numH2}, h3: ${numH3}, time: ${time} `);

                fs.writeFileSync(`/tmp/lighthouse/${isH3 ? 'H3' : 'H2'}-report.html`, report);

                for (const cat of LIGHTHOUSE_CATEGORIES) {
                    if (cat === 'speed-index') {
                        continue;
                    }
                    const { details } = audits[cat];

                    if (cat === 'final-screenshot') {
                        console.log(details.timing);

                        const base64Data = details.data.replace(/^data:image\/jpeg;base64,/, '');

                        fs.writeFileSync(`/tmp/lighthouse/screenshots/${isH3 ? 'H3' : 'H2'}-final.jpeg`, base64Data, 'base64');
                    } else {
                        const { items } = details;

                        items.forEach((item, k) => {
                            const base64Data = item.data.replace(/^data:image\/jpeg;base64,/, '');

                            fs.writeFileSync(`/tmp/lighthouse/screenshots/${isH3 ? 'H3' : 'H2'}-${k}.jpeg`, base64Data, 'base64');
                        });
                    }
                }
                break;
            } catch (error) {
                console.log('Retrying...');
                console.error(error);
                if (j === RETRIES - 1) {
                    console.error('Exceeded retries');
                    throw error;
                }
            } finally {
                await browser.close();
            }
        }
    }
};

(async () => {
    const parser = new argparse.ArgumentParser();

    // parser.add_argument('url');
    parser.add_argument('--domain');
    parser.add_argument('--size');
    const cliArgs = parser.parse_args();

    const {
        // url: urlString,
        domain,
        size,
    } = cliArgs;


    const urlObj = CONFIG[domain][size];


    console.log('Chrome: H2 - multi object analysis');
    await runChromeWeb(urlObj.url, false);

    console.log('Chrome: H3 - multi object analysis');
    await runChromeWeb(urlObj.url, true);
})();
