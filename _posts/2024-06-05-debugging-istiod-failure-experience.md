---
layout: post
title: "Debugging istiod failure: 'why is it so hard to find out disk pressure?'"
date: 2024-06-05
tags: [k8s, istio, debugging, failure]
---

# Debugging istiod failure: 'why is it so hard to find out disk pressure?'

*How a simple disk space issue turned into a 3-hour debugging*

I have been using istio service mesh in kubernetes cluster for my research project. It makes the infra one layer more complicated with sidecar layer with additional istio-gateway and istiod. It is cost that you have to pay to enjoy the nice netwwork network layer abstraction. One day, while I was running experiments, the `istiod` control plane went down, and istio-ingress gateway pods were failing. What should have been a simple connectivity issue turned into unnecessarily annoying root cause analysis.

Look at this beautiful k8s pod status. What a great reliable system. maybe it is built to panic the user when something goes wrong. maybe it is design choice?

```bash
gangmuk@node0:~$ kubectl get pod -n istio-system
NAME                                   READY   STATUS                   RESTARTS   AGE
istio-ingressgateway-86c4b5c6f-45srp   0/1     Completed                0          68m
istio-ingressgateway-86c4b5c6f-47kz9   0/1     Completed                0          52m
istio-ingressgateway-86c4b5c6f-49tbv   0/1     ContainerStatusUnknown   1          90m
istio-ingressgateway-86c4b5c6f-4d6zq   0/1     Completed                0          14m
istio-ingressgateway-86c4b5c6f-4g8sq   0/1     Completed                0          36m
istio-ingressgateway-86c4b5c6f-4l7qw   0/1     ContainerStatusUnknown   1          8d
istio-ingressgateway-86c4b5c6f-4p25p   0/1     Completed                0          90m
istio-ingressgateway-86c4b5c6f-4q558   0/1     ContainerStatusUnknown   1          98m
istio-ingressgateway-86c4b5c6f-4tqrf   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-4v479   0/1     Completed                0          75m
istio-ingressgateway-86c4b5c6f-4wgtf   0/1     Completed                0          51m
istio-ingressgateway-86c4b5c6f-57m6j   0/1     Completed                0          60m
istio-ingressgateway-86c4b5c6f-584vw   0/1     Completed                0          82m
istio-ingressgateway-86c4b5c6f-5jwr5   0/1     Completed                0          74m
istio-ingressgateway-86c4b5c6f-6gcxw   0/1     Completed                0          37m
istio-ingressgateway-86c4b5c6f-6p4dw   0/1     Completed                0          13m
istio-ingressgateway-86c4b5c6f-6xmc7   0/1     Completed                0          52m
istio-ingressgateway-86c4b5c6f-6zxvw   0/1     Completed                0          44m
istio-ingressgateway-86c4b5c6f-79zm8   0/1     Completed                0          90m
istio-ingressgateway-86c4b5c6f-7pfwz   0/1     Completed                0          75m
istio-ingressgateway-86c4b5c6f-7x86k   0/1     Completed                0          66m
istio-ingressgateway-86c4b5c6f-849vm   0/1     ContainerStatusUnknown   1          67m
istio-ingressgateway-86c4b5c6f-87d5m   0/1     Pending                  0          3s
istio-ingressgateway-86c4b5c6f-8gt25   0/1     Running                  0          7m26s
istio-ingressgateway-86c4b5c6f-8pjgd   0/1     Completed                0          67m
istio-ingressgateway-86c4b5c6f-9k96j   0/1     Completed                0          67m
istio-ingressgateway-86c4b5c6f-9nns9   0/1     Error                    0          22m
istio-ingressgateway-86c4b5c6f-9pzzt   0/1     Completed                0          37m
istio-ingressgateway-86c4b5c6f-9z2nx   0/1     Completed                0          44m
istio-ingressgateway-86c4b5c6f-bb6ws   0/1     Completed                0          60m
istio-ingressgateway-86c4b5c6f-bcwvh   0/1     Running                  0          7m34s
istio-ingressgateway-86c4b5c6f-bg87k   0/1     ContainerStatusUnknown   1          53m
istio-ingressgateway-86c4b5c6f-bj5w9   0/1     Completed                0          82m
istio-ingressgateway-86c4b5c6f-bkz54   0/1     Completed                0          74m
istio-ingressgateway-86c4b5c6f-brxkt   0/1     Completed                0          52m
istio-ingressgateway-86c4b5c6f-c88zc   0/1     ContainerStatusUnknown   1          44m
istio-ingressgateway-86c4b5c6f-c9dnl   0/1     Completed                0          6m12s
istio-ingressgateway-86c4b5c6f-cjv86   0/1     Completed                0          83m
istio-ingressgateway-86c4b5c6f-ck8dn   0/1     Completed                0          45m
istio-ingressgateway-86c4b5c6f-d69v9   0/1     Completed                0          59m
istio-ingressgateway-86c4b5c6f-dhc26   0/1     Completed                0          21m
istio-ingressgateway-86c4b5c6f-dkt2l   0/1     Completed                0          74m
istio-ingressgateway-86c4b5c6f-fls8b   0/1     Completed                0          36m
istio-ingressgateway-86c4b5c6f-fmk2f   0/1     ContainerStatusUnknown   1          8d
istio-ingressgateway-86c4b5c6f-ggbtn   0/1     ContainerStatusUnknown   1          14m
istio-ingressgateway-86c4b5c6f-ggfpl   0/1     Completed                0          29m
istio-ingressgateway-86c4b5c6f-gkvs8   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-glbts   0/1     ContainerStatusUnknown   1          97m
istio-ingressgateway-86c4b5c6f-grdj7   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-gsrr6   0/1     Completed                0          21m
istio-ingressgateway-86c4b5c6f-hf5g5   0/1     Completed                0          75m
istio-ingressgateway-86c4b5c6f-hgkvz   0/1     Completed                0          75m
istio-ingressgateway-86c4b5c6f-hl76k   0/1     ContainerStatusUnknown   1          52m
istio-ingressgateway-86c4b5c6f-hlwrw   0/1     ContainerStatusUnknown   1          59m
istio-ingressgateway-86c4b5c6f-hpcrd   0/1     ContainerStatusUnknown   1          67m
istio-ingressgateway-86c4b5c6f-j26gk   0/1     Completed                0          74m
istio-ingressgateway-86c4b5c6f-j4xn5   0/1     ContainerStatusUnknown   1          13m
istio-ingressgateway-86c4b5c6f-j5m7g   0/1     Completed                0          14m
istio-ingressgateway-86c4b5c6f-j689s   0/1     Completed                0          29m
istio-ingressgateway-86c4b5c6f-j6x4c   0/1     Completed                0          45m
istio-ingressgateway-86c4b5c6f-j8s9r   0/1     Completed                0          82m
istio-ingressgateway-86c4b5c6f-jbzk4   0/1     ContainerStatusUnknown   1          45m
istio-ingressgateway-86c4b5c6f-jf84x   0/1     Completed                0          75m
istio-ingressgateway-86c4b5c6f-jfzjj   0/1     Completed                0          44m
istio-ingressgateway-86c4b5c6f-jm67q   0/1     Completed                0          90m
istio-ingressgateway-86c4b5c6f-jpjr6   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-k2v4d   0/1     Completed                0          83m
istio-ingressgateway-86c4b5c6f-k876b   0/1     ContainerStatusUnknown   1          37m
istio-ingressgateway-86c4b5c6f-kgkcw   0/1     Completed                0          37m
istio-ingressgateway-86c4b5c6f-kjqvr   0/1     Completed                0          28m
istio-ingressgateway-86c4b5c6f-kmvtp   0/1     Completed                0          36m
istio-ingressgateway-86c4b5c6f-ks6cg   0/1     Completed                0          37m
istio-ingressgateway-86c4b5c6f-l8ptx   0/1     Completed                0          91m
istio-ingressgateway-86c4b5c6f-lccv6   0/1     Completed                0          60m
istio-ingressgateway-86c4b5c6f-lh9b5   0/1     ContainerStatusUnknown   1          22m
istio-ingressgateway-86c4b5c6f-llj6g   0/1     Completed                0          45m
istio-ingressgateway-86c4b5c6f-lttc4   0/1     Completed                0          30m
istio-ingressgateway-86c4b5c6f-lw2k2   0/1     ContainerStatusUnknown   1          14m
istio-ingressgateway-86c4b5c6f-mh9d9   0/1     Completed                0          90m
istio-ingressgateway-86c4b5c6f-mmwdp   0/1     Completed                0          97m
istio-ingressgateway-86c4b5c6f-mq7q5   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-mqbf6   0/1     Completed                0          29m
istio-ingressgateway-86c4b5c6f-n4vqt   1/1     Running                  0          6m59s
istio-ingressgateway-86c4b5c6f-n8j7h   0/1     Completed                0          82m
istio-ingressgateway-86c4b5c6f-nh4dg   0/1     Completed                0          53m
istio-ingressgateway-86c4b5c6f-nnv8j   0/1     Completed                0          20m
istio-ingressgateway-86c4b5c6f-nt8w4   0/1     Completed                0          14m
istio-ingressgateway-86c4b5c6f-nvw5g   0/1     Completed                0          52m
istio-ingressgateway-86c4b5c6f-nw9gh   0/1     ContainerStatusUnknown   1          91m
istio-ingressgateway-86c4b5c6f-p2bfp   0/1     ContainerStatusUnknown   1          13m
istio-ingressgateway-86c4b5c6f-pfhgb   0/1     Completed                0          59m
istio-ingressgateway-86c4b5c6f-phd6t   0/1     ContainerStatusUnknown   1          37m
istio-ingressgateway-86c4b5c6f-plbd2   0/1     ContainerStatusUnknown   1          98m
istio-ingressgateway-86c4b5c6f-pqcw7   0/1     ContainerStatusUnknown   1          37m
istio-ingressgateway-86c4b5c6f-prkhn   1/1     Running                  0          6m34s
istio-ingressgateway-86c4b5c6f-psl4l   0/1     ContainerStatusUnknown   1          8d
istio-ingressgateway-86c4b5c6f-pxjsh   1/1     Running                  0          5m55s
istio-ingressgateway-86c4b5c6f-q8mns   0/1     Completed                0          59m
istio-ingressgateway-86c4b5c6f-qcv6j   0/1     ContainerStatusUnknown   1          14m
istio-ingressgateway-86c4b5c6f-qdsz4   0/1     Completed                0          52m
istio-ingressgateway-86c4b5c6f-qp4ql   0/1     Running                  0          6m20s
istio-ingressgateway-86c4b5c6f-qzhrp   0/1     Completed                0          82m
istio-ingressgateway-86c4b5c6f-qzxpx   0/1     Completed                0          43m
istio-ingressgateway-86c4b5c6f-r7jhw   0/1     Running                  0          6m27s
istio-ingressgateway-86c4b5c6f-rbhp9   0/1     ContainerStatusUnknown   1          51m
istio-ingressgateway-86c4b5c6f-rg6n2   0/1     ContainerStatusUnknown   1          29m
istio-ingressgateway-86c4b5c6f-rk4f4   0/1     Completed                0          83m
istio-ingressgateway-86c4b5c6f-rvjjt   0/1     ContainerStatusUnknown   1          21m
istio-ingressgateway-86c4b5c6f-sb664   0/1     Running                  0          6m52s
istio-ingressgateway-86c4b5c6f-sm26n   0/1     ContainerStatusUnknown   1          21m
istio-ingressgateway-86c4b5c6f-spkxj   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-spn48   0/1     Completed                0          15m
istio-ingressgateway-86c4b5c6f-sz65r   0/1     Completed                0          67m
istio-ingressgateway-86c4b5c6f-t4w66   0/1     Completed                0          30m
istio-ingressgateway-86c4b5c6f-t5jdb   0/1     Completed                0          59m
istio-ingressgateway-86c4b5c6f-tb9wz   0/1     Completed                0          60m
istio-ingressgateway-86c4b5c6f-tljvj   0/1     Completed                0          91m
istio-ingressgateway-86c4b5c6f-tn6jw   0/1     ContainerStatusUnknown   1          98m
istio-ingressgateway-86c4b5c6f-v7qdr   0/1     Completed                0          29m
istio-ingressgateway-86c4b5c6f-vcq4j   0/1     Completed                0          97m
istio-ingressgateway-86c4b5c6f-vrrfl   0/1     ContainerStatusUnknown   1          90m
istio-ingressgateway-86c4b5c6f-vsstx   0/1     Completed                0          97m
istio-ingressgateway-86c4b5c6f-w25rt   0/1     Completed                0          75m
istio-ingressgateway-86c4b5c6f-w8l2r   0/1     Completed                0          30m
istio-ingressgateway-86c4b5c6f-w9x4w   0/1     ContainerStatusUnknown   1          67m
istio-ingressgateway-86c4b5c6f-wbs7w   0/1     ContainerStatusUnknown   1          68m
istio-ingressgateway-86c4b5c6f-wc2xj   0/1     Completed                0          21m
istio-ingressgateway-86c4b5c6f-wlx98   0/1     Completed                0          44m
istio-ingressgateway-86c4b5c6f-wqg29   0/1     ContainerStatusUnknown   1          89m
istio-ingressgateway-86c4b5c6f-x6q6j   0/1     Completed                0          60m
istio-ingressgateway-86c4b5c6f-x8fzr   0/1     Completed                0          21m
istio-ingressgateway-86c4b5c6f-xb79w   0/1     Completed                0          83m
istio-ingressgateway-86c4b5c6f-xfvtp   0/1     Completed                0          29m
istio-ingressgateway-86c4b5c6f-xj2ts   0/1     ContainerStatusUnknown   1          97m
istio-ingressgateway-86c4b5c6f-xj5mt   0/1     Completed                0          96m
istio-ingressgateway-86c4b5c6f-xknf8   0/1     Completed                0          68m
istio-ingressgateway-86c4b5c6f-z4w4v   0/1     Running                  0          7m6s
istio-ingressgateway-86c4b5c6f-z5www   0/1     Completed                0          8d
istio-ingressgateway-86c4b5c6f-z8vwk   0/1     Completed                0          82m
istio-ingressgateway-86c4b5c6f-zpm8d   0/1     Completed                0          22m
istio-ingressgateway-86c4b5c6f-zrrwq   0/1     ContainerStatusUnknown   1          98m
istiod-67c6566457-2mn8v                0/1     Completed                0          60m
istiod-67c6566457-4f9xt                1/1     Running                  0          7m23s
istiod-67c6566457-4h9q8                0/1     Evicted                  0          98m
istiod-67c6566457-6ls95                0/1     Evicted                  0          98m
istiod-67c6566457-74gms                0/1     Completed                0          8d
istiod-67c6566457-7mfl6                0/1     Completed                0          36m
istiod-67c6566457-8s8hs                0/1     Evicted                  0          98m
istiod-67c6566457-97prn                0/1     Evicted                  0          98m
istiod-67c6566457-bprft                0/1     Evicted                  0          98m
istiod-67c6566457-br6ts                0/1     ContainerStatusUnknown   1          45m
istiod-67c6566457-bwzd4                0/1     ContainerStatusUnknown   1          74m
istiod-67c6566457-cncnn                0/1     Evicted                  0          98m
istiod-67c6566457-d97vv                0/1     ContainerStatusUnknown   1          98m
istiod-67c6566457-dphj2                0/1     ContainerStatusUnknown   1          66m
istiod-67c6566457-flnt5                0/1     Evicted                  0          98m
istiod-67c6566457-gxhqx                0/1     ContainerStatusUnknown   1          51m
istiod-67c6566457-lvs56                0/1     Evicted                  0          98m
istiod-67c6566457-m97vf                0/1     Evicted                  0          98m
istiod-67c6566457-mb2nk                0/1     ContainerStatusUnknown   1          89m
istiod-67c6566457-mbmrm                0/1     Completed                0          13m
istiod-67c6566457-n7q6b                0/1     Evicted                  0          98m
istiod-67c6566457-nnbs8                0/1     Completed                0          83m
istiod-67c6566457-p9rds                0/1     Evicted                  0          98m
istiod-67c6566457-ph57n                0/1     Evicted                  0          98m
istiod-67c6566457-qxg4z                0/1     Completed                0          22m
istiod-67c6566457-whhtq                0/1     Evicted                  0          98m
istiod-67c6566457-wtvd4                0/1     Completed                0          28m
istiod-67c6566457-x4q9q                0/1     Evicted                  0          98m

```

