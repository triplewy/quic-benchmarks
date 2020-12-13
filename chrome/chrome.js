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
    'interactive',
];

const ENDPOINTS = JSON.parse(fs.readFileSync(Path.join(__dirname, '..', 'endpoints.json'), 'utf8'));
const CONFIG = JSON.parse(fs.readFileSync(Path.join(__dirname, '..', 'config.json'), 'utf8'));

const RETRIES = 50;
const ITERATIONS = CONFIG.iterations.value;

const DATA_PATH = Path.join(__dirname, '..', CONFIG.data_path.value);
const TMP_DIR = Path.join(DATA_PATH, 'tmp');
const TIMINGS_DIR = Path.join(DATA_PATH, 'timings');
const NETLOG_DIR = Path.join(DATA_PATH, 'netlog');
const WPROFX_DIR = Path.join(DATA_PATH, 'wprofx');
const IMAGE_DIR = Path.join(DATA_PATH, 'images');

fs.mkdirSync(TMP_DIR, { recursive: true });
fs.mkdirSync(TIMINGS_DIR, { recursive: true });
fs.mkdirSync(NETLOG_DIR, { recursive: true });
// fs.mkdirSync(WPROFX_DIR, { recursive: true });
// fs.mkdirSync(IMAGE_DIR, { recursive: true });

const DOMAINS = CONFIG.domains;
const SINGLE_SIZES = CONFIG.sizes.single;
const MULTI_SIZES = CONFIG.sizes.multi;

// const DOMAINS = ['cloudflare'];
// const SINGLE_SIZES = ['100KB'];
// const MULTI_SIZES = ['small'];

const CHROME_PROFILE = Path.join(TMP_DIR, 'chrome-profile');
const TMP_NETLOG = Path.join(TMP_DIR, 'chrome.json');

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

const argsort = (array) => {
    const arrayObject = array.map((value, idx) => ({ value, idx }));
    arrayObject.sort((a, b) => {
        if (a.value < b.value) {
            return -1;
        }
        if (a.value > b.value) {
            return 1;
        }
        return 0;
    });
    return arrayObject.map((data) => data.idx);
};

const hasAltSvc = (entry) => {
    const { headers } = entry.response;
    for (const header of headers) {
        if (header.name === 'alt-svc' && header.value.includes('h3-29')) {
            return true;
        }
    }
    return false;
};

const invertMap = (map) => {
    const result = {};

    Object.entries(map).forEach(([key, value]) => {
        result[value] = key;
    });

    return result;
};

const getNetlogTime = (netlog) => {
    const logEventTypes = invertMap(netlog.constants.logEventTypes);
    const logEventPhase = invertMap(netlog.constants.logEventPhase);

    let start = 0;
    let end = 0;

    for (const event of netlog.events) {
        const eventTime = parseInt(event.time, 10);
        const eventType = logEventTypes[event.type];
        const eventPhase = logEventPhase[event.phase];
        const eventParams = event.params;
        if ((eventType === 'TCP_CONNECT' || eventType === 'QUIC_SESSION') && eventPhase === 'PHASE_BEGIN') {
            start = eventTime;
        }
        if (eventType === 'HTTP2_SESSION_RECV_DATA' && eventParams.stream_id === 1 && eventParams.fin) {
            end = eventTime;
        }
        if (eventType === 'QUIC_SESSION_STREAM_FRAME_RECEIVED') {
            end = eventTime;
        }
    }

    return end - start;
};

const chromeArgs = (urls) => {
    const args = [
        // '--no-sandbox',
        '--headless',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--window-size=1920,1080',
        `--user-data-dir=${CHROME_PROFILE}`,
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        `--log-net-log=${TMP_NETLOG}`,
    ];

    if (urls !== null && urls.length > 0) {
        args.push(
            '--enable-quic',
            '--quic-version=h3-29',
        );

        const origins = new Set();
        urls.forEach((urlString) => {
            const urlObject = url.parse(urlString);
            let port = '443';
            if (urlObject.port !== null) {
                port = urlObject.port;
            }
            origins.add(`${urlObject.host}:${port}`);
        });
        args.push(`--origin-to-force-quic-on=${Array.from(origins).join(',')}`);
    } else {
        args.push(
            '--disable-quic',
        );
    }

    return args;
};

