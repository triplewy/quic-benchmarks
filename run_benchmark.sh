#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

LOSS=$1
DELAY=$2
BW=$3

HARDIR="revised_loss-${LOSS}_delay-${DELAY}_bw-${BW}"

node $BASEDIR/chrome/chrome.js --no-single --dir $HARDIR