TLDR; the root cause was

## What I did...

At the very first place, before I started debugging, I thought it would be istio-ingressgateway was overloaded and failed, especially because it actually happened. But this time, it was not istio-ingressgateway problem.

I started by checking the envoy proxy logs
```bash
warning envoy config external/envoy/source/extensions/config_subscription/grpc/grpc_stream.h:190 StreamAggregatedResources gRPC config stream to xds-grpc closed since 354s ago: 14, connection error: desc = "transport: Error while dialing: dial tcp 10.97.219.77:15012: connect: connection refused
```

And checked what this ''10.97.219.77:15012'' ip address comes from and it was istiod svc's cluster ip address.

```bash
k get svc -n istio-system
NAME                   TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)                                      AGE
istio-ingressgateway   LoadBalancer   10.100.183.27   <pending>     15021:31560/TCP,80:32462/TCP,443:32155/TCP   9d
istiod                 ClusterIP      10.97.219.77    <none>        15010/TCP,15012/TCP,443/TCP,15014/TCP        9d
```

so, I checked istiod deployment and none of the pods were ready. Not just istiod deployment but also all the pods of istio-ingressgateway deployment were not ready. This is why I thought istio-ingressgateway was the root cause since istio-ingressgateway is the one that processes the incoming traffic to forward to upstream app services. And istiod is control plane which uses much less resources and it is not even in request critical path. That's why istiod does not even have multiple replicas most of the time.

```bash
kubectl get deploy -n istio-system
NAME                   READY   UP-TO-DATE   AVAILABLE   AGE
istio-ingressgateway   0/10    10           0           9d
istiod                 0/1     1            0           9d
```

I described istiod deployment to see what was going on. Basically, it does not say why 0 pod is availalbe and 1/1 is unavailable. It just says "NewReplicaSetAvailable" and "MinimumReplicasUnavailable". NICE. GREAT. You know what either kubernetes of service mesh should have clearly described why it is not available at this stage. It is not good that user should do more than this to figure out the cause of pod unavailability.

```yaml
k describe deploy istiod -n istio-system
Name:                   istiod
Namespace:              istio-system
CreationTimestamp:      Tue, 16 Jul 2024 05:17:45 +0000
Labels:                 app=istiod
                        istio=pilot
                        istio.io/rev=default
Annotations:            deployment.kubernetes.io/revision: 3
Selector:               istio=pilot
Replicas:               1 desired | 1 updated | 1 total | 0 available | 1 unavailable
  ...
Conditions:
  Type           Status  Reason
  ----           ------  ------
  Progressing    True    NewReplicaSetAvailable
  Available      False   MinimumReplicasUnavailable
OldReplicaSets:  istiod-bc4584967 (0/0 replicas created), istiod-67c6566457 (0/0 replicas created)
NewReplicaSet:   istiod-7fb964cc7b (1/1 replicas created)
Events:
  Type    Reason             Age    From                   Message
  ----    ------             ----   ----                   -------
  Normal  ScalingReplicaSet  6m23s  deployment-controller  Scaled up replica set istiod-7fb964cc7b to 1
  Normal  ScalingReplicaSet  116s   deployment-controller  Scaled down replica set istiod-67c6566457 to 0 from 1
```

I wrapped around my head and thought, "okay, let's check other k8s controller. what about repliacset controller? That's what controls the pod replicas."

```bash
k get rs -n istio-system
NAME                              DESIRED   CURRENT   READY   AGE
istio-ingressgateway-5fc67fbd74   0         0         0       9d
istio-ingressgateway-8676d66897   0         0         0       8d
istio-ingressgateway-86c4b5c6f    10        10        0       8d
istiod-67c6566457                 0         0         0       8d
istiod-7fb964cc7b                 1         1         0       7m23s
istiod-bc4584967                  0         0         0       9d
```

