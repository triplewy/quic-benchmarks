#!/bin/bash

URL=$1
DIRPATH=$2

if [ -z "$DIRPATH" ]
then
    if [[ $* == *--single* ]]
    then
        # Chrome
        node clients/chrome.js $URL --single
        
        # CLI Clients
        python3 clients/client.py $URL
    else
        # Chrome
        node clients/chrome.js $URL --no-single
    fi
else
    mkdir -p $DIRPATH
    
    if [[ $* == *--single* ]]
    then
        # Chrome
        node clients/chrome.js $URL --dir $DIRPATH --single
        
        # CLI Clients
        python3 clients/client.py $URL --dir $DIRPATH
    else
        # Chrome
        node clients/chrome.js $URL --dir $DIRPATH --no-single
    fi
fi






