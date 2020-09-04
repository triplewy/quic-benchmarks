#!/usr/bin/env bash

HOST=$1
WEBPATH=$2

rm -rf /tmp/chrome-profile

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-29 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--headless \
--log-net-log=/tmp/netlog/chrome.json \
--origin-to-force-quic-on=$HOST:443 \
https://$HOST/$WEBPATH