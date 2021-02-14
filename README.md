# QUIC Benchmarks

This repository is a set of tools to benchmark, compare, and analyze QUIC and TCP performance of production endpoints. So far, we have used this tool on endpoints from **Google**, **Facebook**, and **Cloudflare** which are detailed in `endpoints.json`.

The general workflow for our benchmark comprises of the below steps:

1. Use various QUIC and TCP clients to send requests to production endpoints
2. Gather logs and metrics from these requests in various formats
3. Create visualizations from these metrics and logs 

## Clients

- QUIC (HTTP/3)
  - Google Chrome
  - Facebook Proxygen
  - Ngtcp2
- TCP (HTTP/2)
  - Google Chrome
  - cURL

In order to use these clients, you can build them locally or use Docker images, which we automatically download with our tool.

## Setup

### Building Locally

1. Download and build Proxygen, Ngtcp2, and cURL clients. You do not need to build Chrome.
2. Once you have these clients installed, modify `config.json` with their respective paths. You will notice in `config.json` that the paths are currently from my machine.
3. For Chrome, we use Puppeteer which automatically downloads Chrome in node_modules. So you will need Node.js to run `npm install` in the `./chrome` directory.
4. Now that you have all clients setup, you will need Python 3 to run our benchmarking script.
5. Run `pip3 install -r requirements.txt` to download Python depedencies for our benchmarking script.

### Docker

## Usage

```
 ./benchmark.sh [url] -d [results dir] -n [iterations] [-s]

 [url]            - URL to benchmark
 -d [results dir] - Directory path to store results
 -n [iterations]  - Number of iterations to run
 [-s]             - Toggle signifying whether benchmarked URL is a 
                    single-object web resource or full web-page 
```

By default, the amount of benchmark iterations is 10. 

## Network Environments

10 MB bandwidth: `sudo tc qdisc add dev eth0 root tbf rate 10mbps`

100 ms delay: `sudo tc qdisc add dev eth0 root netem delay 100ms`

Burst loss: `sudo tc qdisc change dev eth0 root netem loss 0.3% 25%`

Clean up: `sudo tc qdisc del dev eth0 root`