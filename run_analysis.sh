#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

LOSS=$1
DELAY=$2
BW=$3
DOMAIN=$4
SIZE=$5

ANALYSIS_DIR="loss-${LOSS}_delay-${DELAY}_bw-${BW}"

node $BASEDIR/chrome/chrome.js --analysis --dir $ANALYSIS_DIR --domain $DOMAIN --size $SIZE
