---
layout: post
title:  "DCQCN, RDMA, CXL"
date:   2024-05-19
tags: [networking, notes]
category: blog
---

This post is not organized at all—it's a set of rough notes from my research on RDMA, SmartNICs, and CXL while looking for a potential research project.
It's loosely structured around networking keywords like DCQCN, RDMA, RoCE, SmartNICs, and CXL.

Some easy-reading short posts on RDAM and other datacenter networking.
- [A LinkedIn summary post on RDMA Networking Trends](https://www.linkedin.com/pulse/rdma-networking-trends-rakesh-cheerla-izpuc/)
- [Juniper Networks Blogs on AI/ML Data Center Networking on Ethernet](https://blogs.juniper.net/en-us/industry-solutions-and-trends/ai-ml-data-center-networking-on-ethernet)

### DCQCN

**High level idea of DCQCN**: The idea behind DCQCN is to allow ECN to do flow control by decreasing the transmission rate when congestion starts, thereby minimizing the time PFC is triggered, which stops the flow altogether.

**Purpose of PFC**: preventing buffer overflow

**Purpose of ECN**: controlling sending rate of flow so that PFC is not triggered unless necessary.

**Problem in PFC**: The technical challenge in using PFC is that, when active, it restrains all traffic for the class whether or not it is destined for an overfed path. Furthermore, a single overfed path can lead to traffic being restrained on all network paths. This is called congestion spreading.

**Some random question**: What about RDMA without PFC?

**Headroom Buffers**—A PAUSE message sent to an upstream device takes some time to arrive and take effect. To avoid packet drops, the PAUSE sender must reserve enough buffer to process any packets it may receive during this time. This includes packets that were in flight when the PAUSE was sent, and the packets sent by the upstream device while it is processing the PAUSE message. You allocate headroom buffers on a per port per priority basis out of the global shared buffer. You can control the amount of headroom buffers allocated for each port and priority using the MRU and cable length parameters in the congestion notification profile. If you see minor ingress drops even after PFC is triggered, you can eliminate those drops by increasing the headroom buffers for that port and priority combination.

**PFC Threshold**—This is an ingress threshold. This is the maximum size an ingress priority group can grow to before a PAUSE message is sent to the upstream device. Each PFC priority gets its own priority group at each ingress port. PFC thresholds are set per priority group at each ingress port. There are two components in the PFC threshold—the `PG MIN` threshold and the `PG shared` threshold. Once `PG MIN` and `PG shared` thresholds are reached for a priority group, PFC is generated for that corresponding priority. The switch sends a RESUME message when the queue falls below the PFC thresholds.

**ECN Threshold**—This is an egress threshold. The ECN threshold is equal to the WRED start-fill-level value. Once an egress queue exceeds this threshold, the switch starts ECN marking for packets on that queue. For DCQCN to be effective, this threshold must be lower than the ingress PFC threshold to ensure PFC does not trigger before the switch has a chance to mark packets with ECN. Setting a very low WRED fill level increases ECN marking probability. For example with default shared buffer setting, a WRED start-fill-level of 10 percent ensures lossless packets are ECN marked. But with a higher fill level, the probability of ECN marking is less. For example, with two ingress port with lossless traffic to the same egress port and a WRED start-fill-level of 50 percent, no ECN marking will occur, because ingress PFC thresholds will be met first.

The key differences between TCP and RoCE are:
- TCP is stream-based while RoCE is message-based
- TCP implementations are typically software-based while RoCE is implemented in the hardware
- TCP controls an inflight window, number of unacknowledged bytes, **while RoCE controls the transmission rate**

for lossless traffic, congestion is signaled **at a per-queue** granularity.

[Broadcom: Introduction to Congestion Control for RoCE](https://docs.broadcom.com/doc/NCC-WP1XX)

[Congestion Control for Large-Scale RDMA Deployments, Sigcomm '15](https://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p523.pdf)
- Problem: RDMA requires lossless network. Packet should arrive in-order
- Solution: DCQCN (PFC + ECN)

[Data Center Quantized Congestion Notification (DCQCN](https://www.juniper.net/documentation/us/en/software/junos/traffic-mgmt-qfx/topics/topic-map/cos-qfx-series-DCQCN.html#:~:text=Data%20Center%20Quantized%20Congestion%20Notification%20(DCQCN)%20is%20a%20combination%20of,%2Dto%2Dend%20lossless%20Ethernet).

### RoCE: RDMA over Converged Ethernet

[RDMA over Commodity Ethernet at Scale, Sigcomm ‘16](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/11/rdma_sigcomm2016.pdf)

### Performance Isolation in RDMA

[Justitia: Software Multi-Tenancy in Hardware Kernel-Bypass Networks, NSDI '22](https://www.usenix.org/conference/nsdi22/presentation/zhang-yiwen)
- Problem: In kernel bypass network (RDMA), the network can’t be controlled since the networking is happening in NIC without host(CPU) involved. You as a host CPU don’t know what’s happening in networking layer such as bandwidth utilization, resource contention as well as can’t control the resource allocation in network and also can’t control packet level stuff such as packet controller (spacing, segmentation, MTU, congestion control, etc) .

[Empowering Azure Storage with RDMA, NSDI '23](https://www.usenix.org/conference/nsdi23/presentation/bai)


### CXL: Compute Express Link

Existing disaggregated memory: software memory disaggregation
CXL: hardware memory disaggregation

[Logical Memory Pools: Flexible and Local Disaggregated Memory, HotNet '23](https://conferences.sigcomm.org/hotnets/2023/papers/hotnets23_amaro.pdf)
- Insightful sentence: processors can directly access such memory. Hardware memory disaggregation is faster than software because processors access memory using loads and stores, rather than IO requests. Load and stores are lighter weight, have lower latency, and can leverage processor mechanisms to hide memory latency, such as pipelining, out-of-order and speculative execution, and prefetching [17, 27]. CXL is also more promising than prior attempts at hardware memory disaggregation [1, 7, 16, 19, 25] because it has gained wide support from industry, from memory makers (Samsung, Micron, SK Hynix), to OEMs(e.g.,HPE, Dell),CPUmanufacturers (Intel, AMD), and startups.

[A Case Against CXL Memory Pooling, HotNet '23](https://conferences.sigcomm.org/hotnets/2023/papers/hotnets23_levis.pdf)
- Three problems must be solved for CXL to be used in practice.
- In summary, as long as the cost, software complexity, and lack of utility properties hold, sharing a large DRAM bank between servers with CXL is a losing proposition. If one of these issues goes away – CXL is cheap, CXL is nearly as fast as main memory, or VM shapes become difficult to pack into servers – then CXL memory pools might prove to be useful.