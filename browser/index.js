/* eslint-disable no-loop-func */
/* eslint-disable no-prototype-builtins */
/* eslint-disable indent */
/* eslint-disable no-restricted-syntax */
/* eslint-disable no-await-in-loop */
const puppeteer = require('puppeteer-core');
const PuppeteerHar = require('puppeteer-har');
const webdriver = require('selenium-webdriver');
const firefox = require('selenium-webdriver/firefox');

const path = require('path');
const fs = require('fs');
const url = require('url');

const ITERATIONS = 10;

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

const firefoxOptions = (forceQuic) => {
    const options = new firefox.Options()
        .addArguments('--devtools')
        .setBinary('/Applications/Firefox Nightly.app/Contents/MacOS/firefox')
        .setProfile('/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly')
        .addExtensions('/Users/alexyu/Library/Application Support/Firefox/Profiles/3w5xom8x.default-nightly/extensions/harexporttrigger@getfirebug.com.xpi');

    return options;
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
        const har = new PuppeteerHar(page);

        await har.start();
        try {
            await page.goto(urlString, {
                timeout: 120000,
            });
        } catch (error) {
            console.error(error);
        }

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

const runFirefox = async (driver, urlString, forceQuic) => {
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
        await driver.get(urlString);
        await driver.executeScript(async () => {
            console.log('here');
            const har = await HAR.exportTrigger();
            console.log(har);
        });
    }
};

(async () => {
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

    // // Test H2 - Chrome
    // let args = chromeArgs('', false);
    // let chromeBrowser = await puppeteer.launch({
    //     headless: false,
    //     executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    //     args,
    // });
    // console.log('Chrome: benchmarking H2');
    // for (const urlString of fbUrls) {
    //     await runChrome(chromeBrowser, urlString, false);
    // }
    // for (const urlString of cloudfareUrls) {
    //     await runChrome(chromeBrowser, urlString, false);
    // }
    // await chromeBrowser.close();

    // // Test H3 - Chrome
    // console.log('Chrome: benchmarking H3');
    // args = chromeArgs(fbUrls[0], true);
    // chromeBrowser = await puppeteer.launch({
    //     headless: false,
    //     executablePath: '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
    //     args,
    // });
    // for (const urlString of fbUrls) {
    //     await runChrome(chromeBrowser, urlString, true);
    // }
    // await chromeBrowser.close();
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

    // Test H2 - Firefox
    console.log('Firefox: benchmarking H2');
    let options = firefoxOptions(false);

    let firefoxBrowser = await new webdriver.Builder()
        .forBrowser('firefox')
        .setFirefoxOptions(options)
        .build();

    for (const urlString of fbUrls) {
        await runFirefox(firefoxBrowser, urlString, false);
    }
    await firefoxBrowser.quit();

    // Test H3 - Firefox
    console.log('Firefox: benchmarking H3');
    options = firefoxOptions(true);
    profile = cap.get('moz:profile');

    firefoxBrowser = await new webdriver.Builder().forBrowser('firefox')
        .setFirefoxOptions(options).build();
    cap = await firefoxBrowser.getCapabilities();
    for (const urlString of fbUrls) {
        await runFirefox(firefoxBrowser, urlString, false);
    }
    await firefoxBrowser.close();
})();
