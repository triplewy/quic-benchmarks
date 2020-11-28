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
    'first-contentful-paint',
    'first-meaningful-paint',
    'largest-contentful-paint',
    'speed-index',
];

const RETRIES = 50;
const ITERATIONS = 40;

const HAR_DIR = Path.join(__dirname, '..', 'har');
const ANALYSIS_DIR = Path.join(__dirname, '..', 'analysis_data');
const CONFIG = JSON.parse(fs.readFileSync(Path.join(__dirname, '..', 'endpoints.json'), 'utf8'));
const DOMAINS = ['google', 'facebook', 'cloudflare'];
// const DOMAINS = ['facebook'];
const SINGLE_SIZES = ['100KB', '1MB', '5MB'];
const SIZES = ['small', 'medium', 'large'];
// const SIZES = ['small'];

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

    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`Iteration: ${i}`);

        for (let j = 0; j < RETRIES; j += 1) {
            // Restart browser for each iteration to make things fair...
            deleteFolderRecursive('/tmp/chrome-profile');
            const args = chromeArgs(isH3 ? [urlString] : null);
            const browser = await puppeteer.launch({
                headless: true,
                defaultViewport: null,
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
    }

    return timings;
};

const runBenchmarkOld = async (urlObj, dir, isH3) => {
    const urlString = urlObj;

    // Run benchmark
    const result = await runChrome(urlString, isH3);

    // Create directory
    if (dir !== undefined) {
        let timings = [];

        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        // Read from file if exists
        const file = Path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
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

const runChromeWeb = async (urlString, size, isH3) => {
    const domains = [urlString];

    const timings = {
        'first-contentful-paint': [],
        'first-meaningful-paint': [],
        'largest-contentful-paint': [],
        'speed-index': [],
    };

    const traces = [];

    console.log(`${urlString}`);

    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`Iteration: ${i}`);

        const wprofx = new Analyze();

        for (let j = 0; j < RETRIES; j += 1) {
            // This webpage incurs throttling
            if (urlString === 'https://dash.cloudflare.com/login/' && isH3) {
                await sleep(2000);
            }

            // Restart browser for each iteration to make things fair...
            deleteFolderRecursive('/tmp/chrome-profile');
            const args = chromeArgs(isH3 ? domains : null);
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

                const numH2 = entries.filter((entry) => entry.response.httpVersion === 'h2').length;
                const numH3 = entries.filter((entry) => entry.response.httpVersion === 'h3-29').length;

                if (isH3 && numH2 > 0) {
                    console.log(entries.filter((entry) => entry.response.httpVersion === 'h2').map((entry) => entry.request.url));
                    if (urlString === 'https://www.facebook.com/') {
                        domains.push(...entries.filter((entry) => entry.response.httpVersion !== 'h3').map((entry) => entry.request.url));
                    } else {
                        domains.push(...entries.filter((entry) => entry.response.httpVersion === 'h2').map((entry) => entry.request.url));
                    }
                    console.log(`Not enough h3 resources, h2: ${numH2}, h3: ${numH3} `);
                    if (j === RETRIES - 1) {
                        throw Error('Exceeded retries');
                    }
                    continue;
                }

                const payloadBytes = entries.reduce((acc, entry) => acc + entry.response._transferSize, 0);
                const payloadMb = (payloadBytes / 1048576).toFixed(2);
                console.log(`Size: ${payloadMb} mb`);

                // if (payloadMb < size) {
                //     console.log(`Retrieved less than expected payload.Expected: ${size}, Got: ${payloadMb} `);
                //     if (j === RETRIES - 1) {
                //         throw Error('Exceeded retries');
                //     }
                //     continue;
                // }

                entries.sort((a, b) => (a._requestTime * 1000 + a.time) - (b._requestTime * 1000 + b.time));

                const start = entries[0]._requestTime * 1000;
                const end = entries[entries.length - 1]._requestTime * 1000 + entries[entries.length - 1].time;
                const time = end - start;

                console.log(`Total: ${entries.length}, h2: ${numH2}, h3: ${numH3}, time: ${time} `);

                const res = await wprofx.analyzeTrace(artifacts.traces.defaultPass.traceEvents);
                res.size = payloadMb;
                res.time = time;
                res.entries = entries;

                LIGHTHOUSE_CATEGORIES.forEach((cat) => {
                    timings[cat].push(audits[cat].numericValue);
                });

                traces.push(res);

                fs.writeFileSync(`/tmp/lighthouse/${isH3 ? 'H3' : 'H2'}-report-${i}.html`, report);

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
    return { timings, traces };
};

const runBenchmarkWebOld = async (urlObj, harDir, traceDir, isH3) => {
    const { url: urlString, size } = urlObj;

    // Run benchmark
    const { timings: result, traces } = await runChromeWeb(urlString, size, isH3);

    // Create directory
    if (harDir !== undefined) {
        let timings = {
            'first-contentful-paint': [],
            'first-meaningful-paint': [],
            'largest-contentful-paint': [],
            'speed-index': [],
        };

        if (!fs.existsSync(harDir)) {
            fs.mkdirSync(harDir, { recursive: true });
        }

        // Read from file if exists
        const file = Path.join(harDir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
        try {
            timings = JSON.parse(fs.readFileSync(file, 'utf8'));
        } catch (error) {
            //
        }

        // Concat result times to existing data
        Object.keys(timings).forEach((key) => {
            timings[key].push(...result[key]);
        });

        // Save data
        fs.writeFileSync(file, JSON.stringify(timings));
    }

    if (traceDir !== undefined) {
        const realTraceDir = Path.join(traceDir, `chrome_${isH3 ? 'h3' : 'h2'}`);

        if (!fs.existsSync(realTraceDir)) {
            fs.mkdirSync(realTraceDir, { recursive: true });
        }

        // Write all traces to disk as well
        traces.forEach((trace, i) => {
            fs.writeFileSync(Path.join(realTraceDir, `trace-${i}.json`), JSON.stringify(trace));
        });
    }
};

const runChromeTracing = async (urlString, size, isH3) => {
    const results = [];
    const domains = [urlString];

    console.log(`${urlString}`);

    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`Iteration: ${i}`);

        const wprofx = new Analyze();

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

                if (isH3 && numH2 > 0) {
                    console.log(entries.filter((entry) => entry.response.httpVersion === 'h2').map((entry) => entry.request.url));
                    if (urlString === 'https://www.facebook.com/') {
                        domains.push(...entries.filter((entry) => entry.response.httpVersion !== 'h3').map((entry) => entry.request.url));
                    } else {
                        domains.push(...entries.filter((entry) => entry.response.httpVersion === 'h2').map((entry) => entry.request.url));
                    }
                    console.log(`Not enough h3 resources, h2: ${numH2}, h3: ${numH3} `);
                    if (j === RETRIES - 1) {
                        throw Error('Exceeded retries');
                    }
                    continue;
                }

                const payloadBytes = entries.reduce((acc, entry) => acc + entry.response._transferSize, 0);
                const payloadMb = (payloadBytes / 1048576).toFixed(2);
                console.log(`Size: ${payloadMb} mb`);

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

                const data = JSON.parse(tracing.toString());
                const res = await wprofx.analyzeTrace(data.traceEvents);

                res.size = payloadMb;
                res.time = time;
                res.entries = entries;

                results.push(res);
                break;
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
    }

    return results;
};

const runBenchmarkWeb = async (urlObj, dir, isH3) => {
    const { url: urlString, size } = urlObj;

    let realDir;

    if (dir !== undefined) {
        realDir = Path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}`);

        if (!fs.existsSync(realDir)) {
            fs.mkdirSync(realDir, { recursive: true });
        }
    }

    const results = await runChromeTracing(urlString, size, isH3);

    if (realDir !== undefined) {
        results.forEach((res) => {
            const file = Path.join(realDir, `${short.generate()}.json`);

            // Save data
            fs.writeFileSync(file, JSON.stringify(res));
        });
    }
};

(async () => {
    const parser = new argparse.ArgumentParser();

    // parser.add_argument('url');
    parser.add_argument('--dir');
    parser.add_argument('--single', { action: argparse.BooleanOptionalAction, help: 'is single object (i.e an image resource vs a web-page)' });
    parser.add_argument('--analysis', { action: argparse.BooleanOptionalAction, default: false, help: 'Perform critical path analysis on web-page' });
    parser.add_argument('--domain');
    parser.add_argument('--size');
    const cliArgs = parser.parse_args();

    const {
        // url: urlString,
        dir,
        single,
        analysis,
        domain: analysisDomain,
        size: analysisSize,
    } = cliArgs;

    if (analysis) {
        if (analysisDomain === undefined || analysisSize === undefined || dir === undefined) {
            throw Error('Analysis not enough inputs');
        }

        const analysisDir = Path.join(ANALYSIS_DIR, dir, analysisDomain, analysisSize);

        const urlObj = CONFIG[analysisDomain][analysisSize];

        console.log('Chrome: H3 - multi object analysis');
        await runBenchmarkWeb(urlObj, analysisDir, true);
        console.log('Chrome: H2 - multi object analysis');
        await runBenchmarkWeb(urlObj, analysisDir, false);

        return;
    }

    const sizes = single ? SINGLE_SIZES : SIZES;

    for (const domain of DOMAINS) {
        for (const size of sizes) {
            if (!(size in CONFIG[domain])) {
                continue;
            }
            if (domain === 'cloudflare' && size === 'medium') {
                continue;
            }

            const urlObj = CONFIG[domain][size];
            const harDir = Path.join(HAR_DIR, dir, domain, size);
            const traceDir = Path.join(ANALYSIS_DIR, dir, domain, size);

            console.log(`${domain}/${size}`);

            if (single) {
                console.log('Chrome: H2 - single object');
                await runBenchmarkOld(urlObj, harDir, false);
                console.log('Chrome: H3 - single object');
                await runBenchmarkOld(urlObj, harDir, true);
            } else {
                console.log('Chrome: H2 - multi object');
                await runBenchmarkWebOld(urlObj, harDir, traceDir, false);
                console.log('Chrome: H3 - multi object');
                await runBenchmarkWebOld(urlObj, harDir, traceDir, true);
            }
        }
    }
})();
