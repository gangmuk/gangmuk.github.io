---
layout: post
title: "Mental model for TP and PP in LLM inference"
tags: [TP, PP, llm inference]
date: 2025-12-24
category: blog
---

# Mental model for TP and PP in LLM inference

## Perspective

TP is much more popular than PP in the industry even if TP has much higher network communication. There are two all-reduce for each inference. It becomes amplified in decoding since your FLOPS is smaller but the amount of network communication stay same. Still, I don't have statistics but TP seems more popular. Why? 
There are several factors. I think the most significant factor is the latency not resource utilization. TP has lower latency than PP, especially in decoding. In TP, all GPUs work on the token at the same time. So, the perspective is latency not resource utilization!

Another reason is that PP needs to deal with bubble in pipelining. But I think even if the PP addressed the bubble issue, industry would prefer TP because of the latency. 

From the resource perspective, inherent tradeoff between TP and PP is dealing with communication overhead vs pipeline bubble overhead. It seems it is easier to deal with communication overhead. For example, faster hardware like custom fabric (nvswitch), faster NIC, faster data path (GPU-direct), the whole thing as a product like NV72, and more optimized communication library (evolving NCCL,RCCL,UCCL.).

And the model is placed under the same rack, so the communication overhead becomes less significant. Even in cloud, if you have 4 GPU or 8 GPU instance, they provide higher network bandwidth between the GPU of the same instance, meaning they run in the same machine.

Then, when do we need to use PP? 1. When it is unavoidable to deploy the model in different racks. (The reason can vary), 2. when network can be bottleneck resource (network resource is shared with other application), 3. When the latency is not the first citizen.


