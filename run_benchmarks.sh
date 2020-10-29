#!/bin/bash

mkdir -p /tmp/qlog

for i in {1..20}
do
    sudo docker run \
    -v /tmp/qlog:/logs \
    --rm \
    --name=mvfst \
    --entrypoint=/proxygen/proxygen/_build/proxygen/httpserver/hq \
    lnicco/mvfst-qns \
    --log_response=false \
    --mode=client \
    --stream_flow_control=1073741824 \
    --conn_flow_control=1073741824 \
    --host=scontent.xx.fbcdn.net \
    --port=443 \
    --path=/speedtest-1MB \
    --qlogger_path=/logs \
    --use_draft=true \
    --protocol=h3-29
done
