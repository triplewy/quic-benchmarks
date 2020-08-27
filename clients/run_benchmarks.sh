#!/bin/bash

LOSS=$1
DELAY=$2
BW=$3

# Remember to randomize the order!

# 2. Curl
python3 client.py curl_h2 $LOSS $DELAY $BW

# 3. Ngtcp2
python3 client.py ngtcp2_h3 $LOSS $DELAY $BW

# 4. Proxygen
python3 client.py proxygen_h3 $LOSS $DELAY $BW

# 1. Chrome
node chrome.js $LOSS $DELAY $BW


# # 5. Firefox
# node firefox.js $LOSS $DELAY $BW
