#!/bin/bash

DELAY=$1

CHROME_DEVEL_SANDBOX=/usr/local/sbin/chrome-devel-sandbox
HOST=127.0.0.1
PORT=30000
SIZE=1048576

mkdir -p /tmp/proxygen/logs

sudo docker stop mvfst
sudo docker rm mvfst

sudo docker run \
-d \
-v /tmp/proxygen/logs:/logs \
-p ${HOST}:${PORT}:${PORT}/udp \
--name=mvfst \
--entrypoint=/proxygen/proxygen/_build/proxygen/httpserver/hq \
lnicco/mvfst-qns \
--mode=server \
--host=0.0.0.0 \
--port=${PORT} \
--h2port=6667 \
--logdir=/logs \
--qlogger_path=/logs \
--congestion=bbr \
--pacing=true \
--v=0

sleep 2

# setup network conditions
# sudo tcdel lo --all
sudo tcset lo --delay ${DELAY}ms --direction outgoing --overwrite

sleep 2

# proxygen
multitime -n 5 \
/quic/proxygen/proxygen/_build/proxygen/httpserver/hq \
--mode=client \
--log-response=false \
--use_draft=true \
--draft-version=29 \
--stream_flow_control=1073741824 \
--conn_flow_control=1073741824 \
--host=${HOST} \
--port=${PORT} \
--path=/${SIZE}

# ngtcp2
multitime -n 5 \
/quic/ngtcp2/examples/client \
--quiet \
--exit-on-all-streams-close \
--max-data=1073741824 \
--max-stream-data-uni=1073741824 \
--max-stream-data-bidi-local=1073741824 \
${HOST} \
${PORT} \
https://${HOST}:${PORT}/${SIZE}

# chrome
# node /quic/quic-benchmarks/clients/multitime-chrome.js -n 5 https://${HOST}:${PORT}/${SIZE}