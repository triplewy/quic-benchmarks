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
const path = require('path');
const fs = require('fs');
const url = require('url');
const Analyze = require('./wprofx/analyze');

const wprofx = new Analyze();

const config = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config.json'), 'utf8'));
const endpoints = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'endpoints.json'), 'utf8'));

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
const CHROME_PATH = config.paths.chrome;
const ITERATIONS = config.iterations;

const RETRIES = 50;

fs.mkdirSync('/tmp/netlog', { recursive: true });

const chromeArgs = (urls) => {
    const args = [
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

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);

        // Restart browser for each iteration to make things fair...
        fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
        const args = chromeArgs(isH3 ? [urlString] : null);
        const browser = await puppeteer.launch({
            headless: true,
            args,
        });

        let gotoUrl;
        if (urlString.includes('scontent')) {
            if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-100KB') {
                gotoUrl = `file://${config.paths['100KB']}`;
            } else if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-1MB') {
                gotoUrl = `file://${config.paths['1MB']}`;
            } else if (urlString === 'https://scontent.xx.fbcdn.net/speedtest-5MB') {
                gotoUrl = `file://${config.paths['5MB']}`;
            } else {
                gotoUrl = urlString;
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
            }
        }

        await browser.close();
    }

    return timings;
};

const runBenchmark = async (urlString, dir, isH3) => {
    // Create directory
    const dirpath = path.join(dir, 'chrome', `loss-${loss}_delay-${delay}_bw-${bw}`, domain, size);
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
    const result = await runChrome(urlString, isH3);

    // Concat result times to existing data
    timings = timings.concat(...result);

    // Save data
    fs.writeFileSync(file, JSON.stringify(timings));
};

const runChromeWeb = async (obj, isH3, isAnalysis) => {
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

                entries.sort((a, b) => (a._requestTime * 1000 + a.time) - (b._requestTime * 1000 + b.time));

                const start = entries[0]._requestTime * 1000;
                const end = entries[entries.length - 1]._requestTime * 1000 + entries[entries.length - 1].time;
                const time = end - start;

                console.log(`Total: ${entries.length}, h2: ${numH2}, h3: ${numH3}, time: ${time} `);

                if (isAnalysis) {
                    timings.push(entries);

                    // move netlog
                    fs.renameSync('/tmp/netlog/chrome.json', `/tmp/netlog/chrome_${isH3 ? 'h3' : 'h2'}_${30 + i}.json`);
                } else {
                    timings.push(time);
                }
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

const runChromeTracing = async (obj, isH3) => {
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
                args,
            });

            try {
                const page = await browser.newPage();
                const har = await new PuppeteerHar(page);

                const cdp = await page.target().createCDPSession();
                await cdp.send('Page.enable');
                await cdp.send('Network.enable');

                await har.start();
                await page.tracing.start({ categories: TRACE_CATEGORIES });

                await page.goto(urlString, {
                    timeout: 120000,
                });

                await page.close();

                const harResult = await har.stop();
                const tracing = await page.tracing.stop();

                const { entries } = harResult.log;

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

                const data = JSON.parse(tracing.toString());
                const res = await wprofx.analyzeTrace(data.traceEvents);

                timings.push(res);
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
    // Create directory
    const dir = path.join(__dirname, 'har', `loss-${loss}_delay-${delay}_bw-${bw}`, domain, size);
    fs.mkdirSync(dir, { recursive: true });

    // Read from file if exists
    const file = path.join(dir, `chrome_${isH3 ? 'h3' : 'h2'}.json`);
    let timings = [];
    try {
        timings = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (error) {
        console.error(error);
    }

    const result = await runChromeTracing(urls[size], isH3);

    timings.push(...result);

    // Save data
    fs.writeFileSync(file, JSON.stringify(timings));
};

(async () => {
    const parser = new argparse.ArgumentParser();

    parser.add_argument('url');
    parser.add_argument('dir');
    parser.add_argument('single');

    const cliArgs = parser.parse_args();

    const { urlString, dir, single } = cliArgs;

    if (single) {
        // H2 - single object
        console.log('Chrome: H2 - single object');
        await runBenchmark(urlString, dir, false);

        // H3 - single object
        console.log('Chrome: H3 - single object');
        await runBenchmark(urlString, dir, true);
    } else {
        // H2 - multi object
        console.log('Chrome: H2 - multi object');
        await runBenchmarkWeb(urlString, dir, false);

        // H3 - multi object
        console.log('Chrome: H3 - multi object');
        await runBenchmarkWeb(urlString, dir, false);
    }
})();
