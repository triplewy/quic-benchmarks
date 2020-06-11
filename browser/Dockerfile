FROM debian:buster

RUN apt-get update
RUN apt-get --yes --fix-missing update

# Get and build proxygen with HTTP/3 support
RUN apt-get install --yes wget net-tools iputils-ping tcpdump ethtool iperf python3

# Copy HQ
COPY hq .
# Copy shared libs
COPY libs.tar .
RUN tar xvf libs.tar
RUN rm libs.tar

COPY client.py .

RUN mkdir /tmp/logs

# ENTRYPOINT [ "python3", "client.py", "hq", "1" ]