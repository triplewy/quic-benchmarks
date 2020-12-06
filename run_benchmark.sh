#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

LOSS=$1
DELAY=$2
BW=$3

DIRNAME="loss-${LOSS}_delay-${DELAY}_bw-${BW}"

python3 client.py --dir $DIRNAME
HOME=/quic node $BASEDIR/chrome/chrome.js --single --dir $DIRNAME
HOME=/quic node $BASEDIR/chrome/chrome.js --no-single --dir $DIRNAME