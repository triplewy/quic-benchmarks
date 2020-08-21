#!/bin/bash

LOSS=$1
DELAY=$2
BW=$3

# Chrome
node chrome.js $LOSS $DELAY $BW

# Firefox
python3 main.py $LOSS $DELAY $BW

# Curl
python3 client.py curl_h2 $LOSS $DELAY $BW

# Ngtcp2
python3 client.py ngtcp2_h3 $LOSS $DELAY $BW

# Proxygen
python3 client.py proxygen_h3 $LOSS $DELAY $BW
