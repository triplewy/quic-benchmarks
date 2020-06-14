#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-28 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--auto-open-devtools-for-tabs \
--ssl-key-log-file=/Users/alexyu/wireshark/chrome_sslkeylog \
--origin-to-force-quic-on=127.0.0.1:4433 \
https://127.0.0.1:4433/10000kb/index-1.html