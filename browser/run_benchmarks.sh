#!/bin/bash

LOSS=$1
BW=$2

# Chrome
node index.js $LOSS $BW

# # Firefox
# python3 main.py $LOSS $BW

# Curl
python3 client.py curl $LOSS $BW

# Ngtcp2
python3 client.py ngtcp2 $LOSS $BW

# Proxygen
docker rm hq
docker run \
--name hq \
-v /Users/alexyu/quic-benchmarks/browser/har:/har \
hq python3 client.py proxygen $LOSS $BW
