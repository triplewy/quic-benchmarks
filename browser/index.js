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

const ITERATIONS = 10;
const RETRIES = 5;

function sleep(ms) {
    return new Promise((resolve) => {
        setTimeout(resolve, ms);
    });
}

const chromeArgs = (urlString, forceQuic) => {
    const args = [
        '--user-data-dir=/tmp/chrome-profile',
        '--disk-cache-dir=/dev/null',
        '--disk-cache-size=1',
        '--aggressive-cache-discard',
    ];

    if (forceQuic) {
        const urlObject = url.parse(urlString);
        args.push(
            '--enable-quic',
            '--quic-version=h3-29',
            `--origin-to-force-quic-on=${urlObject.host}:443`,
        );
    }

    return args;
};

const runChrome = async (browser, urlString, forceQuic, loss, delay, bw) => {
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
            return path.join('har', `loss-${loss}_delay-${delay}_bw-${bw}`, 'chrome', 'h3', urlObject.host);
        }
        return path.join('har', `loss-${loss}_delay-${delay}_bw-${bw}`, 'chrome', 'h2', urlObject.host);
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
        const idlePage = await browser.newPage();

        for (let j = 0; j < RETRIES; j += 1) {
            try {
                await har.start();
                const loadPage = page.goto(urlString, {
                    timeout: 120000,
                });
                await sleep(100);
                await idlePage.bringToFront();
                await loadPage;
                const harResult = await har.stop();
                const { entries } = harResult.log;

                const result = entries.filter((entry) => entry.request.url === urlString);

                if (result.length !== 1) {
                    console.error('Invalid HAR');
                    throw Error;
                }

                const entry = result[0];
                console.log(entry.response.httpVersion, entry.time);
                timings.total.push(entry.time);
                // const timing = entry.timings;
                // Object.entries(timing).forEach(([key, value]) => {
                //     timings[key].push(value);
                // });

                await page.close();
                await idlePage.close();

                break;
            } catch (error) {
                if (j === RETRIES - 1) {
                    console.error(error);
                    throw error;
                }
            }
        }
    }

    fs.writeFileSync(harPath, JSON.stringify(timings));
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

const instagramUrls = [
    'https://www.instagram.com',
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

const [, , loss, delay, bw] = process.argv;

(async () => {
    // Test H2 - Chrome
    console.log('Chrome: benchmarking H2');
    fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
    let args = chromeArgs('', false);
    let chromeBrowser = await puppeteer.launch({
        headless: false,
        executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        args,
        devtools: true,
    });
    // for (const urlString of microsoftUrls) {
    //     await queryFile(chromeBrowser, urlString, false);
    // }
    // for (const urlString of cloudfareUrls) {
    //     await runChrome(chromeBrowser, urlString, false);
    // }
    for (const urlString of fbUrls) {
        await runChrome(chromeBrowser, urlString, false, loss, delay, bw);
    }
    // for (const urlString of instagramUrls) {
    //     await runChrome(chromeBrowser, urlString, false, loss, delay, bw);
    // }

    await chromeBrowser.close();

    // Test H3 - Chrome
    console.log('Chrome: benchmarking H3');
    fs.rmdirSync('/tmp/chrome-profile', { recursive: true });
    args = chromeArgs(instagramUrls[0], true);
    chromeBrowser = await puppeteer.launch({
        headless: false,
        executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        args,
        devtools: true,
    });
    for (const urlString of fbUrls) {
        await runChrome(chromeBrowser, urlString, true, loss, delay, bw);
    }
    // for (const urlString of instagramUrls) {
    //     await runChrome(chromeBrowser, urlString, false, loss, delay, bw);
    // }
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
