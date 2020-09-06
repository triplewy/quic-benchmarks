#!/bin/bash

DIR=$1
HOST=$2
WEBPATH=$3

DATA_DIR="analysis/data/$DIR"

mkdir -p /tmp/logs
mkdir -p /tmp/qlog
mkdir -p /tmp/netlog
mkdir -p $DATA_DIR

ITERATIONS=(1 2 3)
for i in ${ITERATIONS[@]}
do
    echo $i
    
    # chrome
    ./clients/connect.sh $HOST $WEBPATH
    node netlog/index.js /tmp/netlog/chrome.json $DATA_DIR/chrome$i.qlog
    mv /tmp/netlog/chrome.json $DATA_DIR/chrome$i.json
    
    # proxygen
    $HOME/proxygen-clone/proxygen/_build/proxygen/httpserver/hq \
    --log_response=false \
    --mode=client \
    --stream_flow_control=1073741824 \
    --conn_flow_control=1073741824 \
    --use_draft=true \
    --draft-version=29 \
    --client_auth_mode='Required' \
    --qlogger_path=/tmp/qlog \
    --v=0 \
    --host=$HOST \
    --port=443 \
    --path=/$WEBPATH
    
    mv /tmp/qlog/.qlog $DATA_DIR/proxygen$i.qlog
    
    # ngtcp2
    $HOME/ngtcp2/examples/client \
    --quiet \
    --no-quic-dump \
    --exit-on-all-streams-close \
    --max-data=1073741824 \
    --max-stream-data-uni=1073741824 \
    --max-stream-data-bidi-local=1073741824 \
    --cc=cubic \
    --qlog-file=/tmp/qlog/.qlog \
    $HOST \
    443 \
    https://$HOST/$WEBPATH
    
    mv /tmp/qlog/.qlog $DATA_DIR/ngtcp2$i.qlog
    
    # quiche
    QLOGDIR=/tmp/qlog quiche-client \
    --max-data=1073741824 \
    --max-stream-data=1073741824 \
    https://$HOST/$WEBPATH > /dev/null
    
    find /tmp/qlog -name '*.qlog' -exec mv '{}' $DATA_DIR/quiche$i.qlog \;
    
    # # aioquic
    # python3 $HOME/aioquic/examples/http3_client.py \
    # -q /tmp/qlog \
    # --max-data=1073741824 \
    # --max-stream-data=1073741824 \
    # https://$HOST/$WEBPATH > /dev/null
    
    # find /tmp/qlog -name '*.qlog' -exec mv '{}' $DATA_DIR/aioquic$i.qlog \;
done

python3 analysis/ack-analysis.py --qlogdir $DATA_DIR