#!/bin/bash

# QUIC docker implementations: https://github.com/marten-seemann/quic-interop-runner/blob/master/implementations.json

# Pull proxygen image
sudo docker pull lnicco/mvfst-qns:latest

# Pull ngtcp2 image
sudo docker pull ghcr.io/ngtcp2/ngtcp2-interop:latest
