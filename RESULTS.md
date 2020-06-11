# Results

## Facebook

20 Iterations for each endpoint. Graphs show mean of total time to load the web 
page. Curl and HQ have poorer results in the smaller sized pages since they are
run in subprocesses and the time measurement consists of the process starting 
and exiting.

![fb-kb-0](./graphs/FB-KB-loss_0.png)
![fb-mb-0](./graphs/FB-MB-loss_0.png)
![fb-kb-1](./graphs/FB-KB-loss_1.png)
![fb-mb-1](./graphs/FB-MB-loss_1.png)

### Conclusion

No egregious discrepancies. H3 and H2 performance seem quite similar.

## Cloudflare

![cf](./graphs/CF.png)

## Microsoft

![ms](./graphs/MS.png)

## F5

![f5](./graphs/F5.png)