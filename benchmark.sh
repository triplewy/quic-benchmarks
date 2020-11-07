#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

usage() {
cat << EOF
Usage: benchmark.sh [url] -d [results_dir] -n [iterations] -s
    [url]            - The URL to benchmark
    -d [results_dir] - The directory path to store results
    -n [iterations]  - The amount of iterations to run
    -s               - Signifies url is a single-object web resource
EOF
}

URL=$1
DIRPATH=""
ITERATIONS=20
SINGLE=""

shift 1

while getopts ":sd:n:" o; do
    case "${o}" in
        d)
            RESULTS_DIR=${OPTARG}
        ;;
        n)
            ITERATIONS=${OPTARG}
        ;;
        s)
            SINGLE="--single"
        ;;
        *) usage
        ;;
    esac
done

if [[ -z $URL ]]; then
    usage
    exit 1
fi

if [[ -n $SINGLE ]]; then
    if [ -z "$DIRPATH" ]
    then
        python3 client.py $URL -n $ITERATIONS
    else
        mkdir -p $DIRPATH
        
        python3 client.py $URL --dir $DIRPATH -n $ITERATIONS
    fi
fi

# Gave up on calling the chrome container via python...
if [[ -z $SINGLE ]]; then
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
    yushuf/chrome:latest \
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
    yushuf/chrome:latest \
    node \
    /usr/src/app/chrome.js \
    $URL \
    $SINGLE \
    --h3 \
    --dir=/logs
    
    i=$(($i + 1))
done