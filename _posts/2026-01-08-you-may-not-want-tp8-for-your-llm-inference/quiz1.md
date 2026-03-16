
Question: 
If the parallelism is the same and the GPU model is the same, would they have the same performance regardless of instance choice? More specifically, for the same parallelism config of (TP=4, PP=2), 
what do you expect in these two deployments?
1. two 4 GPU instances (2 * g5.12xlarge) 
2. one 8 GPU instance (1 * g5.48xlarge)

The same throughput since they have the same parallelism and GPU model?

Different throughput? 

Why same? Or why not same?

In two 4 GPU instances, each PP stage will be placed within the same instance. The first TP=4 stage will be placed in the first instance and the second TP=4 will be placed in the second instance to avoid cross-node TP.



Hint:
Oh hoi! Not same. Surprise again!?

Can you guess which one is worse? 2x g5.12xlarge v.s. 1x g5.48xlarge for (TP=4, PP=2)

See if you can guess the reason with more information about hardware. 

The G5 instance family is not nvlink supported. G5 instance has PCIe Gen4 x 16 lanes which has ~32 GB/s unidirectional and ~64GB/s bidirectional bandwidth. g5.12xlarge instance is a single socket node with one PCIe root complex with all 4 GPUs connected the same PCIe root complex. g5.12xlarge’s NIC offers 5GB/s (40Gbps) network bandwidth (virtualized NIC). 

And 48xlarge instance is a two-socket system with two NUMA nodes, two PCIe root complexes (Gen4 x 16 lanes each), 4 GPUs connected to each PCIe root complex. Inter-socket bandwidth (AMD Infinity Fabric) is around 128GB/s which is higher than NIC bandwidth and PCIe bandwidth.



Answer:

The answer is… 2x g5.12xlarge is better than g5.48xlarge for TP=4, PP=2! (for 2048/512 for input/output token length workload)

If you are puzzled, thinking …
‘How the heck is 1x g5.48xlarge is worse than 2x g5.12xlarge? 48xlarge is a single machine with 8 GPUs which has higher inter-GPU network bandwidth which is PCIe than inter-node network between two separate 12xlarge instance which is using 5GB/s NIC. Okay, maybe not better for whatever reason but at least why not same!?!!!?’

So, if you just do blind calculation, then 1x 48xlarge should be much faster or at least on par with 2x 12xlarge. But TP=4, PP=2 with 1x 48xlarge has much worse performance than 2x 12xlarge.

Distributed inference with higher network bandwidth has lower throughput!?! 
It is counter-intuitive (which we love!).

Let’s see why. To do that, we need to peel off a few more layers. We need to know what happens in the cloud VM, in NCCL, and in vLLM at the same time.


Layer 1: What the VM actually sees

We said the g5.48xlarge is physically a two-socket machine. Two NUMA nodes, two PCIe root complexes, 4 GPUs on each socket, connected by AMD Infinity Fabric. You’d expect NCCL to see this topology and make smart decisions about it.

But it doesn’t. Here’s what `nvidia-smi topo -m` shows inside the 48xlarge VM:

```
        GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7   NUMA Affinity
GPU0     X    PHB   PHB   PHB   PHB   PHB   PHB   PHB    0-1
GPU1    PHB    X    PHB   PHB   PHB   PHB   PHB   PHB    0-1
...
GPU7    PHB   PHB   PHB   PHB   PHB   PHB   PHB    X     0-1
```

All GPUs show PHB (PCIe Host Bridge) to every other GPU. NUMA affinity is "0-1" for all of them. The physical truth -- that GPU 0-3 are on socket 0 and GPU 4-7 are on socket 1 -- is completely hidden by the hypervisor. The VM sees a flat topology.

Here's the subtle part: the hypervisor hides two things, but in different ways. The PCIe device-level topology is fully blocked -- GPUs can't do direct P2P transfers because the hypervisor virtualizes the PCIe bus and doesn't expose the real BAR addresses. But the CPU NUMA topology is partially exposed -- the VM does see two NUMA nodes (0 and 1) with all 192 cores. The problem is the *mapping* between GPUs and NUMA nodes is lost. Every GPU reports affinity to "0-1" (both nodes), so software has no way to know which GPUs are physically closer to which NUMA node.

As far as NCCL is concerned, all 8 GPUs are equivalent and all 192 CPU cores are equally close to any GPU.

On the 12xlarge? Each VM is carved from a single socket. `nvidia-smi topo -m` shows 4 GPUs, all PHB, NUMA affinity "0". One NUMA domain. 48 CPU cores. Simple and honest.

This matters because the next layer -- NCCL -- makes all of its decisions based on this topology information.


Layer 2: NCCL transport -- how GPUs actually talk

vLLM uses NCCL for all GPU-to-GPU communication. TP=4 all-reduce shuffles data between all 4 GPUs in the TP group at every transformer layer. PP sends activations from the last GPU of stage 1 to the first GPU of stage 2 once per microbatch.

G5 instances don’t have NVLink. So what transport does NCCL use?

