#!/bin/bash

URL=$1
DIRPATH=$2
ITERATIONS=10

if [ -z "$DIRPATH" ]
then
    if [[ $* == *--single* ]]
    then
        python3 client.py $URL --single -n $ITERATIONS
    else
        python3 client.py $URL -n $ITERATIONS
    fi
else
    mkdir -p $DIRPATH
    
    if [[ $* == *--single* ]]
    then
        python3 client.py $URL --dir $DIRPATH --single -n $ITERATIONS
    else
        python3 client.py $URL --dir $DIRPATH -n $ITERATIONS
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

for _ in {0..$ITERATIONS}
do
    #h2
    docker run \
    --rm \
    -v /tmp/results:/logs \
    --security-opt seccomp=seccomp.json \
    --entrypoint "" \
    chrome \
    node \
    /usr/src/app/chrome.js \
    $URL \
    $SINGLE \
    --no-h3 \
    --dir=/logs
    
    #h3
    docker run \
    --rm \
    -v /tmp/results:/logs \
    --security-opt seccomp=seccomp.json \
    --entrypoint "" \
    chrome \
    node \
    /usr/src/app/chrome.js \
    $URL \
    $SINGLE \
    h3 \
    --dir=/logs
    
done