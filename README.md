# QUIC Benchmarks

## Purpose

The purpose of this project is to **benchmark throughput and latency for various 
public QUIC endpoints**. We use public endpoints since the OSS versions of some 
QUIC implementions (Google, Facebook, Cloudflare) do not represent what these 
companies use in production. The QUIC clients used for this project are Chrome 
Canary, Firefox Nightly, ngtcp2, and quiche. When possible, we also benchmark
the H2 counterparts for these public endpoints and compare them with H3 results.

## Methodology

Each benchmark scenario is run 50 times to offset internet network conditions.

### Public Endpoints

| Implementation | Cases                                            |
| -------------- | ------------------------------------------------ |
| Facebook       | 0B, 1KB, 10KB, 100KB, 500KB, 1MB, 2MB, 5MB, 10MB |
| Cloudflare     | 1MB, 5MB                                         |

### Client Scenarios

- 1 request
- 10 parallel requests
- 100 parallel requests

### Network Conditions

## Measuring Results

### Throughput

Browsers: Use HAR files
Non-browsers: Use python scripts