NCCL first tries P2P (direct GPU-to-GPU transfer over PCIe). But P2P over PCIe doesn’t work on G5 instances. The hypervisor virtualizes the PCIe topology and blocks direct P2P transactions between GPUs. NCCL detects this and falls back to: **SHM (shared memory) transport**.

SHM transport works like this:
1. GPU-0 DMAs its data to a pinned buffer in host (CPU) memory
2. GPU-1 DMAs from that same host buffer into its own memory

Two PCIe hops per transfer. Double the PCIe bandwidth consumption compared to P2P. But it works, and both setups (12xlarge and 48xlarge) use the exact same SHM transport. Same transport, same PCIe Gen4 bandwidth per GPU. So... why different performance?

The answer is NOT in the transport itself. It’s in the CPU threads that orchestrate it.


Layer 3: NCCL proxy threads -- where it falls apart

NCCL doesn’t just fire-and-forget these DMAs. It runs **proxy threads** on the CPU that manage the whole dance -- polling for DMA completion, signaling the peer GPU that data is ready, coordinating the next chunk. These proxy threads are on the critical path of every transfer. If they stall, the GPU stalls waiting for data. And they are busy-spinning threads -- they burn a CPU core polling in a tight loop to minimize latency.

NCCL pins each proxy thread to a specific CPU core. How does it pick which core? It looks at the GPU’s NUMA affinity and tries to pick a core on the same NUMA node as the GPU. Sensible strategy. When it works.

On the g5.12xlarge, the GPU NUMA affinity says "0". NCCL picks from cores 0-47. All on the same (and only) NUMA node. All local to the GPUs. Clean.

On the g5.48xlarge, the GPU NUMA affinity says "0-1". Both NUMA nodes. NCCL has no signal. It picks cores semi-randomly across the entire 192-core space. Here’s what actually happened in our benchmark:

**g5.48xlarge proxy thread placement (TP communicator):**

| GPU | Proxy Progress core | Proxy Service core |
|-----|--------------------|--------------------|
| 0   | 182 (NUMA 1)       | 85 (NUMA 0)        |
| 1   | 66 (NUMA 0)        | 105 (NUMA 1)       |
| 2   | 167 (NUMA 1)       | 189 (NUMA 1)       |
| 3   | 91 (NUMA 0)        | 105 (NUMA 1)       |
| 4   | 138 (NUMA 1)       | 24 (NUMA 0)        |
| 5   | 59 (NUMA 0)        | 181 (NUMA 1)       |
| 6   | 33 (NUMA 0)        | 13 (NUMA 0)        |
| 7   | 59 (NUMA 0)        | 180 (NUMA 1)       |

Chaos. GPU 0 is physically on socket 0, but its proxy progress thread is pinned to core 182 on NUMA 1. GPU 1 and GPU 3 both have their proxy service pinned to the same core 105 -- two busy-spinning threads fighting for one core. GPU 5 and GPU 7 share core 59 for their progress threads.

It gets worse. For the PP communicator, four different GPU proxy threads are pinned to **the same core 183**. Four busy-spinning threads on one core. Fighting for time slices instead of driving DMAs.

**g5.12xlarge proxy thread placement (TP communicator, one node):**

| GPU | Proxy Progress core | Proxy Service core |
|-----|--------------------|--------------------|
| 0   | 47                 | 20                 |
| 1   | 47                 | 2                  |
| 2   | 25                 | 20                 |
| 3   | 3                  | 31                 |

All cores in 0-47. Single NUMA domain. No cross-socket surprises.


Layer 4: Why cross-NUMA proxy placement kills throughput

So what exactly goes wrong when a proxy thread is on the wrong NUMA node?

Two things compound.

**First: cross-NUMA SHM buffer placement.** The SHM buffer’s physical memory pages get allocated on the NUMA node where the proxy thread first touches them. If GPU 0’s proxy thread runs on NUMA 1, the SHM buffer lands on NUMA 1’s memory. Now GPU 0 (physically on socket 0) has to DMA across the inter-socket link to reach the buffer. Every all-reduce chunk, every layer, every token -- the DMA crosses the socket boundary. Not because it has to, but because NCCL was given wrong topology information.

**Second: proxy thread contention.** When multiple busy-spinning proxy threads share a core, they’re preempted by the OS scheduler in round-robin. A proxy thread that gets preempted can’t signal "buffer consumed" to its peer. The peer’s GPU sits idle waiting for the signal. Multiply this by four threads on core 183, across thousands of all-reduce operations, and you get systemic throughput loss.

On the 12xlarge, neither problem exists. Single NUMA means all buffers are local. Fewer GPUs per node means fewer proxy threads competing for cores. The VM boundary accidentally creates the perfect NUMA-aligned partition.

The irony: AWS’s virtualization helps on the 12xlarge (forces NUMA locality) and hurts on the 48xlarge (hides NUMA topology from NCCL).


But wait -- what about PP over the network?

The PP boundary crosses the 5 GB/s NIC on the 2x 12xlarge setup. Meanwhile, on the 48xlarge, the PP boundary is just SHM within the same machine. Sounds bad for the 12xlarge, right?

