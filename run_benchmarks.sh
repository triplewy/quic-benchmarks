#!/bin/bash

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# 0 loss
sudo tcdel ens192 --all
sudo tcset ens192 --rate 100mbps --direction outgoing
sudo tcset ens192 --rate 100mbps --direction incoming --add
sudo tcshow ens192
$BASEDIR/run_benchmark.sh 0 0 100

# 0.1% loss
sudo tcdel ens192 --all
sudo tcset ens192 --rate 100mbps --loss 0.1% --direction outgoing
sudo tcset ens192 --rate 100mbps --loss 0.1% --direction incoming --add
sudo tcshow ens192
$BASEDIR/run_benchmark.sh 0dot1 0 100

# 1% loss
sudo tcdel ens192 --all
sudo tcset ens192 --rate 100mbps --loss 1% --direction outgoing
sudo tcset ens192 --rate 100mbps --loss 1% --direction incoming --add
sudo tcshow ens192
$BASEDIR/run_benchmark.sh 1 0 100

# 50ms delay
sudo tcdel ens192 --all
sudo tcset ens192 --rate 100mbps --delay 25ms --direction outgoing
sudo tcset ens192 --rate 100mbps --delay 25ms --direction incoming --add
sudo tcshow ens192
$BASEDIR/run_benchmark.sh 0 50 100

# 100ms delay
sudo tcdel ens192 --all
sudo tcset ens192 --rate 100mbps --delay 50ms --direction outgoing
sudo tcset ens192 --rate 100mbps --delay 50ms --direction incoming --add
sudo tcshow ens192
$BASEDIR/run_benchmark.sh 0 100 100

# 1% loss + 50ms delay
sudo tcdel ens192 --all
sudo tcset ens192 --rate 100mbps --delay 25ms --loss 1% --direction outgoing
sudo tcset ens192 --rate 100mbps --delay 25ms --loss 1% --direction incoming --add
sudo tcshow ens192
$BASEDIR/run_benchmark.sh 1 50 100

# Analysis
python3 $BASEDIR/main.py