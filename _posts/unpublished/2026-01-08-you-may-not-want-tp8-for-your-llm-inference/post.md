---
layout: post
title: "You may not want TP=8 for your LLM inference"
tags: [numa, nccl, llm inference, TP, PP, pcie]
date: 2026-01-14
category: blog
---

# You may not always want TP=8 for your LLM inference

Recently, I benchmarked batch LLM inference on cloud (AWS) with various TP and PP degrees configurations (TP=[1,2,4,8], PP=[1,2,3,4]). And one of the results confused me a lot. IN a nutshell, (TP=8, PP=1) config in eight GPU instances (48xlarge instance) was slower than (TP=4, PP=1) config in four GPU instances. In this post, I will share what and why it happened. If you are considering running multi-gpu LLM inference (particularly in cloud), this post may be helpful.

## Benchmark environment
This is what and how I benchmarked.

**Application**

LLM inference with Llama3 70B model in fp16 precision.

**Workload**

input token lenght: 2048 tokens per request for all requests

output token lenght: 512 tokens per request for all requests

**Engine**

vLLM

**Cluster**

AWS cloud instances. I will use g6e.12xlarge and g6e.48xlarge, and g5.24xlarge and g5.48xlarge instances for this post.

aws g6e.24xlarge instance has 4 NVIDIA-L40S GPUs

aws g6e.48xlarge instance has 8 NVIDIA-L40S GPUs

aws g5.24xlarge instance has 4 NVIDIA-A10G GPUs

aws g5.48xlarge instance has 8 NVIDIA-A10G GPUs

24xlarge instance is single socket machine. 48xlarge instance is dual socket machine and each socket has 4 GPUs under each physical PCIe root complex.

**Parallelism configurations**

TP=4, PP=1 for four GPU instances (g6e.12xlarge, g5.24xlarge)

TP=8, PP=1 for eight GPU instances (g6e.48xlarge, g5.48xlarge)

Before I show the benchmark results, what's your guess about the performance? Which one do you think it would have higher throughput?

I want to share what I expected and why I was confused.

## Increase TP!? No! Huh?

TP=4, PP=1 (g6e.12xlarge, 4 GPUs):
- Input throughput: 421.63 tokens/sec
- Output throughput: 104.95 tokens/sec
- Total throughput: 526.58 tokens/sec

TP=8, PP=1 (g6e.48xlarge, 8 GPUs):
- Input throughput: 453.61 tokens/sec
- Output throughput: 112.91 tokens/sec
- Total throughput: 566.52 tokens/sec

TP=8 is only ~7.6% faster than TP=4
- Expected: ~2x (doubling GPUs)
- Actual: ~1.08x

**Huh? What? Something is wrong!?**

All GPU-to-GPU communication uses host memory copies over PCIe (no NVLink)
TP=8 has more all-reduce operations (8 GPUs vs 4)
Cross-socket communication in TP=8 adds latency (4 GPUs per socket)

Actually, I am not the only one who are puzzled with this result. 

