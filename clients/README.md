# QUIC Benchmarks

## Directory layout

```
har
│   loss-0_delay-0_bw-1
│   loss-0_delay-0_bw-10
│   loss-0.1_delay-0_bw-1
│   loss-0.1_delay-0_bw-10
│   loss-1_delay-0_bw-1
│   loss-1_delay-0_bw-10
│   loss-0_delay-50_bw-1
│   loss-0_delay-50_bw-10
│   loss-0_delay-200_bw-1
│   loss-0_delay-200_bw-10
│   loss-1_delay-200_bw-1
└───loss-1_delay-200_bw-10
    │   facebook
    │   google
    └───cloudflare
        │   web   
        │   100KB
        │   1MB
        └───5MB
            │   chrome_h2.json   
            │   chrome_h3.json
            │   firefox_h2.json
            │   firefox_h3.json
            │   proxygen_h3.json
            │   curl_h2.json
            │   ngtcp2_h3.json

Total files: 12 * 3 * 4 * 7 = 1008
Total data points: 1008 * 20 = 20160