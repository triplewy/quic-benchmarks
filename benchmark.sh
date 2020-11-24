#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

usage() {
cat << EOF
Usage: benchmark.sh [url] -d [results_dir] -n [iterations] -s -l
    [url]            - The URL to benchmark
    -d [results_dir] - The directory path to store results
    -n [iterations]  - The amount of iterations to run
    -s               - Signifies url is a single-object web resource
    -l               - Signifies if using local binaries/chrome
EOF
}

URL=$1
DIRPATH=""
ITERATIONS=20
SINGLE=""
LOCAL=""

shift 1

while getopts ":sld:n:" o; do
    case "${o}" in
        d)
            DIRPATH=${OPTARG}
        ;;
        n)
            re='^[0-9]+$'
            if ! [[ ${OPTARG} =~ $re ]] ; then
                echo "error: Not a number" >&2; exit 1
            fi
            ITERATIONS=${OPTARG}
        ;;
        s)
            SINGLE="--single"
        ;;
        l)
            LOCAL="--local"
        ;;
        *) usage
        ;;
    esac
done

echo "url: $URL"
echo "results_dir: $DIRPATH"
echo "iterations: $ITERATIONS"
echo "single: $SINGLE"
echo "local: $LOCAL"

if [[ -z $URL ]]; then
    usage
    exit 1
fi

ARGS="-n $ITERATIONS"

if [[ -n "$DIRPATH" ]]; then
    mkdir -p $DIRPATH
    ARGS+=" --dir $DIRPATH"
fi

if [[ -n $LOCAL ]]; then
    ARGS+=" $LOCAL"
fi

if [[ -n $SINGLE ]]; then
    python3 client.py $URL $ARGS
fi

# Gave up on calling the chrome container via python...
if [[ -z $SINGLE ]]; then
    SINGLE="--no-single"
fi

i=1
while [ "$i" -le "$ITERATIONS" ]
do
    if [[ -n $LOCAL ]]
    then
        # h2
        node \
        $BASEDIR/chrome/chrome.js \
        $URL \
        $SINGLE \
        --no-h3 \
        --dir=$DIRPATH
        
        # h3
        node \
        $BASEDIR/chrome/chrome.js \
        $URL \
        $SINGLE \
        --h3 \
        --dir=$DIRPATH
    else
        # h2
        docker run \
        --rm \
        -v $DIRPATH:/logs \
        --security-opt seccomp="$BASEDIR"/seccomp.json \
        --entrypoint "" \
        yushuf/chrome:latest \
        node \
        /usr/src/app/chrome.js \
        $URL \
        $SINGLE \
        --no-h3 \
        --dir=/logs
        
        # h3
        docker run \
        --rm \
        -v $DIRPATH:/logs \
        --security-opt seccomp="$BASEDIR"/seccomp.json \
        --entrypoint "" \
        yushuf/chrome:latest \
        node \
        /usr/src/app/chrome.js \
        $URL \
        $SINGLE \
        --h3 \
        --dir=/logs
    fi
    
    i=$(($i + 1))
done