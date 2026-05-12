---
layout: post
title: "VLLM error and network configs"
tags: [vllm, error, network, configs]
date: 2025-12-29
category: blog
---

The terms used in vllm were confusing me with what I knew. So, I did some research on it to confirm them correctly. This is a summary.

What I was confused with is shm in vllm config and nvshmem. shm in vllm (specifcally communication in ray) has nothing to do with nvshmem. In my opinion, the term 'shm' in ray is misleading. It should be something 'host_memory' or 'host_memory_staging'.

And any of these does not configure AWS EFA (Elastic Fabric Adapter). 

`VLLM_USE_RAY_WRAPPED_PP_COMM`: default is 1. When 1, it will use vLLM's internal PP communication handling (RayPPCommunicator wrapping vLLM's device_communicator). When 0, Ray creates and manages its own NCCL groups directly. 1 is more reliable because it integrates better with vLLM's PP infrastructure.

`NCCL_P2P_DISABLE`: default is 0 (P2P enabled). When 0, allows direct GPU-to-GPU transfer without host memory staging if hardware supports it (NVLink or PCIe P2P). When 1, forces all NCCL communication through host memory. Only matters when using NCCL transport - if CHANNEL_TYPE=shm, this setting is ignored for PP communication (but still affects TP).

`VLLM_USE_RAY_COMPILED_DAG_CHANNEL_TYPE`: default is "auto". This configures the actual TRANSPORT MECHANISM (data path) for PP inter-stage communication. When "nccl", uses NCCL transport which respects NCCL_P2P_DISABLE setting. When "shm", uses Ray's data transfer implementation that goes through host memory staging. It always goes through host memory regardless of hardware. When "auto", Ray decides based on heuristics.

In my case, I was running experiments with "G6e" family instance in aws. (NVIDIA L40S aws instances)

G6e family has EFA RDMA but NO GPUDirect RDMA, and no NVLink. It means:
- Same-node with CHANNEL_TYPE=nccl: networking between GPUs can still use PCIe P2P without host memory if NCCL_P2P_DISABLE=0. Only uses host memory if NCCL_P2P_DISABLE=1 or if CHANNEL_TYPE=shm.
- Same-node with CHANNEL_TYPE=shm: networking between GPUs always goes through host memory.
- Cross-node: networking between GPUs must copy through host memory because there's no GPUDirect RDMA support.