const runChrome = async (urlString, netlogDir, isH3, n) => {
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

    for (let i = n; i < ITERATIONS; i += 1) {
        console.log(`Iteration: ${i}`);

        for (let j = 0; j < RETRIES; j += 1) {
            // Catch browser crashing on linux
            try {
                // Restart browser for each iteration to make things fair...
                deleteFolderRecursive(CHROME_PROFILE);
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
                    const harTime = entry.time - entry.timings.blocked - entry.timings._queued - entry.timings.dns;
                    console.log(entry.response.httpVersion, harTime);

                    if (isH3 && entry.response.httpVersion !== 'h3-29') {
                        throw Error('incorrect protocol');
                    }

                    if (!isH3 && entry.response.httpVersion !== 'h2') {
                        throw Error('incorrect protocol');
                    }
                    await browser.close();

                    const netlogRaw = fs.readFileSync(TMP_NETLOG, { encoding: 'utf-8' });
                    let netlog;
                    try {
                        netlog = JSON.parse(netlogRaw);
                    } catch (error) {
                        // netlog did not flush completely
                        netlog = JSON.parse(`${netlogRaw.substring(0, netlogRaw.length - 1)}]}`);
                    }

                    const time = getNetlogTime(netlog);
                    console.log('netlog time:', time);
                    timings.push(time);
                    fs.writeFileSync(Path.join(netlogDir, `netlog_${i}.json`), JSON.stringify(netlog));

                    break;
                } catch (error) {
                    await browser.close();
                    console.log(j);
                    if (j === RETRIES - 1) {
                        console.error('Exceeded retries');
                        throw error;
                    }
                }
            } catch (error) {
                console.log(j);
                if (j === RETRIES - 1) {
                    console.error('Exceeded retries');
                    throw error;
                }
            }
        }
    }

    return timings;
};

