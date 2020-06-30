#!/bin/bash

# sudo dnctl pipe 1 config plr 0.10 delay 500 bw 10Mbit/s queue 100
sudo dnctl pipe 1 config bw 1Kbit/s queue 100
sudo pfctl -a ts -f rules.txt