But PP only sends one activation tensor per pipeline microbatch. It’s a single point-to-point transfer, not an all-reduce. The data volume is small compared to the TP all-reduce that happens at every transformer layer. TP all-reduce is the hot path. PP is the cool path. Paying a small network tax on the cool path while getting clean, NUMA-local SHM on the hot path is a great trade.


The numbers

| Metric | 1x g5.48xlarge | 2x g5.12xlarge |
|--------|---------------|----------------|
| Total tokens/s | 139.28 | 180.05 |
| Output tokens/s | 27.76 | 35.88 |
| Avg SM utilization | 90.19% | 85.48% |
| Avg memory BW utilization | 46.93% | 61.58% |

Look at the SM utilization. The 48xlarge has *higher* SM utilization (90%) but *lower* throughput. The GPUs are busy... waiting. Spinning on synchronization barriers while the communication layer struggles to move data through cross-NUMA SHM with contended proxy threads.

Memory bandwidth utilization tells the real story: 46.93% vs 61.58%. The 48xlarge’s GPUs can’t keep their memory pipelines fed because the data isn’t arriving fast enough from the broken communication path.

30% more throughput. By using two smaller, cheaper instances instead of one big one. The cloud is weird.


---


Quiz 2: TP=8 PP=1 vs TP=4 PP=2 on the same g5.48xlarge

Question:

Both (TP=4, PP=2) and (TP=8, PP=1) use the same instance type (1x g5.48xlarge). Same 8 A10G GPUs, same total compute.

Which parallelism config has higher throughput?

And what's the specific reason one is better than the other?


Hint:

(TP=8, PP=1) has higher throughput than (TP=4, PP=2) on g5.48xlarge.

What's the reason that causes it, do you think?

Do you think it was because of the pipeline bubble from PP=2?


Answer:

Well, no. (and you say 'huhhh, you liar!')

If the pipeline bubble in PP=2 was the reason, then (TP=8, PP=1) should have higher throughput than (TP=4, PP=2) regardless of instance choice. But look at (TP=4, PP=2) deployed on 2x g5.12xlarge instances:

| Config | Instance | Total tok/s | Output tok/s |
|--------|----------|-------------|-------------|
| TP=4, PP=2 | 1x g5.48xlarge | ~139 | ~27.8 |
| TP=8, PP=1 | 1x g5.48xlarge | 166.8 | 33.2 |
| TP=4, PP=2 | 2x g5.12xlarge | 180.1 | 35.9 |

2x g5.12xlarge with TP=4, PP=2 beats TP=8, PP=1 on 48xlarge. Pipeline bubble and all. If the bubble was the problem, this shouldn't happen.

We can infer that the pipeline bubble is NOT the reason for the lower throughput of (TP=4, PP=2) on g5.48xlarge compared to (TP=8, PP=1).

Then, what's the reason? We need to take a look at one deeper layer.

Surprisingly, it is the same culprit from Quiz 1: NCCL proxy threads' NUMA-blind core placement on the g5.48xlarge.

Both configs suffer from the same NUMA problem on the 48xlarge — proxy threads scattered across both sockets, SHM buffers landing on wrong NUMA nodes. But the data shows TP=4, PP=2 gets hit harder. The smoking gun is in the run-to-run variance.

We ran TP=4, PP=2 on g5.48xlarge six times. Same config, same instance type, same code. The only thing that changes between runs is where NCCL's proxy threads randomly land:

| Run | Total tok/s | Mem BW util |
|-----|-------------|-------------|
| 0108 | 134.56 | 46.03% |
| 0110_0315 | 139.28 | 46.93% |
| 0110_0515 | 139.42 | 46.91% |
| 0110_1324 | **165.60** | **55.63%** |
| 0110_1358 | 139.13 | 46.91% |
| 0120 | **160.59** | **54.17%** |

Most runs land around 139 tok/s with ~47% memory bandwidth utilization. But two runs hit 160-165 tok/s with ~55% memory bandwidth. The lucky runs got better NUMA placement — their proxy threads happened to land closer to the right sockets, keeping more SHM buffers local. The throughput jumps 19% just from the NUMA dice roll.

And notice: the lucky TP=4, PP=2 runs (165.6 tok/s) nearly match TP=8, PP=1 (166.8 tok/s). When TP=4, PP=2 gets good NUMA placement, the gap disappears.

Why does TP=4, PP=2 have more variance? It creates more NCCL communicators — separate ones for TP and PP — which means more proxy threads total (84 vs 48 for TP=8, PP=1). More proxy threads scattered across 192 cores means more SHM buffers exposed to the NUMA lottery. Most of the time, the odds aren't in its favor.

TP=8, PP=1 has fewer communicators, fewer proxy threads, and less surface area for NUMA misplacement. It still suffers from the same underlying problem, but it rolls fewer dice.

Compare with the 12xlarge: TP=4, PP=2 on 2x g5.12xlarge hits 180.05 tok/s every time. No variance. Single-socket VMs, NUMA affinity "0", all proxy threads local. The NUMA lottery doesn't exist when there's only one NUMA node.
