#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

PORT=30000
HTTPVERSION=0.9
HOST=127.0.0.1
URLPATH=/1048576
QLOGDIR=/tmp/qlog
CONN_FLOW_CONTROL=15728640
STREAM_FLOW_CONTROL=6291456

# Remove container
docker stop mvfst
docker rm mvfst

# Start docker container
docker run \
-d \
--name mvfst \
-v ${QLOGDIR}/server:/logs \
-v /certs:/certs \
--entrypoint /proxygen/_build/proxygen/bin/hq \
-p ${HOST}:${PORT}:${PORT}/udp \
-p ${HOST}:${PORT}:${PORT}/tcp \
lnicco/mvfst-qns:latest \
--mode=server \
--cert=/certs/leaf_cert.pem \
--key=/certs/leaf_cert.key \
--port=${PORT} \
--httpversion=${HTTPVERSION} \
--h2port=${PORT} \
--qlogger_path=/logs \
--host=0.0.0.0 \
--congestion=bbr \
--pacing=true \
--v=0

# Run clients

# Proxygen
/quic/proxygen/proxygen/_build/proxygen/httpserver/hq \
--log_response=false \
--mode=client \
--stream_flow_control=${STREAM_FLOW_CONTROL} \
--conn_flow_control=${CONN_FLOW_CONTROL} \
--use_draft=true \
--draft-version=29 \
--qlogger_path=${QLOGDIR}/client \
--host=${HOST} \
--port=${PORT} \
--path=${URLPATH} \
--v=0

# ngtpc2
/quic/ngtcp2/examples/client \
--quiet \
--exit-on-all-streams-close \
--max-data=${CONN_FLOW_CONTROL} \
--max-stream-data-uni=${STREAM_FLOW_CONTROL} \
--max-stream-data-bidi-local=${STREAM_FLOW_CONTROL} \
--group=X25519 \
--qlog-dir=${QLOGDIR}/client \
${HOST} \
${PORT} \
https://${HOST}:${PORT}${URLPATH}

# chrome h3
$BASEDIR/connect_h3.sh ${HOST} ${PORT} ${URLPATH}

# chrome h2
$BASEDIR/connect_h2.sh ${HOST} ${PORT} ${URLPATH}