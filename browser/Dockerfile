FROM ubuntu:bionic

RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository ppa:mhier/libboost-latest

# Get and build proxygen with HTTP/3 support
RUN apt-get install --yes libboost1.67-dev python3 

# Copy HQ
COPY hq .

# Copy shared libs
COPY libs.tar .
RUN tar xvf libs.tar
RUN rm libs.tar

COPY client.py .

RUN mkdir /tmp/logs