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

const ENDPOINTS = JSON.parse(fs.readFileSync(Path.join(__dirname, '..', 'endpoints.json'), 'utf8'));
const CONFIG = JSON.parse(fs.readFileSync(Path.join(__dirname, '..', 'config.json'), 'utf8'));

const RETRIES = 50;
const ITERATIONS = CONFIG.iterations.value;

const DATA_PATH = Path.join(__dirname, '..', CONFIG.data_path.value);
const TMP_DIR = Path.join(DATA_PATH, 'tmp');
const TIMINGS_DIR = Path.join(DATA_PATH, 'timings');
const NETLOG_DIR = Path.join(DATA_PATH, 'netlog');
const METRICS_DIR = Path.join(DATA_PATH, 'metrics')

fs.mkdirSync(TMP_DIR, { recursive: true });
fs.mkdirSync(TIMINGS_DIR, { recursive: true });
fs.mkdirSync(NETLOG_DIR, { recursive: true });
fs.mkdirSync(METRICS_DIR, { recursive: true });


const DOMAINS = CONFIG.domains;
const SINGLE_SIZES = CONFIG.sizes.single;

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
    let initRtt = null;

    let firstDataPktTime = null
    let initCwndMss = 0;
    let initCwndBytes = 0;

    for (const event of netlog.events) {
        const eventTime = parseInt(event.time, 10);
        const eventType = logEventTypes[event.type];
        const eventPhase = logEventPhase[event.phase];
        const eventParams = event.params;

        if (eventType === 'TCP_CONNECT') {
            if (eventPhase === 'PHASE_BEGIN') {
                start = eventTime;
            } else {
                initRtt = eventTime - start;
            }
        }
        if (eventType === 'QUIC_SESSION_PACKET_SENT'
            && eventParams['encryption_level'] === 'ENCRYPTION_INITIAL'
            && start === 0) {
            start = eventTime;
        }
        if (eventType === 'QUIC_SESSION_UNAUTHENTICATED_PACKET_HEADER_RECEIVED'
            && eventParams['long_header_type'] === 'INITIAL'
            && initRtt === null) {
            initRtt = eventTime - start;
        }

        if ((eventType === 'HTTP2_SESSION_RECV_HEADERS' || eventType === 'HTTP3_HEADERS_RECEIVED')
            && firstDataPktTime === null) {
            firstDataPktTime = eventTime;
        }

        if (eventType === 'HTTP2_SESSION_RECV_DATA' && eventParams.stream_id === 1) {
            if (firstDataPktTime !== null && eventTime <= firstDataPktTime + initRtt) {
                initCwndBytes += eventParams['size'];
            }
            if (eventParams.fin) {
                end = eventTime;
            }
        }

        if (eventType === 'QUIC_SESSION_STREAM_FRAME_RECEIVED') {
            if (eventParams['stream_id'] === 0 && firstDataPktTime !== null && eventTime <= firstDataPktTime + initRtt) {
                initCwndMss += 1;
                initCwndBytes += eventParams['length'];
            }
            end = eventTime;
        }
    }
    console.log('initRtt', initRtt);
    return {
        'time': end - start,
        initCwndMss,
        initCwndBytes
    };
};

const chromeArgs = (urls, log) => {
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
    ];

    if (log) {
        args.push(`--log-net-log=${TMP_NETLOG}`);
    }

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
            origins.add(`${urlObject.host.split(':')[0]}:${port}`);
        });
        args.push(`--origin-to-force-quic-on=${Array.from(origins).join(',')}`);
    } else {
        args.push(
            '--disable-quic',
        );
    }

    return args;
};