[vllm issue #8089](https://github.com/vllm-project/vllm/issues/8089)

[vllm issue #16300](https://github.com/vllm-project/vllm/issues/16300)

[vllm issue #16011](https://github.com/vllm-project/vllm/issues/16011)


### hardware topology

g6e.48xlarge instance is dual socket machine. This is the hardware topology of the instance.
```text
┌────────────────────────────────────────────────────────────────┐
│                        g6e.48xlarge                            │
└────────────────────────────────────────────────────────────────┘

     NUMA Node 0                                NUMA Node 1
┌──────────────────────┐                  ┌──────────────────────┐
│  AMD EPYC 7R13       │                  │  AMD EPYC 7R13       │
│  • 96 vCPUs          │◄────────────────►│  • 96 vCPUs          │
│  • 768 GB DDR5       │ Infinity Fabric  │  • 768 GB DDR5       │
│                      │  (~128 GB/s)     │                      │
│  ┌────────────────┐  │                  │  ┌────────────────┐  │
│  │ Root Complex 0 │  │                  │  │ Root Complex 1 │  │
│  │ (PCIe ctrl)    │  │                  │  │ (PCIe ctrl)    │  │
│  └─┬──┬──┬──┬─────┘  │                  │  └─┬──┬──┬──┬─────┘  │
│    │  │  │  │        │                  │    │  │  │  │        │
└────┼──┼──┼──┼────────┘                  └────┼──┼──┼──┼────────┘
     │  │  │  │                                │  │  │  │
     ↓  ↓  ↓  ↓                                ↓  ↓  ↓  ↓
   GPU0 1  2  3                              GPU4 5  6  7

```
Note: No direct GPU↔GPU DMA paths exist. All GPU communication MUST go through host memory.

### Data path

**within the same socket**

GPU-0 Memory (Socket 0) ─► PCIe-0 DMA Write (32 GB/s) ─► CPU-0 Root Complex ─► CPU-0 Host Memory (Staging Buffer) ─► DMA Read Request ─► CPU-0 Root Complex ─► PCIe-0 DMA Read ─► GPU-1 Memory

**cross-socket within the same NUMA node (g6e.48xlarge)**

GPU-3 Memory (Socket 0) ─► PCIe-3 DMA Write (32 GB/s) ─► CPU-0 Root Complex ─► CPU-0 Host Memory (Staging Buffer) ─► Memory Controller reads for transfer ─► Infinity Fabric (CPU-to-CPU memory copy, ~128 GB/s shared) ─► CPU-1 Host Memory (Staging Buffer) ─► DMA Read Request ─► CPU-1 Root Complex ─► PCIe-4 DMA Read ─► GPU-4 Memory

**NCCL_P2P_DISABLE config**

NCCL_P2P_DISABLE=1
Conservative path:
- Use socket-based IPC
- Explicit synchronization barriers
- Extra memory copies for safety
- Lower performance
- 
NCCL_P2P_DISABLE=0
Optimized path:
- Use DMA-based transfers
- Pipelined operations
- Better buffer management
- Still uses host memory, but more efficiently
- ~10-20% faster

Both use host memory. The difference is the software path, not hardware path.

NCCL_P2P_DISABLE=0 does not show higher performance than NCCL_P2P_DISABLE=1. It is because the hardware data path is the same.


**table**

PathNCCL_P2P_DISABLE=0NCCL_P2P_DISABLE=1Why?Same Socket~18-22 GB/s~16-20 GB/sBoth use host memory stagingCross Socket~12-16 GB/s~10-14 GB/sBoth use host memory + Infinity Fabric

## Avoid inter-node communication! No! Huh?
AWS including other cloud providers offers different instance sizes with the same GPU type. For example, NVIDIA-A10G (g6 family), NVIDIA-L40S (g6e family), and other GPU instances in AWS offer 1,2,4,8 GPU instances. For example, NVIDIA-A10G offers
- g5.xlarge instance: 1 GPU
- g5.2xlarge instance: 1 GPU
- g5.4xlarge instance: 2 GPU
- g5.8xlarge instance: 2 GPU
- g5.12xlarge instance: 4 GPU
- g5.24xlarge instances: 4 GPU
- g5.48xlarge instance: 8 GPU

Now, think about what instance you would choose for a given TP and PP. There are different ways to deploy the same TP and PP. For example, TP=4, PP=2 can be deployed either in two g5.x12large instanes or one g5.48xlarge instance. If the throughput maximization is the goal, what would you choose between these two options?

**g5.24xlarge vs g5.48xlarge**

g5.24xlarge instance is a single socket and has 4 GPUs. 

g5.48xlarge instance is dual-socket NUMA node and has total 8 GPUs. Each socket has its own PCIe root complex and connected to four GPUs, respectively. Inter-socket is connected by AMD's Infinity Fabric.

**workload**
llama3 70B model, fp16

2048 input tokens per request

512 output tokens per request

Sending 30 requests at the same time

**performance**
What do you expect? Which one do you think it would be faster? two g5.x12large instances or one g5.48xlarge instance?

1×g5.48xlarge (single node):
Throughput: 134.56 tokens/sec
Cost: $16.384/hour
2×g5.12xlarge (2 nodes):
Throughput: 180.05 tokens/sec
Cost: $8.192/hour

Yes, what the heck! Why single-node is slower than multi-node? 

It was completely unexpected result for me. My mental model was avoid inter-node communication as much as possible. Cross-node networking is always bad! But the actual benchmark result was the opposite... Why...

**hardware utilization**
Metric	Single-Node	Multi-Node	Insight
Memory BW Util	46.03%	61.58%	Multi-node uses more bandwidth (higher throughput)
Throughput	134.56 tok/s	180.05 tok/s	Multi-node is 34% faster
Expected Cross-Socket BW	~5-10 Gbps	N/A	Host memory bottleneck
Expected Network BW	N/A	~25 Gbps	AWS Enhanced Networking

**Why single-node is slower than multi-node?**
My guesses were:
- Cross-socket bandwidth: On g5 instances, cross-socket communication uses host memory (PHB topology), which can be slower than inter-node network bandwidth.
- Network vs host memory: AWS inter-node network (25 Gbps) may exceed the cross-socket host memory bandwidth.
- Memory contention: Single-node may have more contention for host memory bandwidth.
- Ray overhead: Different Ray communication patterns between single-node and multi-node.

**Root cause: NUMA hardware topology**
GPU-to-CPU hardware topology is the root cause of the unexpected bad performance in 48x.large instance.
```text
GPU 0,1,6 → NUMA 0 (cores 0-95)
GPU 2,3,4,5,7 → NUMA 1 (cores 96-191)
```

3:5 split across NUMA nodes.... This mapping is determined by physical PCIe topology - AWS wired 3 GPUs to Socket 0, 5 GPUs to Socket 1. What the heck... really? doesn't make sense... what is this weird topology... But this is what the log showed...

And this destroys the performance.
```
PP Stage 0 TP (GPU0,1,2,3): 2 on NUMA 0, 2 on NUMA 1 → Forces Infinity Fabric cross
PP Stage 1 TP (GPU4,5,6,7): 3 on NUMA 1, 1 on NUMA 0 → Forces Infinity Fabric cross
```

Not just PP stages but every TP all-reduce crosses inter-socket, Infinity Fabric (~64 GB/s, contended).

That's why 2x g5.24xlarge wins by large margin for TP=4, PP=2 over 1x g5.48xlarge... 

What's even more headaching is that the PCIe topology in 48x.large instance is not static apparently.. it is random box and this random will affect the performance a lot. Hence, the safe/conservative option is to avoid NUMA node except for TP=8 strategy.

<div class="expandable" markdown="1">

```text
2026-01-08 08:58:04,274 - INFO - (RayWorkerWrapper pid=25590) ip-172-31-38-18:25590:26347 [0] NCCL INFO [Proxy Service] Device 0 CPU core 72\
2026-01-08 08:58:04,274 - INFO - (RayWorkerWrapper pid=25590) ip-172-31-38-18:25590:26351 [0] NCCL INFO [Proxy Service UDS] Device 0 CPU core 74\
2026-01-08 08:58:04,278 - INFO - (RayWorkerWrapper pid=25591) ip-172-31-38-18:25591:26349 [1] NCCL INFO [Proxy Service UDS] Device 1 CPU core 61\
2026-01-08 08:58:04,282 - INFO - (RayWorkerWrapper pid=25593) ip-172-31-38-18:25593:26350 [3] NCCL INFO [Proxy Service UDS] Device 3 CPU core 159\
2026-01-08 08:58:04,282 - INFO - (RayWorkerWrapper pid=25593) ip-172-31-38-18:25593:26346 [3] NCCL INFO [Proxy Service] Device 3 CPU core 144\
2026-01-08 08:58:04,286 - INFO - (RayWorkerWrapper pid=25595) ip-172-31-38-18:25595:26357 [5] NCCL INFO [Proxy Service] Device 5 CPU core 163\
2026-01-08 08:58:04,286 - INFO - (RayWorkerWrapper pid=25595) ip-172-31-38-18:25595:26361 [5] NCCL INFO [Proxy Service UDS] Device 5 CPU core 189\
2026-01-08 08:58:04,289 - INFO - (RayWorkerWrapper pid=25592) ip-172-31-38-18:25592:26345 [2] NCCL INFO [Proxy Service] Device 2 CPU core 170\
2026-01-08 08:58:04,289 - INFO - (RayWorkerWrapper pid=25592) ip-172-31-38-18:25592:26348 [2] NCCL INFO [Proxy Service UDS] Device 2 CPU core 189\
2026-01-08 08:58:04,291 - INFO - (RayWorkerWrapper pid=25596) ip-172-31-38-18:25596:26359 [6] NCCL INFO [Proxy Service] Device 6 CPU core 72\
2026-01-08 08:59:43,277 - INFO - (RayWorkerWrapper pid=25591) ip-172-31-38-18:25591:27323 [1] NCCL INFO [Proxy Service] Device 1 CPU core 95\
2026-01-08 08:59:43,286 - INFO - (RayWorkerWrapper pid=25593) ip-172-31-38-18:25593:27326 [3] NCCL INFO [Proxy Service] Device 3 CPU core 185\
2026-01-08 08:59:43,286 - INFO - (RayWorkerWrapper pid=25593) ip-172-31-38-18:25593:27331 [3] NCCL INFO [Proxy Service UDS] Device 3 CPU core 158\
2026-01-08 08:59:43,954 - INFO - (RayWorkerWrapper pid=25597) ip-172-31-38-18:25597:27345 [7] NCCL INFO [Proxy Progress] Device 7 CPU core 177\
...
```

</div>


**actual root cause?**
NUMA Topology Results
NUMA Hardware Layout (from numactl --hardware):

available: 2 nodes (0-1)
```
node 0 cpus: 0-47, 96-143     (96 cores)
node 1 cpus: 48-95, 144-191   (96 cores)
```

GPU PCIe Bus and NUMA Mapping:
```
GPU	PCIe Bus ID	NUMA Node	Local CPUs
GPU0	00000000:00:16.0	N/A	N/A
GPU1	00000000:00:17.0	N/A	N/A
GPU2	00000000:00:18.0	N/A	N/A
GPU3	00000000:00:19.0	N/A	N/A
GPU4	00000000:00:1A.0	N/A	N/A
GPU5	00000000:00:1B.0	N/A	N/A
GPU6	00000000:00:1C.0	N/A	N/A
GPU7	00000000:00:1D.0	N/A	N/A
```

Key Findings
Virtualized PCIe topology: The PCIe bus IDs (00000000:00:1X.0) are virtualized by AWS. These are not real physical PCIe addresses - they're virtual addresses exposed by the Nitro hypervisor.

No NUMA affinity exposed: The /sys/bus/pci/devices/*/numa_node files don't exist for these virtual PCIe devices, which is why we get N/A. This is because:

AWS g5 instances use passthrough virtualization for GPUs
The hypervisor doesn't expose physical NUMA topology to the guest OS
All GPUs appear as connected to a single virtual PCIe root complex
NCCL's behavior: Since NCCL can't determine real NUMA affinity, it assigns proxy threads somewhat arbitrarily across CPU cores. This explains the scattered proxy core assignments we saw earlier (cores 32, 54, 149, 179, etc. across both NUMA nodes).

What this means for performance
On g5.48xlarge:

No NVLink - all GPUs connect via PCIe through CPU
Virtualized topology - real NUMA affinity is hidden
P2P disabled (NCCL_P2P_LEVEL=SYS) - forces all traffic through CPU memory
Random NUMA placement - proxy threads may cross NUMA boundaries adding latency
