#!/bin/bash

for i in 1 2
do
    # 0 loss
    sudo tcset ens192 --rate 50mbps --direction incoming
    sudo tcset ens192 --rate 50mbps --direction outgoing
    python3 benchmark.py 0 0 50
    sudo tcdel ens192 --all
    
    # 0.1 loss
    sudo tcset ens192 --rate 50mbps --loss 0.1% --direction incoming
    sudo tcset ens192 --rate 50mbps --loss 0.1% --direction outgoing
    python3 benchmark.py 0dot1 0 50
    sudo tcdel ens192 --all
    
    # 1 loss
    sudo tcset ens192 --rate 50mbps --loss 1% --direction incoming
    sudo tcset ens192 --rate 50mbps --loss 1% --direction outgoing
    python3 benchmark.py 1 0 50
    sudo tcdel ens192 --all
    
    # 50ms delay
    sudo tcset ens192 --rate 50mbps --delay 25ms --direction incoming
    sudo tcset ens192 --rate 50mbps --delay 25ms --direction outgoing
    python3 benchmark.py 0 50 50
    sudo tcdel ens192 --all
    
    # 100ms delay
    sudo tcset ens192 --rate 50mbps --delay 50ms --direction incoming
    sudo tcset ens192 --rate 50mbps --delay 50ms --direction outgoing
    python3 benchmark.py 0 100 50
    sudo tcdel ens192 --all
    
done