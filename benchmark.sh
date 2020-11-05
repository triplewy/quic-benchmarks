#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

URL=$1
DIRPATH=$2
ITERATIONS=10

if [ -z "$DIRPATH" ]
then
    if [[ $* == *--single* ]]
    then
        python3 client.py $URL --single -n $ITERATIONS
    fi
else
    mkdir -p $DIRPATH
    
    if [[ $* == *--single* ]]
    then
        python3 client.py $URL --dir $DIRPATH --single -n $ITERATIONS
    fi
fi

# Gave up on calling the chrome container via python...
SINGLE="--single"
if [[ $* == *--single* ]]
then
    SINGLE="--single"
else
    SINGLE="--no-single"
fi

i=1
while [ "$i" -le "$ITERATIONS" ]
do
    #h2
    docker run \
    --rm \
    -v /tmp/results:/logs \
    --security-opt seccomp="$BASEDIR"/seccomp.json \
    --entrypoint "" \
    chrome \
    node \
    /usr/src/app/chrome.js \
    $URL \
    $SINGLE \
    --no-h3 \
    --dir=/logs
    
    i=$(($i + 1))
done

i=1
while [ "$i" -le "$ITERATIONS" ]
do
    #h3
    docker run \
    --rm \
    -v /tmp/results:/logs \
    --security-opt seccomp="$BASEDIR"/seccomp.json \
    --entrypoint "" \
    chrome \
    node \
    /usr/src/app/chrome.js \
    $URL \
    $SINGLE \
    --h3 \
    --dir=/logs
    
    i=$(($i + 1))
done