#!/bin/bash

URL=$1
DIRPATH=$2

if [[ $* == *--single* ]]
then
    # Chrome
    node clients/chrome.js $URL $DIRPATH true
    
    # CLI Clients
    python3 clients/client.py $URL $DIRPATH
else
    # Chrome
    node clients/chrome.js $URL $DIRPATH false
fi