```yaml
$ k describe rs istiod-7fb964cc7b -n istio-system
Name:           istiod-7fb964cc7b
Namespace:      istio-system
Selector:       istio=pilot,pod-template-hash=7fb964cc7b
Labels:         app=istiod
                install.operator.istio.io/owning-resource=unknown
                istio=pilot
...

Events:
  Type    Reason            Age    From                   Message
  ----    ------            ----   ----                   -------
  Normal  SuccessfulCreate  8m35s  replicaset-controller  Created pod: istiod-7fb964cc7b-gqxz5
  Normal  SuccessfulCreate  3m36s  replicaset-controller  Created pod: istiod-7fb964cc7b-7r4z7
```
AMAZING. Nothing useful. 

Okay, it is fine, I never expected replicaset will give some useful information. Let's check something more details than what kubectl describe command gives. Let's check actual istiod's pod log.

(it is long. I put all to give how bad it is to debug)
```bash
gangmuk@node0:~$ k logs -n istio-system istiod-67c6566457-4f9xt
2024-07-25T20:12:52.265556Z	info	FLAG: --caCertFile=""
2024-07-25T20:12:52.265607Z	info	FLAG: --clusterAliases="[]"
2024-07-25T20:12:52.265617Z	info	FLAG: --clusterID="Kubernetes"
2024-07-25T20:12:52.265621Z	info	FLAG: --clusterRegistriesNamespace="istio-system"
2024-07-25T20:12:52.265625Z	info	FLAG: --configDir=""
2024-07-25T20:12:52.265629Z	info	FLAG: --ctrlz_address="localhost"
2024-07-25T20:12:52.265635Z	info	FLAG: --ctrlz_port="9876"
2024-07-25T20:12:52.265639Z	info	FLAG: --domain="cluster.local"
2024-07-25T20:12:52.265644Z	info	FLAG: --grpcAddr=":15010"
2024-07-25T20:12:52.265649Z	info	FLAG: --help="false"
2024-07-25T20:12:52.265653Z	info	FLAG: --httpAddr=":8080"
2024-07-25T20:12:52.265657Z	info	FLAG: --httpsAddr=":15017"
2024-07-25T20:12:52.265662Z	info	FLAG: --keepaliveInterval="30s"
2024-07-25T20:12:52.265667Z	info	FLAG: --keepaliveMaxServerConnectionAge="30m0s"
2024-07-25T20:12:52.265672Z	info	FLAG: --keepaliveTimeout="10s"
2024-07-25T20:12:52.265675Z	info	FLAG: --kubeconfig=""
2024-07-25T20:12:52.265681Z	info	FLAG: --kubernetesApiBurst="160"
2024-07-25T20:12:52.265688Z	info	FLAG: --kubernetesApiQPS="80"
2024-07-25T20:12:52.265693Z	info	FLAG: --log_as_json="false"
2024-07-25T20:12:52.265697Z	info	FLAG: --log_caller=""
2024-07-25T20:12:52.265702Z	info	FLAG: --log_output_level="default:info"
2024-07-25T20:12:52.265706Z	info	FLAG: --log_rotate=""
2024-07-25T20:12:52.265714Z	info	FLAG: --log_rotate_max_age="30"
2024-07-25T20:12:52.265721Z	info	FLAG: --log_rotate_max_backups="1000"
2024-07-25T20:12:52.265730Z	info	FLAG: --log_rotate_max_size="104857600"
2024-07-25T20:12:52.265740Z	info	FLAG: --log_stacktrace_level="default:none"
2024-07-25T20:12:52.265755Z	info	FLAG: --log_target="[stdout]"
2024-07-25T20:12:52.265762Z	info	FLAG: --meshConfig="./etc/istio/config/mesh"
2024-07-25T20:12:52.265766Z	info	FLAG: --monitoringAddr=":15014"
2024-07-25T20:12:52.265771Z	info	FLAG: --namespace="istio-system"
2024-07-25T20:12:52.265776Z	info	FLAG: --networksConfig="./etc/istio/config/meshNetworks"
2024-07-25T20:12:52.265782Z	info	FLAG: --profile="true"
2024-07-25T20:12:52.265808Z	info	FLAG: --registries="[Kubernetes]"
2024-07-25T20:12:52.265822Z	info	FLAG: --secureGRPCAddr=":15012"
2024-07-25T20:12:52.265828Z	info	FLAG: --shutdownDuration="10s"
2024-07-25T20:12:52.265841Z	info	FLAG: --tls-cipher-suites="[]"
2024-07-25T20:12:52.265847Z	info	FLAG: --tlsCertFile=""
2024-07-25T20:12:52.265851Z	info	FLAG: --tlsKeyFile=""
2024-07-25T20:12:52.265858Z	info	FLAG: --vklog="0"
2024-07-25T20:12:52.294539Z	info	initializing Istiod admin server
2024-07-25T20:12:52.308477Z	info	starting HTTP service at [::]:8080
2024-07-25T20:12:52.309912Z	info	initializing mesh configuration ./etc/istio/config/mesh
2024-07-25T20:12:52.325405Z	info	controllers	starting	controller=configmap istio
2024-07-25T20:12:52.325763Z	info	Loaded MeshNetworks config from Kubernetes API server.
2024-07-25T20:12:52.325785Z	info	mesh networks configuration updated to: {

}
2024-07-25T20:12:52.328755Z	info	Loaded MeshConfig config from Kubernetes API server.
2024-07-25T20:12:52.329367Z	info	mesh configuration updated to: {
    "proxyListenPort": 15001,
    "proxyInboundListenPort": 15006,
    "connectTimeout": "10s",
    "protocolDetectionTimeout": "0s",
    "ingressClass": "istio",
    "ingressService": "istio-ingressgateway",
    "ingressControllerMode": "STRICT",
    "enableTracing": true,
    "defaultConfig": {
        "configPath": "./etc/istio/proxy",
        "binaryPath": "/usr/local/bin/envoy",
        "serviceCluster": "istio-proxy",
        "drainDuration": "45s",
        "discoveryAddress": "istiod.istio-system.svc:15012",
        "proxyAdminPort": 15000,
        "controlPlaneAuthPolicy": "MUTUAL_TLS",
        "statNameLength": 189,
        "tracing": {
            "zipkin": {
                "address": "zipkin.istio-system:9411"
            }
        },
        "statusPort": 15020,
        "terminationDrainDuration": "5s"
    },
    "outboundTrafficPolicy": {
        "mode": "ALLOW_ANY"
    },
    "enableAutoMtls": true,
    "trustDomain": "cluster.local",
    "defaultServiceExportTo": [
        "*"
    ],
    "defaultVirtualServiceExportTo": [
        "*"
    ],
    "defaultDestinationRuleExportTo": [
        "*"
    ],
    "rootNamespace": "istio-system",
    "localityLbSetting": {
        "enabled": true
    },
    "dnsRefreshRate": "60s",
    "enablePrometheusMerge": true,
    "extensionProviders": [
        {
            "name": "prometheus",
            "prometheus": {

            }
        },
        {
            "name": "stackdriver",
            "stackdriver": {

            }
        },
        {
            "name": "envoy",
            "envoyFileAccessLog": {
                "path": "/dev/stdout"
            }
        }
    ],
    "defaultProviders": {
        "metrics": [
            "prometheus"
        ]
    }
}
2024-07-25T20:12:52.341531Z	info	initializing mesh networks from mesh config watcher
2024-07-25T20:12:52.341698Z	info	mesh configuration: {
    "proxyListenPort": 15001,
    "proxyInboundListenPort": 15006,
    "connectTimeout": "10s",
    "protocolDetectionTimeout": "0s",
    "ingressClass": "istio",
    "ingressService": "istio-ingressgateway",
    "ingressControllerMode": "STRICT",
    "enableTracing": true,
    "defaultConfig": {
        "configPath": "./etc/istio/proxy",
        "binaryPath": "/usr/local/bin/envoy",
        "serviceCluster": "istio-proxy",
        "drainDuration": "45s",
        "discoveryAddress": "istiod.istio-system.svc:15012",
        "proxyAdminPort": 15000,
        "controlPlaneAuthPolicy": "MUTUAL_TLS",
        "statNameLength": 189,
        "tracing": {
            "zipkin": {
                "address": "zipkin.istio-system:9411"
            }
        },
        "statusPort": 15020,
        "terminationDrainDuration": "5s"
    },
    "outboundTrafficPolicy": {
        "mode": "ALLOW_ANY"
    },
    "enableAutoMtls": true,
    "trustDomain": "cluster.local",
    "defaultServiceExportTo": [
        "*"
    ],
    "defaultVirtualServiceExportTo": [
        "*"
    ],
    "defaultDestinationRuleExportTo": [
        "*"
    ],
    "rootNamespace": "istio-system",
    "localityLbSetting": {
        "enabled": true
    },
    "dnsRefreshRate": "60s",
    "enablePrometheusMerge": true,
    "extensionProviders": [
        {
            "name": "prometheus",
            "prometheus": {

            }
        },
        {
            "name": "stackdriver",
            "stackdriver": {

            }
        },
        {
            "name": "envoy",
            "envoyFileAccessLog": {
                "path": "/dev/stdout"
            }
        }
    ],
    "defaultProviders": {
        "metrics": [
            "prometheus"
        ]
    }
}
2024-07-25T20:12:52.341711Z	info	version: 1.20.3-692e556046b48ebc471205211c68a2c69e74a321-Clean
2024-07-25T20:12:52.342088Z	info	flags: {
   "ServerOptions": {
      "HTTPAddr": ":8080",
      "HTTPSAddr": ":15017",
      "GRPCAddr": ":15010",
      "MonitoringAddr": ":15014",
      "EnableProfiling": true,
      "TLSOptions": {
         "CaCertFile": "",
         "CertFile": "",
         "KeyFile": "",
         "TLSCipherSuites": null,
         "CipherSuits": null
      },
      "SecureGRPCAddr": ":15012"
   },
   "InjectionOptions": {
      "InjectionDirectory": "./var/lib/istio/inject"
   },
   "PodName": "istiod-67c6566457-4f9xt",
   "Namespace": "istio-system",
   "Revision": "default",
   "MeshConfigFile": "./etc/istio/config/mesh",
   "NetworksConfigFile": "./etc/istio/config/meshNetworks",
   "RegistryOptions": {
      "FileDir": "",
      "Registries": [
         "Kubernetes"
      ],
      "KubeOptions": {
         "SystemNamespace": "",
         "MeshServiceController": null,
         "DomainSuffix": "cluster.local",
         "ClusterID": "Kubernetes",
         "ClusterAliases": {},
         "Metrics": null,
         "XDSUpdater": null,
         "MeshNetworksWatcher": null,
         "MeshWatcher": null,
         "KubernetesAPIQPS": 80,
         "KubernetesAPIBurst": 160,
         "SyncTimeout": 0,
         "DiscoveryNamespacesFilter": null,
         "ConfigController": null,
         "ConfigCluster": false
      },
      "ClusterRegistriesNamespace": "istio-system",
      "KubeConfig": "",
      "DistributionCacheRetention": 60000000000,
      "DistributionTrackingEnabled": false
   },
   "CtrlZOptions": {
      "Port": 9876,
      "Address": "localhost"
   },
   "KeepaliveOptions": {
      "Time": 30000000000,
      "Timeout": 10000000000,
      "MaxServerConnectionAge": 1800000000000,
      "MaxServerConnectionAgeGrace": 10000000000
   },
   "ShutdownDuration": 10000000000,
   "JwtRule": ""
}
2024-07-25T20:12:52.342101Z	info	initializing mesh handlers
2024-07-25T20:12:52.342169Z	info	model	reloading network gateways
2024-07-25T20:12:52.342183Z	info	creating CA and initializing public key
2024-07-25T20:12:52.342203Z	info	Using istiod file format for signing ca files
2024-07-25T20:12:52.342216Z	info	Use self-signed certificate as the CA certificate
2024-07-25T20:12:52.588321Z	info	pkica	Load signing key and cert from existing secret istio-system/istio-ca-secret
2024-07-25T20:12:52.589959Z	info	pkica	Set secret name for self-signed CA cert rotator to istio-ca-secret
2024-07-25T20:12:52.589979Z	info	pkica	Using existing public key: -----BEGIN CERTIFICATE-----
MIIC/TCCAeWgAwIBAgIRAJ+arN6JF5YnbytSHvUdMIswDQYJKoZIhvcNAQELBQAw
GDEWMBQGA1UEChMNY2x1c3Rlci5sb2NhbDAeFw0yNDA3MTYwNTE4MzdaFw0zNDA3
MTQwNTE4MzdaMBgxFjAUBgNVBAoTDWNsdXN0ZXIubG9jYWwwggEiMA0GCSqGSIb3
DQEBAQUAA4IBDwAwggEKAoIBAQC2KW8DwTqUAn6oyJZYXb3abOhfxHPYXIV7gaj9
kR0Mgpfzn6ve0Wc1OdG9Hv9MCnk8rP0S2mM4/1thIIFtqp+N5pAJJJGmssyQEc5Q
bfkLdssaHAHzODs40+SrNmSkva8IGh7MDzMxtbYAtsGCf++1pniAEJlH49riO8kl
xuZFixTwkCu9h+IdT08E84SlLcuRVkoQ+wk0eNLs5m6TjLpO1DvMzDZRyMc7VC3B
ogWn8Z1yYCVRYJf6zVVf1aswSDlWViTn5NIF1NNqU940WJ8ibTNPo8bE/EBRrgOR
ZS+K/zpLhPzTlpThhSlSvYjRzoBkcmVnthSQInMk9n8BXFQ5AgMBAAGjQjBAMA4G
A1UdDwEB/wQEAwICBDAPBgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBQvieTEXxns
aw/2Cy/rXfDvDSLtfzANBgkqhkiG9w0BAQsFAAOCAQEAb5/O6ASeLkoSGYHhv0H2
zJAfs35/39MXFChphw5boduUoVuqsTFR7ZnMypq8WXcSCBeVuo46ojHfde0FzH0h
3PK9jrMdcXIenjWmdpWPbhCz6UhcVvEdyCcvrFh3kXJm8s2jAmYDGCAtJuLA6EEf
gWfsXFBl8mb13hLG+MkjSnGB5xV9M4p2qKUEXo/49vo/p5KbNQ5YVu8YVy36IwfX
Ky7DBmQsCdlKta4b/NWMLIyPULtHTDEc2Ycwix2iOHaUEX1HNOMl3RTwJZDSxA6r
4SfWVLVolC1ien+6vCDbwl8ivYxpc0lsZEN0ISlIbTU3bO5kpOE4LdGtwpFbd4P0
0g==
-----END CERTIFICATE-----

2024-07-25T20:12:52.590014Z	info	rootcertrotator	Set up back off time 33m30s to start rotator.
2024-07-25T20:12:52.590041Z	info	initializing controllers
2024-07-25T20:12:52.590146Z	info	rootcertrotator	Jitter is enabled, wait 33m30s before starting root cert rotator.
2024-07-25T20:12:52.590775Z	info	Adding Kubernetes registry adapter
2024-07-25T20:12:52.590832Z	info	Discover server subject alt names: [istio-pilot.istio-system.svc istiod-remote.istio-system.svc istiod.istio-system.svc]
2024-07-25T20:12:52.590880Z	info	initializing Istiod DNS certificates host: istiod.istio-system.svc, custom host:
2024-07-25T20:12:53.242039Z	info	Generating istiod-signed cert for [istio-pilot.istio-system.svc istiod-remote.istio-system.svc istiod.istio-system.svc]:
 -----BEGIN CERTIFICATE-----
MIIDaTCCAlGgAwIBAgIQSp8mpy2dhDmhnNuHRVfBqDANBgkqhkiG9w0BAQsFADAY
MRYwFAYDVQQKEw1jbHVzdGVyLmxvY2FsMB4XDTI0MDcyNTIwMTA1M1oXDTM0MDcy
MzIwMTI1M1owADCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALGoHhwE
+Hl2FQ3rewtWFEWZsEJBBDXPL6S4nq5V7IK3Ev69F3zwT2YWNbKai03zpOoH8cQQ
bDNhdBcZs8iBbJU6qSxsAYho1fDrvTu1E0FWpjfH5XeuDFDmn+QlWXVTOU30rGgY
zznoA67EaBnxj9NbCXlb0Bk9wfHoEkhp69bfwq0/zznIrTirO2876Glaw+7bDaQG
T2WHZgFZ/81tFaKVRmkLHw5BfJNwl0R8tCeFzDbKaT9a83c9FI2icEHKV6R+eGOI
OIHPT5tjByg3C5+vGCAf3+qQUXy+HATd+PG9vqUVc6ZINOJjRSZgKYsz/3CqNdyS
oxATSLaszeBttfUCAwEAAaOBxjCBwzAOBgNVHQ8BAf8EBAMCBaAwHQYDVR0lBBYw
FAYIKwYBBQUHAwEGCCsGAQUFBwMCMAwGA1UdEwEB/wQCMAAwHwYDVR0jBBgwFoAU
L4nkxF8Z7GsP9gsv613w7w0i7X8wYwYDVR0RAQH/BFkwV4IcaXN0aW8tcGlsb3Qu
aXN0aW8tc3lzdGVtLnN2Y4IeaXN0aW9kLXJlbW90ZS5pc3Rpby1zeXN0ZW0uc3Zj
ghdpc3Rpb2QuaXN0aW8tc3lzdGVtLnN2YzANBgkqhkiG9w0BAQsFAAOCAQEAQxN4
iwotxPmBjhQJDSHnYWR9hS16bSCIokrn4OriVBCdTT+lmhS0/j0X3RfwcDQI0id9
tXcRvh1c0IpkFr9lAxP8HlNhfKYibOSIGFlEQNJyDV0xmz53ckSgRyT1z0866+F0
5/+Xz9pyxiiI/hu2hvF1wkOso9rrEfmsyPaB6voIEn4v/9vLFwI6GxLQhxxtBXvS
/bP31/G2OSeLRic375tDmZ0IgZRFBOj5kLDreasxVtJ4pSY/KzmWAYHsVhfI/ded
1sjwWF08qUcSUT6/bm1Ep6Pzwp/xDg/sA6tS74xCfvOpNBcAHRC0NxQUUK8oAYvj
/kV3JZ09TesB24NIdg==
-----END CERTIFICATE-----

2024-07-25T20:12:53.242113Z	info	Using istiod file format for signing ca files
2024-07-25T20:12:53.242128Z	info	Use istio-generated cacerts at etc/cacerts/ca-key.pem or istio-ca-secret
2024-07-25T20:12:53.242683Z	info	x509 cert - Issuer: "O=cluster.local", Subject: "", SN: 4a9f26a72d9d8439a19cdb874557c1a8, NotBefore: "2024-07-25T20:10:53Z", NotAfter: "2034-07-23T20:12:53Z"
2024-07-25T20:12:53.242694Z	info	Istiod certificates are reloaded
2024-07-25T20:12:53.242792Z	info	spiffe	Added 1 certs to trust domain cluster.local in peer cert verifier
2024-07-25T20:12:53.242801Z	info	initializing secure discovery service
2024-07-25T20:12:53.242850Z	info	initializing secure webhook server for istiod webhooks
2024-07-25T20:12:53.282788Z	info	initializing sidecar injector
2024-07-25T20:12:53.302629Z	info	initializing config validator
2024-07-25T20:12:53.302666Z	info	initializing registry event handlers
2024-07-25T20:12:53.302713Z	info	starting discovery service
2024-07-25T20:12:53.304870Z	info	Starting Istiod Server with primary cluster Kubernetes
2024-07-25T20:12:53.304971Z	info	ControlZ available at 127.0.0.1:9876
2024-07-25T20:12:53.307976Z	info	initializing Kubernetes credential reader for cluster Kubernetes
2024-07-25T20:12:53.308102Z	info	kube	Initializing Kubernetes service registry "Kubernetes"
2024-07-25T20:12:53.308738Z	info	Starting multicluster remote secrets controller
2024-07-25T20:12:53.308919Z	info	status	Starting status manager
2024-07-25T20:12:53.309067Z	info	kube	Starting Pilot K8S CRD controller	controller=crd-controller
2024-07-25T20:12:53.309111Z	info	Starting validation controller
2024-07-25T20:12:53.309125Z	info	kube	controller "networking.istio.io/v1alpha3/Sidecar" is syncing...	controller=crd-controller
2024-07-25T20:12:53.309179Z	info	Starting ADS server
2024-07-25T20:12:53.309214Z	info	klog	attempting to acquire leader lease istio-system/istio-gateway-deployment-default...
2024-07-25T20:12:53.309225Z	info	Starting IstioD CA
2024-07-25T20:12:53.309243Z	info	JWT policy is third-party-jwt
2024-07-25T20:12:53.309241Z	info	controllers	starting	controller=healthcheck
2024-07-25T20:12:53.309288Z	info	controllers	starting	controller=unregister_workloadentry
2024-07-25T20:12:53.309280Z	info	controllers	starting	controller=auto-register existing connections
2024-07-25T20:12:53.309329Z	info	klog	attempting to acquire leader lease istio-system/istio-gateway-status-leader...
2024-07-25T20:12:53.309388Z	info	klog	attempting to acquire leader lease istio-system/istio-leader...
2024-07-25T20:12:53.309435Z	info	Istiod CA has started
2024-07-25T20:12:53.309532Z	info	cluster "Kubernetes" kube client started
2024-07-25T20:12:53.311549Z	info	kube	controller "gateway.networking.k8s.io/v1beta1/Gateway" is syncing...	controller=crd-controller
2024-07-25T20:12:53.314969Z	info	multicluster remote secrets controller cache synced in 6.240522ms
2024-07-25T20:12:53.314988Z	info	controllers	starting	controller=multicluster secret
2024-07-25T20:12:53.315575Z	info	controllers	starting	controller=webhook patcher
2024-07-25T20:12:53.315706Z	info	controllers	starting	controller=default revision
2024-07-25T20:12:53.315827Z	info	controllers	starting	controller=default revision
2024-07-25T20:12:53.315869Z	info	kube	controller "networking.istio.io/v1alpha3/Gateway" is syncing...	controller=crd-controller
2024-07-25T20:12:53.315885Z	info	controllers	starting	controller=validation
2024-07-25T20:12:53.316015Z	info	controllers	starting	controller=default revision
2024-07-25T20:12:53.316025Z	info	controllers	starting	controller=configmap istio-sidecar-injector
2024-07-25T20:12:53.319393Z	info	validationController	Not ready to switch validation to fail-closed: dummy invalid rejected for the wrong reason: Internal error occurred: failed calling webhook "rev.validation.istio.io": failed to call webhook: Post "https://istiod.istio-system.svc:443/validate?timeout=10s": dial tcp 10.97.219.77:443: connect: connection refused
2024-07-25T20:12:53.324666Z	info	controllers	starting	controller=ingress
2024-07-25T20:12:53.324675Z	info	controllers	starting	controller=crd watcher
2024-07-25T20:12:53.324705Z	info	kube	controller "gateway.networking.k8s.io/v1beta1/ReferenceGrant" is syncing...	controller=crd-controller
2024-07-25T20:12:53.324761Z	info	authorizationpolicies.security.istio.io is now ready, building client
2024-07-25T20:12:53.324801Z	info	destinationrules.networking.istio.io is now ready, building client
2024-07-25T20:12:53.324831Z	info	envoyfilters.networking.istio.io is now ready, building client
2024-07-25T20:12:53.324859Z	info	gateways.networking.istio.io is now ready, building client
2024-07-25T20:12:53.324900Z	info	peerauthentications.security.istio.io is now ready, building client
2024-07-25T20:12:53.324932Z	info	proxyconfigs.networking.istio.io is now ready, building client
2024-07-25T20:12:53.324966Z	info	requestauthentications.security.istio.io is now ready, building client
2024-07-25T20:12:53.324993Z	info	serviceentries.networking.istio.io is now ready, building client
2024-07-25T20:12:53.325029Z	info	sidecars.networking.istio.io is now ready, building client
2024-07-25T20:12:53.325102Z	info	telemetries.telemetry.istio.io is now ready, building client
2024-07-25T20:12:53.325199Z	info	virtualservices.networking.istio.io is now ready, building client
2024-07-25T20:12:53.325257Z	info	wasmplugins.extensions.istio.io is now ready, building client
2024-07-25T20:12:53.325333Z	info	workloadentries.networking.istio.io is now ready, building client
2024-07-25T20:12:53.325378Z	info	workloadgroups.networking.istio.io is now ready, building client
2024-07-25T20:12:53.341078Z	info	kube	Pilot K8S CRD controller synced in 32.012011ms	controller=crd-controller
2024-07-25T20:12:53.373445Z	info	kube	kube controller for Kubernetes synced after 64.430085ms
2024-07-25T20:12:53.374272Z	info	model	Full push, new service kasten-io/dashboardbff-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374351Z	info	model	Full push, new service kasten-io/executor-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374399Z	info	model	Full push, new service kasten-io/frontend-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374460Z	info	model	Incremental push, service jobs-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.374489Z	info	model	Incremental push, service logging-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.374517Z	info	model	Incremental push, service prometheus-server.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.374558Z	info	model	Full push, new service kasten-io/state-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374603Z	info	model	Full push, new service kasten-io/controllermanager-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374659Z	info	model	Full push, new service kasten-io/crypto-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374690Z	info	model	Incremental push, service k10-grafana.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.374712Z	info	model	Incremental push, service prometheus-server-exp.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.374758Z	info	model	Full push, new service kasten-io/auth-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374813Z	info	model	Full push, new service kasten-io/gateway.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374868Z	info	model	Full push, new service kasten-io/kanister-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374898Z	info	model	Incremental push, service metering-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.374958Z	info	model	Full push, new service kasten-io/aggregatedapis-svc.kasten-io.svc.cluster.local
2024-07-25T20:12:53.374999Z	info	model	Incremental push, service catalog-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.375036Z	info	model	Full push, new service kasten-io/gateway-admin.kasten-io.svc.cluster.local
2024-07-25T20:12:53.375392Z	info	model	Full push, new service kube-system/kube-dns.kube-system.svc.cluster.local
2024-07-25T20:12:53.375473Z	info	model	Full push, new service kube-system/metrics-server.kube-system.svc.cluster.local
2024-07-25T20:12:53.375652Z	info	model	Full push, new service default/bufferbloater-svc-a.default.svc.cluster.local
2024-07-25T20:12:53.375715Z	info	model	Full push, new service default/bufferbloater-svc-b.default.svc.cluster.local
2024-07-25T20:12:53.375763Z	info	model	Full push, new service default/bufferbloater-svc-c.default.svc.cluster.local
2024-07-25T20:12:53.375813Z	info	model	Full push, new service default/kubernetes.default.svc.cluster.local
2024-07-25T20:12:53.376089Z	info	model	Full push, new service istio-system/istio-ingressgateway.istio-system.svc.cluster.local
2024-07-25T20:12:53.376146Z	info	model	Incremental push, service istiod.istio-system.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376394Z	info	model	Incremental push, service istiod.istio-system.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376487Z	info	model	Incremental push, service catalog-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376705Z	info	model	Incremental push, service jobs-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376738Z	info	model	Incremental push, service k10-grafana.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376795Z	info	model	Incremental push, service logging-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376827Z	info	model	Incremental push, service metering-svc.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376851Z	info	model	Incremental push, service prometheus-server-exp.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.376874Z	info	model	Incremental push, service prometheus-server.kasten-io.svc.cluster.local at shard Kubernetes/Kubernetes has no endpoints
2024-07-25T20:12:53.441852Z	info	Waiting for caches to be synced
2024-07-25T20:12:53.441895Z	info	All controller caches have been synced up in 43.353µs
2024-07-25T20:12:53.441899Z	info	kube	joining leader-election for istio-namespace-controller-election in istio-system on cluster Kubernetes
2024-07-25T20:12:53.442055Z	info	klog	attempting to acquire leader lease istio-system/istio-namespace-controller-election...
2024-07-25T20:12:53.444088Z	info	controllers	starting	controller=default revision
2024-07-25T20:12:53.477840Z	info	ads	Push debounce stable[1] 103 for config Secret/kasten-io/k10-license and 42 more configs: 100.026396ms since last change, 163.533964ms since last push, full=true
2024-07-25T20:12:53.478586Z	info	ads	XDS: Pushing Services:26 ConnectedEndpoints:0 Version:2024-07-25T20:12:53Z/1
2024-07-25T20:12:53.505052Z	info	ads	All caches have been synced up in 1.239931526s, marking server ready
2024-07-25T20:12:53.505268Z	info	starting gRPC discovery service at [::]:15010
2024-07-25T20:12:53.505316Z	info	starting webhook service at [::]:15017
2024-07-25T20:12:53.505366Z	info	starting secure gRPC discovery service at [::]:15012
2024-07-25T20:12:53.801949Z	info	validationController	Successfully updated validatingwebhookconfiguration istio-validator-istio-system (failurePolicy=Ignore,resourceVersion=1857948)
2024-07-25T20:12:53.801995Z	error	controllers	error handling istio-validator-istio-system, retrying (retry count: 1): webhook is not ready, retry	controller=validation
2024-07-25T20:12:54.361819Z	info	klog	successfully acquired lease istio-system/istio-gateway-status-leader
2024-07-25T20:12:54.361864Z	info	klog	successfully acquired lease istio-system/istio-gateway-deployment-default
2024-07-25T20:12:54.361957Z	info	leader election lock obtained: istio-gateway-status-leader
2024-07-25T20:12:54.361988Z	info	klog	successfully acquired lease istio-system/istio-leader
2024-07-25T20:12:54.362007Z	info	Starting gateway status writer
2024-07-25T20:12:54.362082Z	info	leader election lock obtained: istio-gateway-deployment-default
2024-07-25T20:12:54.362087Z	info	model	Full push, new service istio-system/istiod.istio-system.svc.cluster.local
2024-07-25T20:12:54.362101Z	info	klog	successfully acquired lease istio-system/istio-namespace-controller-election
2024-07-25T20:12:54.362122Z	info	leader election lock obtained: istio-leader
2024-07-25T20:12:54.362210Z	info	leader election lock obtained: istio-namespace-controller-election
2024-07-25T20:12:54.362237Z	info	kube	starting namespace controller for cluster Kubernetes
2024-07-25T20:12:54.364200Z	info	validationController	Not ready to switch validation to fail-closed: dummy invalid config not rejected
2024-07-25T20:12:54.364640Z	info	Starting ingress controller
2024-07-25T20:12:54.364658Z	info	controllers	starting	controller=ingress status
2024-07-25T20:12:54.462719Z	info	ads	Push debounce stable[2] 2 for reason global:1 and endpoint:1: 100.548946ms since last change, 100.656796ms since last push, full=true
2024-07-25T20:12:54.462790Z	info	controllers	starting	controller=namespace controller
2024-07-25T20:12:54.463327Z	info	ads	XDS: Pushing Services:26 ConnectedEndpoints:0 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:12:54.962903Z	info	validationController	Successfully updated validatingwebhookconfiguration istiod-default-validator (failurePolicy=Ignore,resourceVersion=1857962)
2024-07-25T20:12:54.962976Z	error	controllers	error handling istiod-default-validator, retrying (retry count: 1): webhook is not ready, retry	controller=validation
2024-07-25T20:12:55.589269Z	info	ads	Push debounce stable[3] 1 for config ServiceEntry/istio-system/istiod.istio-system.svc.cluster.local: 100.262673ms since last change, 100.262382ms since last push, full=false
2024-07-25T20:12:55.589368Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:0 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:12:55.883611Z	info	validationController	Not ready to switch validation to fail-closed: dummy invalid config not rejected
2024-07-25T20:12:55.883647Z	info	validationController	validatingwebhookconfiguration istio-validator-istio-system (failurePolicy=Ignore, resourceVersion=1857948) is up-to-date. No change required.
2024-07-25T20:12:55.883668Z	error	controllers	error handling istio-validator-istio-system, retrying (retry count: 2): webhook is not ready, retry	controller=validation
2024-07-25T20:12:55.892521Z	info	validationServer	configuration is invalid: "internal.istio.io/webhook-always-reject" annotation found, rejecting (dry run)
2024-07-25T20:12:55.893710Z	info	validationController	Endpoint successfully rejected invalid config. Switching to fail-close.
2024-07-25T20:12:56.156565Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-bcwvh.istio-system-1
2024-07-25T20:12:56.161555Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-bcwvh.istio-system resources:48 size:51.3kB cached:0/47
2024-07-25T20:12:56.201767Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-bcwvh.istio-system resources:47 size:7.1kB empty:15 cached:0/47
2024-07-25T20:12:56.253053Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system-2
2024-07-25T20:12:56.256776Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:48 size:51.3kB cached:0/47
2024-07-25T20:12:56.296974Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:47 size:7.1kB empty:15 cached:0/47
2024-07-25T20:12:56.859579Z	info	validationController	Successfully updated validatingwebhookconfiguration istiod-default-validator (failurePolicy=Fail,resourceVersion=1857972)
2024-07-25T20:12:57.316251Z	info	validationController	Successfully updated validatingwebhookconfiguration istio-validator-istio-system (failurePolicy=Fail,resourceVersion=1857976)
2024-07-25T20:12:57.316351Z	info	validationController	validatingwebhookconfiguration istiod-default-validator (failurePolicy=Fail, resourceVersion=1857972) is up-to-date. No change required.
2024-07-25T20:12:57.316403Z	info	validationController	validatingwebhookconfiguration istio-validator-istio-system (failurePolicy=Fail, resourceVersion=1857976) is up-to-date. No change required.
2024-07-25T20:12:57.387663Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system-3
2024-07-25T20:12:57.390423Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:48 size:51.3kB cached:0/47
2024-07-25T20:12:57.429944Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:47 size:7.1kB empty:15 cached:0/47
2024-07-25T20:12:57.883992Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system-4
2024-07-25T20:12:57.886675Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:48 size:51.3kB cached:0/47
2024-07-25T20:12:57.927240Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:47 size:7.1kB empty:15 cached:0/47
2024-07-25T20:12:58.711764Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:1 size:2.0kB
2024-07-25T20:12:58.718529Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:12:58.893399Z	info	ads	Push debounce stable[4] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.261318ms since last change, 100.261014ms since last push, full=false
2024-07-25T20:12:58.893476Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:4 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:12:58.973748Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:48 size:51.3kB cached:0/47
2024-07-25T20:12:58.975407Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:47 size:7.1kB empty:12 cached:3/47
2024-07-25T20:12:58.975605Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:1 size:2.0kB
2024-07-25T20:12:58.975855Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-prkhn.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:12:59.093175Z	info	ads	ADS: new connection for node:bufferbloater-svc-a-us-west-1-7f4ff47554-2kjr2.default-5
2024-07-25T20:12:59.095914Z	info	ads	CDS: PUSH request for node:bufferbloater-svc-a-us-west-1-7f4ff47554-2kjr2.default resources:51 size:54.1kB cached:0/47
2024-07-25T20:12:59.097086Z	info	ads	EDS: PUSH request for node:bufferbloater-svc-a-us-west-1-7f4ff47554-2kjr2.default resources:47 size:7.5kB empty:12 cached:0/47
2024-07-25T20:12:59.099210Z	info	ads	LDS: PUSH request for node:bufferbloater-svc-a-us-west-1-7f4ff47554-2kjr2.default resources:27 size:64.6kB
2024-07-25T20:12:59.100154Z	info	ads	RDS: PUSH request for node:bufferbloater-svc-a-us-west-1-7f4ff47554-2kjr2.default resources:19 size:22.5kB cached:0/19
2024-07-25T20:12:59.132684Z	info	ads	EDS: PUSH request for node:bufferbloater-svc-a-us-west-1-7f4ff47554-2kjr2.default resources:47 size:7.5kB empty:12 cached:0/47
2024-07-25T20:12:59.188703Z	info	ads	Push debounce stable[5] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.906771ms since last change, 100.906602ms since last push, full=false
2024-07-25T20:12:59.188768Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:5 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:12:59.537630Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-bcwvh.istio-system resources:1 size:2.0kB
2024-07-25T20:12:59.541925Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-bcwvh.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:12:59.668326Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system-6
2024-07-25T20:12:59.669015Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:12:59.708754Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:47 size:7.5kB empty:0 cached:47/47
2024-07-25T20:12:59.770522Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:1 size:2.0kB
2024-07-25T20:12:59.774954Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:00.363072Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:1 size:2.0kB
2024-07-25T20:13:00.367395Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:00.906720Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:00.907245Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:47 size:7.5kB empty:0 cached:44/47
2024-07-25T20:13:00.907461Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:1 size:2.0kB
2024-07-25T20:13:00.907743Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-n4vqt.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:01.088987Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:01.089688Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:47 size:7.9kB empty:0 cached:44/47
2024-07-25T20:13:01.089927Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:1 size:2.0kB
2024-07-25T20:13:01.090978Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-pxjsh.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:01.102744Z	info	ads	Push debounce stable[6] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.05015ms since last change, 100.049981ms since last push, full=false
2024-07-25T20:13:01.102847Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:6 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:01.277581Z	info	ads	Push debounce stable[7] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.257261ms since last change, 100.257083ms since last push, full=false
2024-07-25T20:13:01.277661Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:6 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:02.066523Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system-7
2024-07-25T20:13:02.067211Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:02.106382Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:47 size:8.3kB empty:0 cached:47/47
2024-07-25T20:13:02.137227Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:1 size:2.0kB
2024-07-25T20:13:02.141412Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:02.251115Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:1 size:2.0kB
2024-07-25T20:13:02.255502Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:02.841662Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:02.841938Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:47 size:8.3kB empty:0 cached:47/47
2024-07-25T20:13:02.842138Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:1 size:2.0kB
2024-07-25T20:13:02.842357Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-8gt25.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:02.986246Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:02.987073Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:47 size:8.7kB empty:0 cached:44/47
2024-07-25T20:13:02.987260Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:1 size:2.0kB
2024-07-25T20:13:02.987471Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-sb664.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:02.991723Z	info	ads	Push debounce stable[8] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.732008ms since last change, 100.731842ms since last push, full=false
2024-07-25T20:13:02.991776Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:7 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:03.124937Z	info	ads	Push debounce stable[9] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.243231ms since last change, 100.243053ms since last push, full=false
2024-07-25T20:13:03.125018Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:7 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:03.310220Z	info	ads	Push Status: {
    "pilot_eds_no_instances": {
        "outbound|15021||istio-ingressgateway.istio-system.svc.cluster.local": {},
        "outbound|24224||logging-svc.kasten-io.svc.cluster.local": {},
        "outbound|24225||logging-svc.kasten-io.svc.cluster.local": {},
        "outbound|443||istio-ingressgateway.istio-system.svc.cluster.local": {},
        "outbound|8000||catalog-svc.kasten-io.svc.cluster.local": {},
        "outbound|8000||jobs-svc.kasten-io.svc.cluster.local": {},
        "outbound|8000||logging-svc.kasten-io.svc.cluster.local": {},
        "outbound|8000||metering-svc.kasten-io.svc.cluster.local": {},
        "outbound|8080|central|bufferbloater-svc-a.default.svc.cluster.local": {},
        "outbound|8080|east|bufferbloater-svc-a.default.svc.cluster.local": {},
        "outbound|8080|south|bufferbloater-svc-a.default.svc.cluster.local": {},
        "outbound|80||istio-ingressgateway.istio-system.svc.cluster.local": {},
        "outbound|80||k10-grafana.kasten-io.svc.cluster.local": {},
        "outbound|80||prometheus-server-exp.kasten-io.svc.cluster.local": {},
        "outbound|80||prometheus-server.kasten-io.svc.cluster.local": {}
    }
}
2024-07-25T20:13:03.541119Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system-8
2024-07-25T20:13:03.541718Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:03.580484Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:47 size:9.0kB empty:0 cached:47/47
2024-07-25T20:13:03.612564Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:1 size:2.0kB
2024-07-25T20:13:03.616590Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:04.823169Z	info	ads	ADS: "10.244.0.152:41840" istio-ingressgateway-86c4b5c6f-bcwvh.istio-system-1 terminated
2024-07-25T20:13:05.151973Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:05.152297Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:47 size:9.0kB empty:0 cached:47/47
2024-07-25T20:13:05.152516Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:1 size:2.0kB
2024-07-25T20:13:05.152838Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-z4w4v.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:05.300164Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system-9
2024-07-25T20:13:05.300610Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:48 size:51.3kB cached:47/47
2024-07-25T20:13:05.339737Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:47 size:9.0kB empty:0 cached:47/47
2024-07-25T20:13:05.370457Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:1 size:2.0kB
2024-07-25T20:13:05.374492Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:05.701851Z	info	ads	Push debounce stable[10] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.91913ms since last change, 100.91885ms since last push, full=false
2024-07-25T20:13:05.701920Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:8 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:05.714337Z	info	ads	ADS: new connection for node:bufferbloater-svc-b-us-west-1-67d68cc64f-2p7hx.default-10
2024-07-25T20:13:05.717245Z	info	ads	CDS: PUSH request for node:bufferbloater-svc-b-us-west-1-67d68cc64f-2p7hx.default resources:51 size:54.1kB cached:0/47
2024-07-25T20:13:05.718575Z	info	ads	EDS: PUSH request for node:bufferbloater-svc-b-us-west-1-67d68cc64f-2p7hx.default resources:47 size:9.4kB empty:12 cached:3/47
2024-07-25T20:13:05.720202Z	info	ads	LDS: PUSH request for node:bufferbloater-svc-b-us-west-1-67d68cc64f-2p7hx.default resources:27 size:64.6kB
2024-07-25T20:13:05.721257Z	info	ads	RDS: PUSH request for node:bufferbloater-svc-b-us-west-1-67d68cc64f-2p7hx.default resources:19 size:22.5kB cached:0/19
2024-07-25T20:13:05.752912Z	info	ads	EDS: PUSH request for node:bufferbloater-svc-b-us-west-1-67d68cc64f-2p7hx.default resources:47 size:9.4kB empty:12 cached:3/47
2024-07-25T20:13:06.600520Z	info	ads	Push debounce stable[11] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.955674ms since last change, 100.955516ms since last push, full=false
2024-07-25T20:13:06.600632Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:9 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:06.951425Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:06.951704Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:47 size:9.4kB empty:0 cached:47/47
2024-07-25T20:13:06.951878Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:1 size:2.0kB
2024-07-25T20:13:06.952077Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-qp4ql.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:07.092362Z	info	ads	Push debounce stable[12] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.266669ms since last change, 100.266152ms since last push, full=false
2024-07-25T20:13:07.092442Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:9 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:07.993635Z	info	ads	ADS: new connection for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system-11
2024-07-25T20:13:07.994289Z	info	ads	CDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:08.034589Z	info	ads	EDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:47 size:9.8kB empty:0 cached:47/47
2024-07-25T20:13:08.066255Z	info	ads	LDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:1 size:2.0kB
2024-07-25T20:13:08.070241Z	info	ads	RDS: PUSH request for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:08.962892Z	info	ads	CDS: PUSH for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:48 size:51.3kB cached:44/47
2024-07-25T20:13:08.963204Z	info	ads	EDS: PUSH for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:47 size:9.8kB empty:0 cached:47/47
2024-07-25T20:13:08.963381Z	info	ads	LDS: PUSH for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:1 size:2.0kB
2024-07-25T20:13:08.963663Z	info	ads	RDS: PUSH for node:istio-ingressgateway-86c4b5c6f-r7jhw.istio-system resources:1 size:2.6kB cached:0/0
2024-07-25T20:13:09.131752Z	info	ads	Push debounce stable[13] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.265426ms since last change, 100.26521ms since last push, full=false
2024-07-25T20:13:09.131849Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:10 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:12.523627Z	info	ads	ADS: "10.244.0.153:37564" istio-ingressgateway-86c4b5c6f-8gt25.istio-system-7 terminated
2024-07-25T20:13:13.713585Z	info	ads	Push debounce stable[14] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.756451ms since last change, 100.756289ms since last push, full=false
2024-07-25T20:13:13.713668Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:9 Version:2024-07-25T20:12:54Z/2
2024-07-25T20:13:14.170277Z	info	ads	ADS: new connection for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default-12
2024-07-25T20:13:14.172896Z	info	ads	CDS: PUSH request for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default resources:51 size:54.1kB cached:0/47
2024-07-25T20:13:14.173480Z	info	ads	EDS: PUSH request for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default resources:20 size:6.2kB empty:3 cached:3/20
2024-07-25T20:13:14.174904Z	info	ads	LDS: PUSH request for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default resources:27 size:64.6kB
2024-07-25T20:13:14.175402Z	info	ads	RDS: PUSH request for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default resources:6 size:10.3kB cached:0/6
2024-07-25T20:13:14.243519Z	info	ads	EDS: PUSH request for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default resources:47 size:9.8kB empty:12 cached:3/47
2024-07-25T20:13:14.300329Z	info	ads	RDS: PUSH request for node:bufferbloater-svc-c-us-west-1-65c9ddd684-fkplx.default resources:19 size:22.5kB cached:0/19
2024-07-25T20:13:19.641742Z	info	ads	ADS: "10.244.0.154:56510" istio-ingressgateway-86c4b5c6f-r7jhw.istio-system-11 terminated
2024-07-25T20:13:20.905401Z	info	ads	Push debounce stable[15] 1 for config ServiceEntry/istio-system/istio-ingressgateway.istio-system.svc.cluster.local: 100.269744ms since last change, 100.269455ms since last push, full=false
2024-07-25T20:13:20.905502Z	info	ads	XDS: Incremental Pushing ConnectedEndpoints:9 Version:2024-07-25T20:12:54Z/2
```

