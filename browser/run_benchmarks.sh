#!/bin/bash

LOSS=$1
DELAY=$2
BW=$3

# Chrome
node index.js $LOSS $DELAY $BW

# Firefox
python3 main.py $LOSS $DELAY $BW

# Curl
python3 client.py curl $LOSS $DELAY $BW

# Ngtcp2
python3 client.py ngtcp2 $LOSS $DELAY $BW

# Proxygen
python3 client.py proxygen $LOSS $DELAY $BW