const runBenchmark = async (urlString, timingsDir, netlogDir, isH3) => {
    let timings = [];

    if (!fs.existsSync(timingsDir)) {
        fs.mkdirSync(timingsDir, { recursive: true });
    }
    const realNetlogDir = Path.join(netlogDir, `chrome_${isH3 ? 'h3' : 'h2'}_single`);
    if (!fs.existsSync(realNetlogDir)) {
        fs.mkdirSync(realNetlogDir, { recursive: true });
    }

    // Read from file if exists
    const file = Path.join(timingsDir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
    try {
        timings = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (error) {
        //
    }

    if (timings.length >= ITERATIONS) {
        return;
    }

    // Run benchmark
    const result = await runChrome(urlString, realNetlogDir, isH3, timings.length);

    // Concat result times to existing data
    timings.push(...result);

    // Save data
    fs.writeFileSync(file, JSON.stringify(timings));

    // Get median index of timings
    const medianIndex = argsort(timings)[Math.floor(timings.length / 2)];

    // Remove netlogs that are not median
    fs.readdirSync(realNetlogDir).forEach((f) => {
        const fArr = f.split('.');
        const i = parseInt(fArr[0].split('_')[1], 10);
        if (i !== medianIndex) {
            fs.unlinkSync(Path.join(realNetlogDir, f));
        }
    });
};

const runChromeWeb = async (urlObj, netlogDir, wprofxDir, imageDir, isH3, n) => {
    const { url: urlString, size } = urlObj;

    const domains = [urlString];

    const timings = {
        plt: [],
    };
    LIGHTHOUSE_CATEGORIES.forEach((cat) => {
        timings[cat] = [];
    });

    console.log(`${urlString}`);

    for (let i = n; i < ITERATIONS; i += 1) {
        console.log(`Iteration: ${i}`);

        const wprofx = new Analyze();

        for (let j = 0; j < RETRIES; j += 1) {
            try {
                // Restart browser for each iteration to make things fair...
                deleteFolderRecursive(CHROME_PROFILE);
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
                                onlyAudits: LIGHTHOUSE_CATEGORIES.concat('screenshot-thumbnails'),
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

                    try {
                        const trace = await wprofx.analyzeTrace(artifacts.traces.defaultPass.traceEvents);
                        trace.size = payloadMb;
                        trace.time = time;
                        trace.entries = entries;

                        const plt = trace.loadEventEnd;
                        const fcp = trace.firstContentfulPaint;
                        const wprofxDiff = audits['first-contentful-paint'].numericValue - fcp;
                        timings.plt.push(plt + wprofxDiff);

                        fs.writeFileSync(Path.join(wprofxDir, `wprofx_${i}.json`), JSON.stringify(trace));
                    } catch (error) {
                        console.error(error);
                    }

                    LIGHTHOUSE_CATEGORIES.forEach((cat) => {
                        timings[cat].push(audits[cat].numericValue);
                    });

                    // fs.writeFileSync(`/tmp/lighthouse/${isH3 ? 'H3' : 'H2'}-report-${i}.html`, report);
                    const realImageDir = Path.join(imageDir, `request_${i}`);
                    if (!fs.existsSync(realImageDir)) {
                        fs.mkdirSync(realImageDir, { recursive: true });
                    }
                    audits['screenshot-thumbnails'].details.items.forEach((item, k) => {
                        const base64Data = item.data.replace(/^data:image\/jpeg;base64,/, '');
                        fs.writeFileSync(Path.join(realImageDir, `image_${k}.jpeg`), base64Data, 'base64');
                    });

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

                break;
            } catch (error) {
                console.error(error);
            }
        }

        const netlogRaw = fs.readFileSync(TMP_NETLOG, { encoding: 'utf-8' });
        let netlog;
        try {
            netlog = JSON.parse(netlog);
        } catch (error) {
            // netlog did not flush completely
            netlog = `${netlogRaw.substring(0, netlogRaw.length - 1)}]}`;
        } finally {
            fs.writeFileSync(Path.join(netlogDir, `netlog_${i}.json`), netlog);
        }
    }
    return timings;
};

const runBenchmarkWeb = async (urlObj, timingsDir, wprofxDir, netlogDir, imageDir, isH3) => {
    let timings = {
        plt: [],
    };
    LIGHTHOUSE_CATEGORIES.forEach((cat) => {
        timings[cat] = [];
    });

    // Create directories
    if (!fs.existsSync(timingsDir)) {
        fs.mkdirSync(timingsDir, { recursive: true });
    }
    const realNetlogDir = Path.join(netlogDir, `chrome_${isH3 ? 'h3' : 'h2'}_multi`);

    if (!fs.existsSync(realNetlogDir)) {
        fs.mkdirSync(realNetlogDir, { recursive: true });
    }
    const realWprofxDir = Path.join(wprofxDir, `chrome_${isH3 ? 'h3' : 'h2'}`);

    if (!fs.existsSync(realWprofxDir)) {
        fs.mkdirSync(realWprofxDir, { recursive: true });
    }
    const realImageDir = Path.join(imageDir, `chrome_${isH3 ? 'h3' : 'h2'}`);

    if (!fs.existsSync(realImageDir)) {
        fs.mkdirSync(realImageDir, { recursive: true });
    }

    // Read from timings file if exists
    const file = Path.join(timingsDir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
    try {
        timings = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (error) {
        //
    }

    if (timings['speed-index'].length >= ITERATIONS) {
        return;
    }

    const prevLength = timings['speed-index'].length;

    // Run benchmark
    const result = await runChromeWeb(urlObj, realNetlogDir, realWprofxDir, realImageDir, isH3, prevLength);

    // Concat result times to existing data
    Object.keys(timings).forEach((key) => {
        timings[key].push(...result[key]);
    });

    // Save data
    fs.writeFileSync(file, JSON.stringify(timings));

    // Get median index of timings
    const medianIndexes = new Set(['plt'].concat(LIGHTHOUSE_CATEGORIES)
        .map((cat) => argsort(timings[cat])[Math.floor(timings[cat].length / 2)]));

    // Remove netlogs that are not median
    fs.readdirSync(realNetlogDir).forEach((f) => {
        const fArr = f.split('.');
        const i = parseInt(fArr[0].split('_')[1], 10);
        if (!medianIndexes.has(i)) {
            fs.unlinkSync(Path.join(realNetlogDir, f));
        }
    });

    // Remove traces that are not median
    fs.readdirSync(realWprofxDir).forEach((f) => {
        const fArr = f.split('.');
        const i = parseInt(fArr[0].split('_')[1], 10);
        if (!medianIndexes.has(i)) {
            fs.unlinkSync(Path.join(realWprofxDir, f));
        }
    });

    // Remove image directories that are not median
    fs.readdirSync(realImageDir).forEach((d) => {
        const i = parseInt(d.split('_')[1], 10);
        if (!medianIndexes.has(i)) {
            deleteFolderRecursive(Path.join(realImageDir, d));
        }
    });
};

(async () => {
    const parser = new argparse.ArgumentParser();

    parser.add_argument('--dir');
    parser.add_argument('--single', { action: argparse.BooleanOptionalAction, help: 'is single object (i.e an image resource vs a web-page)' });
    const cliArgs = parser.parse_args();

    const {
        dir,
        single,
    } = cliArgs;

    const sizes = single ? SINGLE_SIZES : MULTI_SIZES;

    for (const domain of DOMAINS) {
        for (const size of sizes) {
            if (!(size in ENDPOINTS[domain])) {
                continue;
            }

            const urlObj = ENDPOINTS[domain][size];
            const timingsDir = Path.join(TIMINGS_DIR, dir, domain, size);
            const wprofxDir = Path.join(WPROFX_DIR, dir, domain, size);
            const netlogDir = Path.join(NETLOG_DIR, dir, domain, size);
            const imageDir = Path.join(IMAGE_DIR, dir, domain, size);

            console.log(`${domain}/${size}`);

            if (single) {
                console.log('Chrome: H2 - single object');
                await runBenchmark(urlObj, timingsDir, netlogDir, false);
                console.log('Chrome: H3 - single object');
                await runBenchmark(urlObj, timingsDir, netlogDir, true);
            } else {
                console.log('Chrome: H3 - multi object');
                await runBenchmarkWeb(urlObj, timingsDir, wprofxDir, netlogDir, imageDir, true);
                console.log('Chrome: H2 - multi object');
                await runBenchmarkWeb(urlObj, timingsDir, wprofxDir, netlogDir, imageDir, false);
            }
        }
    }
})();