Basically, a bunch of network conneciton failure.

Okay, so deployment description is not enough but pod log is too much. Let's check kubectl describe pod

```bash
$ k describe pod istiod-7fb964cc7b-7r4z7 -n istio-system

Name:             istiod-7fb964cc7b-7r4z7
Namespace:        istio-system
Priority:         0
Service Account:  istiod
Node:             node0.bufferbloater.istio-pg0.clemson.cloudlab.us/130.127.133.92
Start Time:       Thu, 25 Jul 2024 21:22:31 +0000
Labels:           app=istiod
                  install.operator.istio.io/owning-resource=unknown
                  istio=pilot
                  istio.io/rev=default
                  operator.istio.io/component=Pilot
                  pod-template-hash=7fb964cc7b
                  sidecar.istio.io/inject=false
Annotations:      ambient.istio.io/redirection: disabled
                  kubectl.kubernetes.io/restartedAt: 2024-07-25T21:10:34Z
                  prometheus.io/port: 15014
                  prometheus.io/scrape: true
                  sidecar.istio.io/inject: false
Status:           Failed
Reason:           Evicted
Message:          The node was low on resource: ephemeral-storage. Threshold quantity: 10057513974, available: 9670764Ki.
IP:               10.244.0.253
IPs:
  IP:           10.244.0.253
Controlled By:  ReplicaSet/istiod-7fb964cc7b
Containers:
  discovery:
    Container ID:
    Image:         docker.io/istio/pilot:1.20.3
    Image ID:
    Ports:         8080/TCP, 15010/TCP, 15017/TCP
    Host Ports:    0/TCP, 0/TCP, 0/TCP
    Args:
      discovery
      --monitoringAddr=:15014
      --log_output_level=default:info
      --domain
      cluster.local
      --keepaliveMaxServerConnectionAge
      30m
    State:          Terminated
      Reason:       ContainerStatusUnknown
      Message:      The container could not be located when the pod was terminated
      Exit Code:    137
      Started:      Mon, 01 Jan 0001 00:00:00 +0000
      Finished:     Mon, 01 Jan 0001 00:00:00 +0000
    Last State:     Terminated
      Reason:       ContainerStatusUnknown
      Message:      The container could not be located when the pod was deleted.  The container used to be Running
      Exit Code:    137
      Started:      Mon, 01 Jan 0001 00:00:00 +0000
      Finished:     Mon, 01 Jan 0001 00:00:00 +0000
    Ready:          False
    Restart Count:  1
    Requests:
      cpu:      500m
      memory:   2Gi
    Readiness:  http-get http://:8080/ready delay=1s timeout=5s period=3s #success=1 #failure=3
    Environment:
      REVISION:               default
      JWT_POLICY:             third-party-jwt
      PILOT_CERT_PROVIDER:    istiod
      POD_NAME:               istiod-7fb964cc7b-7r4z7 (v1:metadata.name)
      POD_NAMESPACE:          istio-system (v1:metadata.namespace)
      SERVICE_ACCOUNT:         (v1:spec.serviceAccountName)
      KUBECONFIG:             /var/run/secrets/remote/config
      PILOT_TRACE_SAMPLING:   1
      PILOT_ENABLE_ANALYSIS:  false
      CLUSTER_ID:             Kubernetes
      GOMEMLIMIT:             node allocatable (limits.memory)
      GOMAXPROCS:             node allocatable (limits.cpu)
      PLATFORM:
    Mounts:
      /etc/cacerts from cacerts (ro)
      /var/run/secrets/istio-dns from local-certs (rw)
      /var/run/secrets/istiod/ca from istio-csr-ca-configmap (ro)
      /var/run/secrets/istiod/tls from istio-csr-dns-cert (ro)
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-2rqr8 (ro)
      /var/run/secrets/remote from istio-kubeconfig (ro)
      /var/run/secrets/tokens from istio-token (ro)
Conditions:
  Type               Status
  DisruptionTarget   True
  Initialized        True
  Ready              False
  ContainersReady    False
  PodScheduled       True
Volumes:
  local-certs:
    Type:       EmptyDir (a temporary directory that shares a pod's lifetime)
    Medium:     Memory
    SizeLimit:  <unset>
  istio-token:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  43200
  cacerts:
    Type:        Secret (a volume populated by a Secret)
    SecretName:  cacerts
    Optional:    true
  istio-kubeconfig:
    Type:        Secret (a volume populated by a Secret)
    SecretName:  istio-kubeconfig
    Optional:    true
  istio-csr-dns-cert:
    Type:        Secret (a volume populated by a Secret)
    SecretName:  istiod-tls
    Optional:    true
  istio-csr-ca-configmap:
    Type:      ConfigMap (a volume populated by a ConfigMap)
    Name:      istio-ca-root-cert
    Optional:  true
  kube-api-access-2rqr8:
    Type:                    Projected (a volume that contains injected data from multiple sources)
    TokenExpirationSeconds:  3607
    ConfigMapName:           kube-root-ca.crt
    ConfigMapOptional:       <nil>
    DownwardAPI:             true
QoS Class:                   Burstable
Node-Selectors:              <none>
Tolerations:                 node-role.kubernetes.io/control-plane:NoSchedule op=Exists
                             node.kubernetes.io/not-ready:NoExecute op=Exists for 300s
                             node.kubernetes.io/unreachable:NoExecute op=Exists for 300s
Events:
  Type     Reason               Age   From               Message
  ----     ------               ----  ----               -------
  Warning  FailedScheduling     17m   default-scheduler  0/4 nodes are available: 1 node(s) had untolerated taint {node.kubernetes.io/disk-pressure: }, 3 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 4 Preemption is not helpful for scheduling..
  Warning  FailedScheduling     12m   default-scheduler  0/4 nodes are available: 1 node(s) had untolerated taint {node.kubernetes.io/disk-pressure: }, 3 node(s) didn't match Pod's node affinity/selector. preemption: 0/4 nodes are available: 4 Preemption is not helpful for scheduling..
  Normal   Scheduled            10m   default-scheduler  Successfully assigned istio-system/istiod-7fb964cc7b-7r4z7 to node0.bufferbloater.istio-pg0.clemson.cloudlab.us
  Normal   Pulling              10m   kubelet            Pulling image "docker.io/istio/pilot:1.20.3"
  Warning  Evicted              10m   kubelet            The node was low on resource: ephemeral-storage. Threshold quantity: 10057513974, available: 9670764Ki.
  Normal   Pulled               10m   kubelet            Successfully pulled image "docker.io/istio/pilot:1.20.3" in 5.863s (17.44s including waiting)
  Normal   Created              10m   kubelet            Created container discovery
  Normal   Started              10m   kubelet            Started container discovery
  Normal   Killing              10m   kubelet            Stopping container discovery
  Warning  ExceededGracePeriod  10m   kubelet            Container runtime did not kill the pod within specified grace period.
```

