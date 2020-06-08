/* eslint-disable no-loop-func */
/* eslint-disable no-prototype-builtins */
/* eslint-disable indent */
/* eslint-disable no-restricted-syntax */
/* eslint-disable no-await-in-loop */
const puppeteer = require('puppeteer-core');
const PuppeteerHar = require('puppeteer-har');
const webdriver = require('selenium-webdriver');
const firefox = require('selenium-webdriver/firefox');
const { harFromMessages } = require('chrome-har');


const path = require('path');
const fs = require('fs');
const url = require('url');

const ITERATIONS = 10;

// event types to observe
const observe = [
    'Page.loadEventFired',
    'Page.domContentEventFired',
    'Page.frameStartedLoading',
    'Page.frameAttached',
    'Network.requestWillBeSent',
    'Network.requestServedFromCache',
    'Network.dataReceived',
    'Network.responseReceived',
    'Network.resourceChangedPriority',
    'Network.loadingFinished',
    'Network.loadingFailed',
];

const chromeArgs = (urlString, forceQuic) => {
    const args = [
        '--user-data-dir=/tmp/chrome-profile',
        '--enable-quic',
        '--quic-version=h3-27',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
    ];

    if (forceQuic) {
        const urlObject = url.parse(urlString);
        args.push(
            `--origin-to-force-quic-on=${urlObject.host}:443`,
        );
    }

    return args;
};

const runChrome = async (browser, urlString, forceQuic) => {
    const timings = {
        total: [],
        blocked: [],
        dns: [],
        connect: [],
        send: [],
        wait: [],
        receive: [],
        ssl: [],
        _queued: [],
    };

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);

        const page = await browser.newPage();

        // list of events for converting to HAR
        const events = [];

        // register events listeners
        const client = await page.target().createCDPSession();
        await client.send('Page.enable');
        await client.send('Network.enable');
        observe.forEach((method) => {
            client.on(method, (params) => {
                events.push({ method, params });
            });
        });

        try {
            await page.goto(urlString, {
                timeout: 120000,
            });
        } catch (error) {
            console.error(error);
        }

        // convert events to HAR file
        const har = harFromMessages(events);
        const { entries } = har.log;

        const result = entries.filter((entry) => entry.request.url === urlString);

        if (result.length !== 1) {
            throw Error;
        }

        const entry = result[0];
        timings.total.push(entry.time);
        const timing = entry.timings;
        Object.entries(timing).forEach(([key, value]) => {
            timings[key].push(value);
        });

        await page.close();
    }

    const urlObject = url.parse(urlString);
    const harDir = (() => {
        if (forceQuic) {
            return path.join('har', 'chrome', 'h3', urlObject.host);
        }
        return path.join('har', 'chrome', 'h2', urlObject.host);
    })();

    fs.mkdirSync(harDir, { recursive: true });
    fs.writeFileSync(
        path.join(harDir, `${urlObject.path.slice(1)}.json`),
        JSON.stringify(timings),
    );
};

const fbUrls = [
    'https://scontent.xx.fbcdn.net/speedtest-0B',
    'https://scontent.xx.fbcdn.net/speedtest-1KB',
    'https://scontent.xx.fbcdn.net/speedtest-10KB',
    'https://scontent.xx.fbcdn.net/speedtest-100KB',
    'https://scontent.xx.fbcdn.net/speedtest-500KB',
    'https://scontent.xx.fbcdn.net/speedtest-1MB',
    'https://scontent.xx.fbcdn.net/speedtest-2MB',
    'https://scontent.xx.fbcdn.net/speedtest-5MB',
    'https://scontent.xx.fbcdn.net/speedtest-10MB',
];

const cloudfareUrls = [
    'https://cloudflare-quic.com/1MB.png',
    'https://cloudflare-quic.com/5MB.png',
];

const microsoftUrls = [
    'https://quic.westus.cloudapp.azure.com/1MBfile.txt',
    'https://quic.westus.cloudapp.azure.com/5000000.txt',
    'https://quic.westus.cloudapp.azure.com/10000000.txt',
];

(async () => {
    // Test H2 - Chrome
    let args = chromeArgs('', false);
    let chromeBrowser = await puppeteer.launch({
        headless: false,
        executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        args,
    });
    console.log('Chrome: benchmarking H2');
    for (const urlString of microsoftUrls) {
        await runChrome(chromeBrowser, urlString, false);
    }
    // for (const urlString of fbUrls) {
    //     await runChrome(chromeBrowser, urlString, false);
    // }
    // for (const urlString of cloudfareUrls) {
    //     await runChrome(chromeBrowser, urlString, false);
    // }
    await chromeBrowser.close();

    // Test H3 - Chrome
    console.log('Chrome: benchmarking H3');
    args = chromeArgs(fbUrls[0], true);
    chromeBrowser = await puppeteer.launch({
        headless: false,
        executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        args,
    });
    for (const urlString of fbUrls) {
        await runChrome(chromeBrowser, urlString, true);
    }
    await chromeBrowser.close();
    args = chromeArgs(cloudfareUrls[0], true);
    chromeBrowser = await puppeteer.launch({
        headless: false,
        executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        args,
    });
    for (const urlString of cloudfareUrls) {
        await runChrome(chromeBrowser, urlString, true);
    }
    await chromeBrowser.close();
})();
