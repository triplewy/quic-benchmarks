#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-27 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--auto-open-devtools-for-tabs \
--ssl-key-log-file=/Users/alexyu/wireshark/sslkeylog.log \
--origin-to-force-quic-on=scontent.xx.fbcdn.net:443 \
https://scontent.xx.fbcdn.net/speedtest-10MB