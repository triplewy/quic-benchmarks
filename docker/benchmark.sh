#!/bin/bash

URL=$1
URL_HOST=$2
URL_PORT=$3
URL_PATH=$4

QLOG_DIR=$HOME/quic-benchmarks/qlog

if [[ $* == *--mvfst* ]]; then
    CMD="for _ in {1..10}; do \
    /proxygen/proxygen/_build/proxygen/httpserver/hq \
    --log_response=false \
    --mode=client \
    --stream_flow_control=1073741824 \
    --conn_flow_control=1073741824 \
    --use_draft=true \
    --protocol=h3-29 \
    --qlogger_path=/qlog \
    --host=$URL_HOST \
    --port=$URL_PORT \
    --path=$URL_PATH \
    --v=0; done"
    
    echo $CMD
    
    docker rm mvfst || \
    docker run \
    -v $QLOG_DIR/mvfst:/qlog \
    --entrypoint='/bin/bash' \
    --name=mvfst lnicco/mvfst-qns \
    -c "$CMD"
fi

if [[ $* == *--aioquic* ]]; then
    docker rm aioquic
    docker run \
    -v $QLOG_DIR/aioquic:/qlog \
    --env SIZE=$SIZE \
    --entrypoint '/bin/bash' \
    --name aioquic aiortc/aioquic-qns \
    -c 'for _ in {1..10}; do \
    python3 \
    /aioquic/examples/http3_client.py \
    --max-data=1073741824 \
    --max-stream-data=1073741824 \
    --quic-log=/qlog \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE; done'
fi

if [[ $* == *--ngtcp2* ]]; then
    docker rm ngtcp2
    docker run \
    -v $QLOG_DIR/ngtcp2:/qlog \
    --env SIZE=$SIZE \
    --entrypoint '/bin/bash' \
    --name ngtcp2 ngtcp2/ngtcp2-interop \
    -c 'for _ in {1..10}; do \
    client \
    --quiet \
    --exit-on-all-streams-close \
    --max-data=1073741824 \
    --max-stream-data-uni=1073741824 \
    --max-stream-data-bidi-local=1073741824 \
    --cc=cubic \
    --qlog-dir=/qlog \
    scontent.xx.fbcdn.net \
    443 \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE; done'
fi

if [[ $* == *--quiche* ]]; then
    docker rm quiche
    docker run \
    -v $QLOG_DIR/quiche:/qlog \
    --env SIZE=$SIZE \
    --env QLOGDIR=/qlog \
    --env RUST_LOG='info' \
    --entrypoint '/bin/bash' \
    --name quiche cloudflare/quiche-qns \
    -c 'for _ in {1..10}; do \
    /quiche/quiche-client \
    --max-data=1073741824 \
    --max-stream-data=1073741824 \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE \
    > /dev/null; done'
fi

# Doesn't work with facebook for some reason
if [[ $* == *--quant* ]]; then
    docker rm quant
    docker run \
    -v $QLOG_DIR/quant:/qlog \
    --env SIZE=$SIZE \
    --entrypoint '/bin/bash' \
    --name quant ntap/quant:interop \
    -c 'for _ in {1..10}; do \
    /usr/local/bin/client \
    -3 \
    -i eth0 \
    -t 150 \
    -x 50 \
    -v 5 \
    -e 0xff00001d \
    -q /qlog \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE; done'
fi

# Does not support qlog
if [[ $* == *--quicly* ]]; then
    docker rm quicly
    docker run \
    -v $QLOG_DIR/quicly:/qlog \
    --env SIZE=$SIZE \
    --env QLOGDIR=/qlog \
    --entrypoint '/bin/bash' \
    --name quicly janaiyengar/quicly:interop \
    -c 'for _ in {1..10}; do \
    /quicly/cli \
    -M 1073741824 \
    -m 1073741824 \
    -q /qlog \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE; done'
fi

if [[ $* == *--picoquic* ]]; then
    docker rm picoquic
    docker run \
    -v $QLOG_DIR/picoquic:/qlog \
    --env SIZE=$SIZE \
    --env QLOGDIR=/qlog \
    --entrypoint '/bin/bash' \
    --name picoquic privateoctopus/picoquic:latest \
    -c 'mkdir -p /logs && for _ in {1..10}; do \
    /picoquic/picoquicdemo \
    -b /logs/client_log.bin \
    scontent.xx.fbcdn.net \
    443 \
    /speedtest-$SIZE && \
    /picoquic/picolog_t \
    -f qlog \
    -o /qlog /logs/client_log.bin && \
    rm /logs/client_log.bin; done'
fi

# Don't know why this is so slow, especially when compared to firefox speed
if [[ $* == *--neqo* ]]; then
    docker rm neqo
    docker run \
    -v $QLOG_DIR/neqo:/qlog \
    --env SIZE=$SIZE \
    --env RUST_LOG='' \
    --entrypoint '/bin/bash' \
    --name neqo neqoquic/neqo-qns:latest \
    -c 'for _ in {1..10}; do \
    /neqo/target/neqo-client \
    --qlog-dir=/qlog \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE > /dev/null; done'
fi

# quic-go not supported because their interop docker image does not have their
# real client
if [[ $* == *--quic-go* ]]; then
    exit -1
fi