const runChrome = async (urlString, netlogDir, isH3, n, log) => {
    const metrics = [];
    const timings = [];

    console.log(`${urlString}`);

    let gotoUrl;
    if (urlString.includes('speedtest-100KB')) {
        gotoUrl = `file://${Path.join(__dirname, 'html', '100kb.html')}`;
    } else if (urlString.includes('speedtest-1MB')) {
        gotoUrl = `file://${Path.join(__dirname, 'html', '1mb.html')}`;
    } else if (urlString.includes('speedtest-5MB')) {
        gotoUrl = `file://${Path.join(__dirname, 'html', '5mb.html')}`;
    } else {
        gotoUrl = urlString;
    }

    for (let i = n; i < ITERATIONS; i += 1) {
        if (netlogDir.includes('LTE')) {
            await sleep(10000);
        }

        console.log(`Iteration: ${i}`);

        for (let j = 0; j < RETRIES; j += 1) {
            // Catch browser crashing on linux
            try {
                // Restart browser for each iteration to make things fair...
                deleteFolderRecursive(CHROME_PROFILE);
                const args = chromeArgs(isH3 ? [urlString] : null, log);
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

                    if (entry.response.status !== 200) {
                        console.error('Unsuccessful request');
                        throw Error;
                    }

                    const harTime = entry.time - entry.timings.blocked - entry.timings._queued - entry.timings.dns;
                    console.log(entry.response.httpVersion, harTime);

                    if (isH3 && entry.response.httpVersion !== 'h3-29') {
                        throw Error('incorrect protocol');
                    }

                    if (!isH3 && entry.response.httpVersion !== 'h2') {
                        throw Error('incorrect protocol');
                    }
                    await browser.close();

                    if (!log) {
                        timings.push(harTime);
                        break;
                    }

                    const netlogRaw = fs.readFileSync(TMP_NETLOG, { encoding: 'utf-8' });
                    let netlog;
                    try {
                        netlog = JSON.parse(netlogRaw);
                    } catch (error) {
                        // netlog did not flush completely
                        netlog = JSON.parse(`${netlogRaw.substring(0, netlogRaw.length - 1)}]}`);
                    }

                    const res = getNetlogTime(netlog);
                    const time = res.time;
                    console.log(res);
                    console.log('netlog time:', time);
                    metrics.push(res);
                    timings.push(time);
                    fs.writeFileSync(Path.join(netlogDir, `netlog_${i}.json`), JSON.stringify(netlog));

                    break;
                } catch (error) {
                    await browser.close();
                    console.error(error);
                    if (j === RETRIES - 1) {
                        console.error('Exceeded retries');
                        throw error;
                    }
                }
            } catch (error) {
                console.error(error);
                if (j === RETRIES - 1) {
                    console.error('Exceeded retries');
                    throw error;
                }
            }
        }
    }

    return { timings, metrics };
};

const runBenchmark = async (urlString, timingsDir, netlogDir, metricsDir, isH3, log) => {
    // Create timings and metrics dirs
    let timings = [];
    if (!fs.existsSync(timingsDir)) {
        fs.mkdirSync(timingsDir, { recursive: true });
    }
    let metrics = [];
    if (!fs.existsSync(metricsDir)) {
        fs.mkdirSync(metricsDir, { recursive: true });
    }

    // Create netlog dir for either h2 or h3
    const realNetlogDir = Path.join(netlogDir, `chrome_${isH3 ? 'h3' : 'h2'}_single`);
    if (!fs.existsSync(realNetlogDir)) {
        fs.mkdirSync(realNetlogDir, { recursive: true });
    }

    // Read timings and metrics file if they exist
    const timings_file = Path.join(timingsDir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
    try {
        timings = JSON.parse(fs.readFileSync(timings_file, 'utf8'));
    } catch (error) {
        //
    }
    const metrics_file = Path.join(metricsDir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
    try {
        metrics = JSON.parse(fs.readFileSync(metrics_file, 'utf8'));
    } catch (error) {
        //
    }

    if (timings.length >= ITERATIONS) {
        return;
    }

    // Run benchmark
    const result = await runChrome(urlString, realNetlogDir, isH3, timings.length, log);

    // Concat result times to existing data
    timings.push(...result.timings);
    metrics.push(...result.metrics);

    // Save data
    fs.writeFileSync(timings_file, JSON.stringify(timings));
    fs.writeFileSync(metrics_file, JSON.stringify(metrics));

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

(async () => {
    const parser = new argparse.ArgumentParser();

    parser.add_argument('--dir');
    parser.add_argument('--log', { action: argparse.BooleanOptionalAction, help: 'Log netlog', default: false });
    const cliArgs = parser.parse_args();

    const {
        dir,
        single,
        log
    } = cliArgs;

    const clients = CONFIG.clients.filter(client => client.includes("chrome"));
    const sizes = SINGLE_SIZES;

    for (const domain of DOMAINS) {
        for (const size of sizes) {
            if (!(size in ENDPOINTS[domain])) {
                continue;
            }

            const urlObj = ENDPOINTS[domain][size];
            const timingsDir = Path.join(TIMINGS_DIR, dir, domain, size);
            const netlogDir = Path.join(NETLOG_DIR, dir, domain, size);
            const metricsDir = Path.join(METRICS_DIR, dir, domain, size);

            console.log(`${domain}/${size}`);

            for (const client of clients) {
                const isH3 = client == 'chrome_h3'
                console.log(`Chrome: ${isH3 ? 'H3' : 'H2'} - single object`);
                await runBenchmark(urlObj, timingsDir, netlogDir, metricsDir, isH3, log);
            }
        }
    }
})();
