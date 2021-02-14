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
2. Once you have these clients installed, modify `local.json` with their respective paths. You will notice in `local.json` that the paths are currently from my machine.
3. For Chrome, we use Puppeteer which automatically downloads Chrome in node_modules. So you will need Node.js to run `npm install` in the `./chrome` directory.
4. Now that you have all clients setup, you will need Python 3 to run our benchmarking script.
5. Run `pip3 install -r requirements.txt` to download Python depedencies for our benchmarking script.

### Docker (In Progress)

1. You will need Python 3 to run our benchmarking script, which automatically downloads the necessary Docker images. These Docker images are described in `docker.json` 
2. Run `pip3 install -r requirements.txt` to download Python depedencies for our benchmarking script.
3. In `config.json`, modify the value of the `local` key to be `false`.


## Usage

```
 ./run_benchmark.sh [dir]

 [dir] - Directory path to store results
```

Our benchmarking configuration is found in `config.json`. Each key in our config has a description which describes its purpose.