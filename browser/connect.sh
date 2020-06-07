#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-27 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--origin-to-force-quic-on=cloudflare-quic.com:443 \
https://cloudflare-quic.com/5MB.png