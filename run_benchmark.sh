#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

DIRNAME=$1

python3 $BASEDIR/client.py --log --dir $DIRNAME
node $BASEDIR/chrome/chrome.js --log --single --dir $DIRNAME
# HOME=/quic node $BASEDIR/chrome/chrome.js --no-single --dir $DIRNAME