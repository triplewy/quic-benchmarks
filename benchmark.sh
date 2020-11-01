#!/bin/bash

URL=$1
DIRPATH=$2

mkdir -p $DIRPATH

if [[ $* == *--single* ]]
then
    # Chrome
    node clients/chrome.js $URL --dir $DIRPATH --single
    
    # CLI Clients
    python3 clients/client.py $URL $DIRPATH
else
    # Chrome
    node clients/chrome.js $URL $DIRPATH false
fi





