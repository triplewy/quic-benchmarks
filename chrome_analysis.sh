#!/bin/bash

ITERATIONS=(1 2 3 4 5)
for i in ${ITERATIONS[@]}
do
    echo $i
    ./clients/connect.sh
    node netlog/index.js /tmp/netlog/chrome.json analysis/data/facebook_delay-100_v2/chrome$i.qlog
done