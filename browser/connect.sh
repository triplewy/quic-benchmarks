#!/usr/bin/env bash

/Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary \
--user-data-dir=/tmp/chrome-profile \
--enable-quic \
--quic-version=h3-27 \
--disk-cache-dir=/dev/null \
--disk-cache-size=1 \
--aggressive-cache-discard \
--origin-to-force-quic-on=f5quic.com:4433 \
https://f5quic.com:4433/50000