## decoding phase
Worth taking a look at [prime intellect in-depth analysis](https://www.primeintellect.ai/blog/inference)

Time to process 125 tokens ≈ Time to process 1000 tokens
Both are dominated by loading the same 19.5 GB of weights
This gives linear throughput scaling with batch size

### Should we microbatching in PP pipelining?
again, the reference: [prime intellect in-depth analysis](https://www.primeintellect.ai/blog/inference)
In synchronous PP: Process full batch (B=1000) in time T, wait (N-1)×T
In async PP: Process N micro-batches (B/N each) in time T each = N×T total
Same total time! This is because of linear throughput scaling when memory bandwidth-bound.

## Network communication

TP communicates 128× MORE than PP.

[Meta Engineering Blog (November 2025)](https://engineering.fb.com/2025/10/17/ai-research/scaling-llm-inference-innovations-tensor-parallelism-context-parallelism-expert-parallelism/):
>"A challenge in tensor parallelism is the 'allreduce' communication operation, which can contribute up to 30% of end-to-end latency."

[Ladder-Residual paper (June 2025)](https://arxiv.org/abs/2506.05476):
>"A Transformer with N layers needs to perform the AllReduce 2N times and this can account for 38% of the inference latency for a 70B model using TP world size of 8, even with NVLink interconnect."

These are empirical measurements from related reference numbers from real systems. 

### TP:

TP (TP_degree=8):
Per layer:
- Attention W_O all-reduce: 2(TP-1)/TP × B × d_model × 2
  = 2 × 7/8 × B × 8192 × 2 = 28,672 × B bytes
  
- MLP W2 all-reduce: 2(TP-1)/TP × B × d_model × 2
  = 28,672 × B bytes

Per layer total: 57,344 × B bytes = 56 KB × B

Total 80 layers: 4.48 MB × B per GPU

Example B=1024: 4.48 GB per GPU per decode step

- Network = 4 × L × (TP_degree - 1) / TP_degree × B × n × d_m
- Prefill (n=1024, B=32) = 4 × 32 × (8-1)/8 × 32 × 1024 × 12288 ≈ 46 GB
- Decode (n=1, B=512) = 4 × 32 × (8-1)/8 × 512 × 1 × 12288 ≈ 0.7 GB

### PP:

PP (PP_degree=8, middle stage):
Receive from previous stage: B × d_model × 2 = B × 16,384 bytes
Send to next stage: B × d_model × 2 = B × 16,384 bytes

Total: 32,768 × B bytes = 32 KB × B per GPU

Example B=1024: 32 MB per GPU per decode step


- Network = (PP_degree - 1) × B × n × d_m
- Prefill (n=1024, B=32) = (8-1) × 32 × 1024 × 12288 ≈ 2.8 GB  (16× less than TP!)
- Decode (n=1, B=512) = (8-1) × 512 × 1 × 12288 ≈ 0.4 GB + weight transfer overhead for microbatching

## Memory consumption

### TP
Per GPU memory:
- Model weights: Total_weights / TP_degree
- KV cache: L × B × max_seq_len × d_m / TP_degree
- Activations: B × d_m (for full batch!)

Total HBM ≈ weights/TP + KV/TP + B×d_m

### PP
Per GPU memory:
- Model weights: Total_weights / PP_degree
- KV cache: L × B × max_seq_len × d_m / PP_degree  
- Activations: microbatch_size × d_m (much smaller!)

Total HBM ≈ weights/PP + KV/PP + (B/PP)×d_m

Activation memory: PP uses B/PP_degree, TP uses full B!

## Memory bandwidth utilization

### TP:
All GPUs stream weights in parallel
Each GPU: weights/TP_degree per decode step
Aggregate bandwidth: ALL GPUs active simultaneously
Utilization: ~100% (memory-bound in decode)

Example (L=32, TP=8, B=1024, d_m=12288):
= 4 × 32 × (7/8) × 1024 × 12288
= 1.4 GB per decode step

Over 100 decode steps: 140 GB total!

### PP:
Pipeline stages stream weights sequentially through stages
Each stage: weights/PP_degree per step
Aggregate bandwidth: Once pipeline full, all GPUs active
Utilization: ~95% (accounting for small bubbles)

Example (PP=8, microbatch=128, d_m=12288):
= 7 × 128 × 12288
= 11 MB per decode step

## Computation

### TP

Prefill: All GPUs compute simultaneously
- Each GPU: FLOPs_layer / TP_degree
- Total active SMs: All GPUs (100% utilization if batch large enough)

Decode: All GPUs compute simultaneously  
- Each GPU: FLOPs_layer / TP_degree
- Total active SMs: All GPUs (but memory-bound, so SMs idle waiting for data)

### PP

Prefill (with microbatching M requests):
- Steady state: All stages busy with different requests
- Stage 0 processes batch m, Stage 1 processes batch m-1, etc.
- Total active SMs: All GPUs (can achieve ~100% if pipeline full)

Decode (single request):
- Only ONE stage active at a time
- Other stages idle (pipeline bubble)
- Total active SMs: 1/PP_degree of total (terrible utilization!)

Decode (with M concurrent requests for pipelining):
- Can fill pipeline, but still sequential dependencies
- Bubble ratio depends on M and stage balance


## Comparison summary

Llama3 70B
| Metric | TP (degree=8) | PP (degree=8) | Ratio |
| :--- | :--- | :--- | :--- |
| **Weights** | 19.5 GB | 19.5 GB | 1× |
| **KV Cache** | 400 MB | 400 MB | 1× |
| **Activations** | 70 MB | 70 MB | 1× |
| **Total Memory** | ~20 GB | ~20 GB | 1× |
| **Memory Read** | 19.5 GB/step | 19.5 GB/step | 1× |
| **Network Comm** | 44.8 GB/step | 320 MB/step | **140×** |

| Phase | Bottleneck Type | TP Trade-off | PP Trade-off | Winner |
| :--- | :--- | :--- | :--- | :--- |
| **Prefill** | Compute-bound | High comm (20-30% overhead) blocks compute | Low comm (<1%), pipeline fills well | **PP** (140× less comm dominates) |
| **Decode (B=10k)** | Memory-bound | High comm, but GPUs parallel (no bubbles) | Low comm, but pipeline bubbles waste cycles | **Empirical** (comm vs bubbles) |

