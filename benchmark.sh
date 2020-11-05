#!/bin/bash

URL=$1
DIRPATH=$2

if [ -z "$DIRPATH" ]
then
    if [[ $* == *--single* ]]
    then
        python3 client.py $URL --single
    else
        python3 client.py $URL
    fi
else
    mkdir -p $DIRPATH
    chmod 0777 $DIRPATH
    
    if [[ $* == *--single* ]]
    then
        python3 client.py $URL --dir $DIRPATH --single
    else
        python3 client.py $URL --dir $DIRPATH
    fi
fi