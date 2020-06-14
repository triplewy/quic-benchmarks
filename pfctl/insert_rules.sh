#!/bin/bash

sudo dnctl pipe 1 config plr 0.01 queue 50
sudo pfctl -a ts -f rules.txt