#!/bin/bash

LOSS=$1

# # Chrome
# node index.js $LOSS

# Firefox
python3 main.py $LOSS

# # Curl
# python3 client.py curl $LOSS

# # HQ
# docker rm hq
# docker run \
# --name hq \
# -v /Users/alexyu/quic-benchmarks/browser/har:/har \
# hq python3 client.py hq $LOSS