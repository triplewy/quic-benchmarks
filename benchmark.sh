#!/bin/bash

SIZE=$1
RTT=$2
LOSS=$3

unset QLOGDIR
QLOG_DIR=$HOME/quic-benchmarks/qlog/"$SIZE"-"$RTT"ms-"$LOSS"loss
trash $QLOG_DIR

# Build all implementations if --build flag is set
if [[ $* == *--build* ]]; then
    build_ngtcp2
    cd $HOME/quiche && git checkout -- . && git pull && \
    cargo build --manifest-path=tools/apps/Cargo.toml --release
    cd $HOME/aioquic && git checkout -- . && git pull origin main
    cd $HOME/proxygen && git checkout -- . && git pull && \
    cd $HOME/proxygen/proxygen && ./build.sh -t -q
fi

# Benchmark all implementations if --bench flag is set
if [[ $* == *--bench* ]]; then
    # ngtcp2
    echo "Benchmarking ngtcp2..."
    mkdir -p $QLOG_DIR/ngtcp2
    multitime -n 10 $HOME/ngtcp2/examples/client --quiet --no-quic-dump \
    --no-http-dump --exit-on-all-streams-close --max-data=1073741824 \
    --max-stream-data-uni=1073741824 --max-stream-data-bidi-local=1073741824 \
    --max-streams-bidi=10 --max-stream-data-bidi-remote=1073741824 \
    --cc=cubic --qlog-dir=$QLOG_DIR/ngtcp2 \
    scontent.xx.fbcdn.net 443 https://scontent.xx.fbcdn.net/speedtest-$SIZE
    
    # quiche
    echo "Benchmarking quiche..."
    mkdir -p $QLOG_DIR/quiche
    export QLOGDIR=$QLOG_DIR/quiche && multitime -n 10 $HOME/quiche/tools/apps/target/release/quiche-client \
    --max-data=1073741824 --max-stream-data=1073741824 \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE > /dev/null
    
    # aioquic
    echo "Benchmarking aioquic..."
    mkdir -p $QLOG_DIR/aioquic
    multitime -n 10 python3 $HOME/aioquic/examples/http3_client.py \
    --max-data=1073741824 --max-stream-data=1073741824 \
    --quic-log=$QLOG_DIR/aioquic \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE
    
    # proxygen
    echo "Benchmarking proxygen..."
    mkdir -p $QLOG_DIR/proxygen
    multitime -n 10 $HOME/proxygen/proxygen/_build/proxygen/httpserver/hq --log_response=false \
    --mode=client --stream_flow_control=1073741824 --conn_flow_control=1073741824 \
    --use_draft=true --protocol=h3-29 --qlogger_path=$QLOG_DIR/proxygen \
    --host=scontent.xx.fbcdn.net --port=443 --path=/speedtest-$SIZE --v=0
fi

if [[ $* == *--qlog* ]]; then
    # ngtcp2 qlog
    $HOME/ngtcp2/examples/client --quiet --no-quic-dump \
    --no-http-dump --exit-on-all-streams-close --max-data=1073741824 \
    --max-stream-data-uni=1073741824 --cc=cubic scontent.xx.fbcdn.net \
    443 https://scontent.xx.fbcdn.net/speedtest-$SIZE --qlog-dir=$QLOG_DIR/ngtcp2
    
    # quiche qlog
    mkdir -p $QLOG_DIR/quiche
    export QLOGDIR=$QLOG_DIR/quiche && $HOME/quiche/tools/apps/target/release/quiche-client \
    --max-data=1073741824 --max-stream-data=1073741824 \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE > /dev/null
    
    # Proxygen qlog
    mkdir -p $QLOG_DIR/proxygen
    $HOME/proxygen/proxygen/_build/proxygen/httpserver/hq --log_response=false \
    --mode=client --stream_flow_control=1073741824 --conn_flow_control=1073741824 \
    --use_draft=true --protocol=h3-29 --host=scontent.xx.fbcdn.net --port=443 \
    --path=/speedtest-$SIZE --v=0 --qlogger_path=$QLOG_DIR/proxygen
    mv $QLOG_DIR/proxygen/.qlog $QLOG_DIR/proxygen/hq.qlog
    
    # aioquic qlog
    mkdir -p $QLOG_DIR/aioquic
    python3 $HOME/aioquic/examples/http3_client.py \
    --max-data=1073741824 --max-stream-data=1073741824 --quic-log=$QLOG_DIR/aioquic \
    https://scontent.xx.fbcdn.net/speedtest-$SIZE
    
    # Anaylze results
    python3 $HOME/quic-benchmarks/qlog-analyzer/main.py $QLOG_DIR $SIZE $RTT $LOSS
fi