#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-29 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--auto-open-devtools-for-tabs \
--ssl-key-log-file=/Users/alexyu/wireshark/chrome_sslkeylog \
--origin-to-force-quic-on=www.instagram.com:443 \
https://www.instagram.com