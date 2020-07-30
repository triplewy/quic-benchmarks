#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-29 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--auto-open-devtools-for-tabs \
--origin-to-force-quic-on=scontent.xx.fbcdn.net:443 \
--log-net-log=/tmp/netlog/speedtest-0B.netlog \
https://scontent.xx.fbcdn.net/speedtest-0B