Nice, it is here. The istiod pod was evicted due to low ephemeral storage on the node. and istio-ingressgateway pods were not able to connect to istiod because the only istiod pod was unavailable. Istio-ingressgateway pods were not ready and terminated considered unhealthy pod and replicaset recreated the pods, and it repeats. The root cause was the ephemeral storage issue on the k8s node where istiod was running.

To confirm, I checked the node 0 status. It shows up as a healthy node (STATUS: ready) but no pod can be scheduled anymore due to disk pressure. It looks weird since I doubt it is what the user expects. This is critical information that affects the pod schedulability. This issue should be shown some where more than in kubectl describe node.

```bash
gangmuk@node0:~$ kubectl describe node node0.bufferbloater.istio-pg0.clemson.cloudlab.us
Name:               node0.bufferbloater.istio-pg0.clemson.cloudlab.us
Roles:              control-plane
Labels:             beta.kubernetes.io/arch=amd64
                    beta.kubernetes.io/os=linux
                    kubernetes.io/arch=amd64
                    kubernetes.io/hostname=node0.bufferbloater.istio-pg0.clemson.cloudlab.us
                    
CreationTimestamp:  Tue, 16 Jul 2024 04:59:24 +0000
Taints:             node-role.kubernetes.io/control-plane:NoSchedule
                    node.kubernetes.io/disk-pressure:NoSchedule
Unschedulable:      false
Conditions:
  Type                 Status  LastHeartbeatTime                 LastTransitionTime                Reason                       Message
  ----                 ------  -----------------                 ------------------                ------                       -------
  NetworkUnavailable   False   Tue, 16 Jul 2024 04:59:58 +0000   Tue, 16 Jul 2024 04:59:58 +0000   FlannelIsUp                  Flannel is running on this node
  MemoryPressure       False   Thu, 25 Jul 2024 21:47:46 +0000   Tue, 16 Jul 2024 04:59:22 +0000   KubeletHasSufficientMemory   kubelet has sufficient memory available
  **DiskPressure         True    Thu, 25 Jul 2024 21:47:46 +0000   Thu, 25 Jul 2024 21:45:12 +0000   KubeletHasDiskPressure       kubelet has disk pressure**
  PIDPressure          False   Thu, 25 Jul 2024 21:47:46 +0000   Tue, 16 Jul 2024 04:59:22 +0000   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready                True    Thu, 25 Jul 2024 21:47:46 +0000   Tue, 16 Jul 2024 04:59:55 +0000   KubeletReady                 kubelet is posting ready status. AppArmor enabled
Addresses:
  InternalIP:  130.127.133.92
  Hostname:    node0.bufferbloater.istio-pg0.clemson.cloudlab.us
Capacity:
  cpu:                40
  ephemeral-storage:  65478604Ki
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             257841Mi
  pods:               110
Allocatable:
  cpu:                40
  ephemeral-storage:  60345081347
  hugepages-1Gi:      0
  hugepages-2Mi:      0
  memory:             257741Mi
  pods:               110

Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests    Limits
  --------           --------    ------
  cpu                950m (2%)   0 (0%)
  memory             290Mi (0%)  340Mi (0%)
  ephemeral-storage  0 (0%)      0 (0%)
  hugepages-1Gi      0 (0%)      0 (0%)
  hugepages-2Mi      0 (0%)      0 (0%)
Events:
  Type     Reason                 Age                    From     Message
  ----     ------                 ----                   ----     -------
  Normal   NodeHasNoDiskPressure  50m (x19 over 3h8m)    kubelet  Node node0.bufferbloater.istio-pg0.clemson.cloudlab.us status is now: NodeHasNoDiskPressure
  Warning  EvictionThresholdMet   10m (x336 over 3h15m)  kubelet  Attempting to reclaim ephemeral-storage
  Warning  FreeDiskSpaceFailed    14s (x31 over 150m)    kubelet  (combined from similar events): Failed to garbage collect required amount of images. Attempted to free 3077055283 bytes, but only found 0 bytes eligible to free.
```

