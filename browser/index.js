/* eslint-disable no-loop-func */
/* eslint-disable no-prototype-builtins */
/* eslint-disable indent */
/* eslint-disable no-restricted-syntax */
/* eslint-disable no-await-in-loop */
const puppeteer = require('puppeteer-core');
const PuppeteerHar = require('puppeteer-har');

const path = require('path');
const fs = require('fs');
const url = require('url');

const ITERATIONS = 1;

function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

const chromeArgs = (urlString, forceQuic) => {
    const args = [
        '--user-data-dir=/tmp/chrome-profile',
        '--enable-quic',
        '--quic-version=h3-27',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
        '--auto-open-devtools-for-tabs',
    ];

    if (forceQuic) {
        const urlObject = url.parse(urlString);
        args.push(
            `--origin-to-force-quic-on=${urlObject.host}`,
        );
    }

    return args;
};

const queryFile = async (browser, urlString, forceQuic, loss) => {
    const timings = {
        total: [],
    };
    const urlObject = url.parse(urlString);
    const page = await browser.newPage();
    try {
        await page.goto(urlString);
    } catch (error) {
        console.error(error);
    }

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);
        const start = Date.now();
        const result = await page.evaluate(async (url) => {
            const res = await fetch(url);
            const text = await res.text();
            return text;
        }, urlString);
        const elapsed = Date.now() - start;
        console.log(`result.length: ${result.length}`);
        timings.total.push(elapsed);
    }

    await page.close();

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

const runChrome = async (browser, urlString, forceQuic, loss) => {
    let timings = {
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

    const urlObject = url.parse(urlString);
    const harDir = (() => {
        if (forceQuic) {
            return path.join('har', `loss_${loss}`, 'chrome', 'h3', urlObject.host);
        }
        return path.join('har', `loss_${loss}`, 'chrome', 'h2', urlObject.host);
    })();
    const harPath = path.join(harDir, `${urlObject.path.slice(1)}.json`);
    fs.mkdirSync(harDir, { recursive: true });

    try {
        const jsonString = fs.readFileSync(harPath, 'utf8');
        timings = JSON.parse(jsonString);
    } catch (error) {
        console.error(error);
    }

    // Repeat test ITERATIONS times
    for (let i = 0; i < ITERATIONS; i += 1) {
        console.log(`${urlString} Iteration: ${i}`);

        const page = await browser.newPage();
        const har = await new PuppeteerHar(page);

        await har.start();
        const loadPage = page.goto(urlString, {
            timeout: 120000,
        });
        const idlePage = await browser.newPage();
        await sleep(100);
        await idlePage.bringToFront();
        await loadPage;

        const harResult = await har.stop();
        const { entries } = harResult.log;

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
        await idlePage.close();
    }

    fs.writeFileSync(harPath, JSON.stringify(timings));
};

const fbUrls = [
    'https://scontent.xx.fbcdn.net/speedtest-0B',
    // 'https://scontent.xx.fbcdn.net/speedtest-1KB',
    // 'https://scontent.xx.fbcdn.net/speedtest-10KB',
    // 'https://scontent.xx.fbcdn.net/speedtest-100KB',
    // 'https://scontent.xx.fbcdn.net/speedtest-500KB',
    // 'https://scontent.xx.fbcdn.net/speedtest-1MB',
    // 'https://scontent.xx.fbcdn.net/speedtest-2MB',
    // 'https://scontent.xx.fbcdn.net/speedtest-5MB',
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

const f5Urls = [
    'https://f5quic.com:4433/50000',
    'https://f5quic.com:4433/5000000',
    'https://f5quic.com:4433/10000000',
];

const [, , loss] = process.argv;

(async () => {
    // // Test H2 - Chrome
    // let args = chromeArgs('', false);
    // let chromeBrowser = await puppeteer.launch({
    //     headless: false,
    //     executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    //     args,
    //     devtools: true,
    // });
    // console.log('Chrome: benchmarking H2');
    // // for (const urlString of microsoftUrls) {
    // //     await queryFile(chromeBrowser, urlString, false);
    // // }
    // // for (const urlString of cloudfareUrls) {
    // //     await runChrome(chromeBrowser, urlString, false);
    // // }
    // for (const urlString of fbUrls) {
    //     await runChrome(chromeBrowser, urlString, false, loss);
    // }
    // await chromeBrowser.close();

    // Test H3 - Chrome
    console.log('Chrome: benchmarking H3');
    args = chromeArgs(fbUrls[0], true);
    chromeBrowser = await puppeteer.launch({
        headless: false,
        executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        args,
    });
    for (const urlString of fbUrls) {
        await runChrome(chromeBrowser, urlString, true, loss);
    }
    await chromeBrowser.close();

    // // H3 - Cloudflare
    // args = chromeArgs(cloudfareUrls[0], true);
    // chromeBrowser = await puppeteer.launch({
    //     headless: false,
    //     executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    //     args,
    // });
    // for (const urlString of cloudfareUrls) {
    //     await runChrome(chromeBrowser, urlString, true);
    // }
    // await chromeBrowser.close();

    // // H3 - Microsoft
    // args = chromeArgs(microsoftUrls[0], true);
    // chromeBrowser = await puppeteer.launch({
    //     headless: false,
    //     executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    //     args,
    // });
    // for (const urlString of microsoftUrls) {
    //     await queryFile(chromeBrowser, urlString, true);
    // }
    // await chromeBrowser.close();

    // // H3 - F5
    // args = chromeArgs(f5Urls[0], true);
    // chromeBrowser = await puppeteer.launch({
    //     headless: false,
    //     executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    //     args,
    // });
    // for (const urlString of f5Urls) {
    //     await queryFile(chromeBrowser, urlString, true);
    // }
    // await chromeBrowser.close();
})();
