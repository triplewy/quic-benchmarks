#!/usr/bin/env bash

CHROME_PATH=/quic/quic-benchmarks/chrome/node_modules/puppeteer/.local-chromium/linux-809590/chrome-linux/chrome
HOST=$1
PORT=$2
WEBPATH=$3

rm -rf /tmp/chrome-profile
mkdir -p /tmp/netlog

${CHROME_PATH} \
--user-data-dir=/tmp/chrome-profile \
--disable-quic \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--headless \
--log-net-log=/tmp/netlog/chrome_h2.json \
https://$HOST:$PORT$WEBPATH