"**DiskPressure         True    Thu, 25 Jul 2024 21:47:46 +0000   Thu, 25 Jul 2024 21:45:12 +0000   KubeletHasDiskPressure       kubelet has disk pressure**"

"**Warning  EvictionThresholdMet   10m (x336 over 3h15m)  kubelet  Attempting to reclaim ephemeral-storage**"

"**Warning  FreeDiskSpaceFailed    14s (x31 over 150m)    kubelet  (combined from similar events): Failed to garbage collect required amount of images. Attempted to free 3077055283 bytes, but only found 0 bytes eligible to free.**"

FYI, I installed k8s in baremetal machine, so k8s node is a baremetal machine not a virtual machine.

And cloudlab machine disk partition where home dir is mounted is god damn small. why....

high disk space pressure.
```bash
gangmuk@node0:~$ df -h
Filesystem                               Size  Used Avail Use% Mounted on
tmpfs                                     26G  2.9M   26G   1% /run
/dev/sda3                                 63G   51G  9.1G  85% /
```

But it seems there are still 9GB (15% of the disk) available. Why is it not enough?

Ephemeral storage used by pods were almost out and kubelet eviction policy is set to evict pod when there is less than 15% disk space is available

It was because of kublet configuration regarding disk pressure situation. To find it out, we need to dump the kublet config. To do it, you run proxy and then curl the kubelet config endpoint.

