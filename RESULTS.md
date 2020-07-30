# Results

| Bandwidth | Loss | Delay (RTT) |
| --------- | ---- | ----------- |
| 10 MB     | 0%   | 0ms         |
| 10 MB     | 5%   | 0ms         |
| 10 MB     | 0%   | 200ms       |
| 10 MB     | 5%   | 200ms       |


## Facebook

20 Iterations for each endpoint. Graphs show mean of total time to load the web 
page. Curl and HQ have poorer results in the smaller sized pages since they are
run in subprocesses and the time measurement consists of the process starting 
and exiting.

![fb-kb-bw_1](./graphs/FB-KB-bw_1.png)
![fb-mb-bw_1](./graphs/FB-MB-bw_1.png)
![fb-kb-bw_5](./graphs/FB-KB-bw_5.png)
![fb-mb-bw_5](./graphs/FB-MB-bw_5.png)
![fb-kb-bw_10](./graphs/FB-KB-bw_10.png)
![fb-mb-bw_10](./graphs/FB-MB-bw_10.png)
![fb-kb-loss_1](./graphs/FB-KB-loss_1.png)
![fb-mb-loss_1](./graphs/FB-MB-loss_1.png)
![fb-kb-loss_5](./graphs/FB-KB-loss_5.png)
![fb-mb-loss_5](./graphs/FB-MB-loss_5.png)
![fb-kb-loss_5](./graphs/FB-KB-loss_10.png)
![fb-mb-loss_5](./graphs/FB-MB-loss_10.png)

![](./graphs/quiche-client_qlog.png)
![](./graphs/aioquic_client.png)
![](./graphs/ngtcp2_client.png)
![](./graphs/mvfst_qlog_from_single_connection.png)

### Conclusion

No egregious discrepancies. H3 and H2 performance seem quite similar.

## Cloudflare

![cf](./graphs/CF.png)

## Microsoft

![ms](./graphs/MS.png)

## F5

![f5](./graphs/F5.png)