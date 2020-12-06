/* eslint-disable indent */
const http2 = require('http2');
const { PerformanceObserver } = require('perf_hooks');

const clientSession = http2.connect('https://scontent.xx.fbcdn.net');

const {
    HTTP2_HEADER_PATH,
    HTTP2_HEADER_STATUS,
} = http2.constants;

const obs = new PerformanceObserver((items) => {
    const entry = items.getEntries()[0];
    console.log(entry.entryType); // prints 'http2'
    if (entry.name === 'Http2Session') {
        // Entry contains statistics about the Http2Session
        console.log(entry);
    } else if (entry.name === 'Http2Stream') {
        // Entry contains statistics about the Http2Stream
        console.log(entry);
    }
});


const req1 = clientSession.request({ [HTTP2_HEADER_PATH]: '/speedtest-500KB' });
const req2 = clientSession.request({ [HTTP2_HEADER_PATH]: '/speedtest-1MB' });

const request = (req) => new Promise((resolve, reject) => {
    req.on('response', (headers) => {
        console.log(headers[HTTP2_HEADER_STATUS]);
        req.on('data', () => { });
        req.on('end', () => {
            console.log('req1: end');
            req.end();
            resolve();
        });
    });
});

const req1Prom = new Promise((resolve, reject) => {
    req1.on('response', (headers) => {
        console.log(headers[HTTP2_HEADER_STATUS]);
        req1.on('data', () => { });
        req1.on('end', () => {
            console.log('req1: end');
            req1.end();
            resolve();
        });
    });
});

const req2Prom = new Promise((resolve, reject) => {
    req2.on('response', (headers) => {
        console.log(headers[HTTP2_HEADER_STATUS]);
        req2.on('data', () => { });
        req2.on('end', () => {
            console.log('req2: end');
            req2.end();
            resolve();
        });
    });
});

(async () => {
    await Promise.all([req1Prom, req2Prom]);
    clientSession.close();
    obs.observe({ entryTypes: ['http2'] });
})();