```bash
kubectl proxy
```

Then, in another terminal, run the following command:

```bash
gangmuk@node0:~$ curl -X GET <node_name>/proxy/configz | jq . > proxy_config.txt
```

`proxy_config.txt`
```json
{
  "kubeletconfig": {
    "enableServer": true,
    "staticPodPath": "/etc/kubernetes/manifests",
    ...
    "evictionHard": {
      "imagefs.available": "15%",
      "memory.available": "100Mi",
      "nodefs.available": "10%",
      "nodefs.inodesFree": "5%"
	    },
    "evictionPressureTransitionPeriod": "5m0s",
    ...
  }
}

```

Anything can easily consume 60GB. In my case, the major culprit was Docker images. I had accumulated a lot of unused Docker images over time, which were taking up significant disk space.

So the solution is to clean up unused Docker images to make some space?

```bash
docker system prune -a
```

Okay, WTF. even now, none of the pods were coming back to ready state. WHY.

Whatever, let's restart 
```bash
kubectl rollout restart deployment istiod -n istio-system
kubectl rollout restart deployment istio-ingressgateway -n istio-system
```

BUT it didn't still bring the pods back... all pods were `Completed`, `ContainerStatusUnknown`, or `Evicted`.



WHAT THE HELL.

The Key Issue: Evicted Pods Are NOT Automatically Cleaned Up
Evicted pods persist until their count exceeds the --terminated-pod-gc-threshold parameter in kube-controller-manager (default is 12,500 pods), and they hang around with a status of "Failed" but reason of "Evicted" Stack OverflowSpacelift.
Why kubectl rollout restart Failed

Rollout restart creates NEW ReplicaSets but doesn't clean up old evicted pods from previous ReplicaSets
When there are replicas in a deployment, evicted pods are typically not deleted automatically How to Delete Pods from a Kubernetes Node with Examples
The hundreds of evicted/failed pods remained in the cluster taking up API server resources and potentially interfering with scheduling decisions
Even after scaling deployment to 0 replicas, evicted pods from old ReplicaSets don't get cleaned up How to Delete Pods from a Kubernetes Node with Examples

Why kubectl delete pods --all Worked

Immediately removed ALL problematic pods - evicted, completed, failed, unknown status pods
Forced the ReplicaSet controllers to create completely fresh pods without any historical baggage
Cleaned the slate - no old evicted pods cluttering the namespace

So, it finally worked when I ran 
```bash
kubectl delete pods --all -n istio-system
```


I think it is such a mess and unreliable. I would say that K8s knows what's happening in very much details. It shouldn't be this difficult to find the root cause of such simple issue (disk pressure). Particularly, the node disk space resourec is infra layer not application layer. User shouldn't be bothered this much when K8s has all this information. K8s should automatically detect the root cause, notify the user, and provide a solution or even just fix it automatically. 