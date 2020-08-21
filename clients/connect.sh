#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-29 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--auto-open-devtools-for-tabs \
--origin-to-force-quic-on=www.instagram.com:443 \
--origin-to-force-quic-on=connect.facebook.net:443 \
--origin-to-force-quic-on=www.facebook.com:443 \
--origin-to-force-quic-on=graph.instagram.com:443 \
--log-net-log=/tmp/netlog/demo.netlog \
https://www.instagram.com