#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

DIRNAME=$1

node $BASEDIR/chrome/chrome.js --single --dir $DIRNAME
python3 $BASEDIR/client.py --dir $DIRNAME
# HOME=/quic node $BASEDIR/chrome/chrome.js --no-single --dir $DIRNAME