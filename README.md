# QUIC Benchmarks

**Usage:**
```
 ./benchmark.sh [url] [results dir] [--single]

 [url]         - URL to benchmark
 [results dir] - Directory path to store results
 [--single]    - Toggle signifying whether benchmarked URL is a 
                 single-object web resource or full web-page 
```

By default, the amount of benchmark iterations is 10. You can change this by editing `ITERATIONS` in `benchmark.sh`.

## Setup

## Network Environments

10 MB bandwidth: `sudo tc qdisc add dev eth0 root tbf rate 10mbps`

100 ms delay: `sudo tc qdisc add dev eth0 root netem delay 100ms`

Burst loss: `sudo tc qdisc change dev eth0 root netem loss 0.3% 25%`

Clean up: `sudo tc qdisc del dev eth0 root`