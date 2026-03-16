---
layout: post
title: "Batching Strategy for Offline LLM Inference"
date: 2026-03-15
tags: [vLLM, LLM inference, batching, KV cache, throughput]
category: blog
---

# Batching Strategy for Offline LLM Inference on Continuous Batching Servers

## 1. Background

### 1.1 Prefill and Decode Phases

Autoregressive LLM inference proceeds in two phases with distinct computational profiles.

The **prefill** phase processes the input prompt in a single forward pass, computing KV (key-value) cache entries for all input tokens. Because it applies dense matrix multiplications across the full sequence length, prefill is compute-bound: it achieves high arithmetic intensity and utilizes GPU streaming multiprocessors (SMs) efficiently.

The **decode** phase generates output tokens one at a time. Each step executes a full forward pass through the model to produce a single token, reading the model weights and accumulated KV cache from memory. With one token of useful output per pass, the ratio of computation to memory access is low, making decode memory-bandwidth-bound.

These characteristics produce an asymmetry in per-phase throughput. Prefill processes many tokens per forward pass, yielding high instantaneous token throughput. Decode produces one token per pass, and its throughput is gated by memory bandwidth.

### 1.2 KV Cache as a Memory Constraint

Each active request holds a KV cache proportional to its current sequence length. GPU memory is statically partitioned between model weights and KV cache at server startup. The KV cache capacity determines the maximum number of concurrently active requests and, by extension, the decode batch size.

When the KV cache is full, the scheduler must either queue incoming requests or preempt active ones. vLLM's continuous batching scheduler assigns priority by arrival order and, when necessary, **preempts** lower-priority requests by discarding their KV cache. A preempted request re-enters the queue and must be re-prefilled from scratch upon rescheduling. vLLM does not perform KV cache swapping to host memory by default.

### 1.3 Continuous Batching

Unlike static batching, where a new batch begins only after all requests in the current batch complete, continuous batching admits new requests into the running batch as soon as KV cache capacity becomes available. This allows the system to overlap prefill of newly admitted requests with ongoing decode of existing ones, improving GPU utilization relative to static batching.

The throughput of a continuously batched system depends on the mix of prefill and decode work at any given time. A batch dominated by prefill achieves higher token throughput; a batch in steady-state decode achieves lower but stable throughput. The scheduler's behavior — how it admits, prioritizes, and preempts requests — directly controls this mix and depends on the pressure exerted by the incoming request queue.

### 1.4 Batching Strategy for Offline Inference

In offline batch inference, the client holds a fixed set of requests and seeks to process all of them as fast as possible. Unlike online serving, where request arrival is exogenous, the client fully controls when and how many requests are submitted to the server.

A natural approach is to submit all requests at once and let the server's scheduler handle them. However, a continuous batching server's scheduler is designed for online serving, where the queue depth is determined by external traffic. When the client floods the server with the entire workload, the scheduler operates under conditions it was not optimized for — a deep, static queue that saturates the KV cache from the start.

An alternative is to **pace** submission to match the server's KV cache capacity: the client maintains a concurrency window equal to the number of requests the KV cache can hold, submitting a new request only when a prior one completes. This keeps the scheduler in a regime where it can freely alternate between prefill and decode without sustained KV cache pressure.

We evaluate both strategies on the same workload and hardware to quantify the throughput difference.

## 2. Experimental Setup

| Parameter | Value |
|---|---|
| Model | DeepSeek-R1-Distill-Llama-70B (70.55B, LlamaForCausalLM) |
| Hardware | 12x NVIDIA A10G (24 GB GDDR6, 600 GB/s bandwidth, PCIe) |
| Topology | 3 nodes x 4 GPUs/node (AWS g5.12xlarge) |
| Parallelism | TP=4 (intra-node), PP=3 (inter-node) |
| Serving stack | vLLM 0.10.0, Ray distributed executor |
| Workload | 708 requests, fixed 1,024 input / 512 output tokens |
| Total tokens | 1,087,488 (724,992 prompt + 362,496 generation), identical for both strategies |
| KV cache concurrency | 177 (derived from server-reported cache blocks and max sequence length) |
| Instance cost | $12.29/hr (3 nodes) |

**Paced submission** uses a client-side semaphore set to 177 (the KV cache concurrency). A new request is submitted only when a prior request completes, maintaining a steady flow that matches the server's capacity.

**Flood submission** submits all 708 requests simultaneously. The server's internal scheduler manages queuing, admission, and preemption.

Both strategies use the same client, server configuration, model weights, and prompts. The only difference is the client-side concurrency control.

## 3. Results

### 3.1 Aggregate Performance

| Metric | Paced | Flood | Delta |
|---|---|---|---|
| Total throughput (tok/s) | 1,025.8 | 791.5 | -22.8% |
| Prefill throughput (tok/s) | 683.9 | 527.7 | -22.8% |
| Decode throughput (tok/s) | 341.9 | 263.8 | -22.8% |
| Elapsed time (s) | 1,060 | 1,374 | +29.6% |
| Preemptions | 37 | 268 | +624% |
| Avg SM utilization (%) | 88.3 | 83.6 | -5.3% |
| Avg memory BW utilization (%) | 29.8 | 23.0 | -22.9% |
| Cost (USD) | 3.62 | 4.69 | +29.6% |
| Cost efficiency (tok/USD) | 300,531 | 231,887 | -22.8% |

Both strategies processed the same 1,087,488 tokens on the same hardware. Flood submission achieved 22.8% lower aggregate throughput, required 29.6% more wall-clock time, and incurred 7.2x more preemptions.

### 3.2 Phase-Level Throughput

To understand where the throughput difference originates, we partition the benchmark timeline into three phases based on KV cache utilization, sampled via the Prometheus `/metrics` endpoint at 0.5-second intervals. Throughput is computed as the rate of change in the cumulative token counters (`vllm:prompt_tokens_total`, `vllm:generation_tokens_total`) between consecutive samples.

**Paced:**

| KV cache phase | Time fraction | Total tok/s | Prefill tok/s | Decode tok/s | Avg running | Avg waiting |
|---|---|---|---|---|---|---|
| < 80% | 38.3% | 2,180 | 1,811 | 369 | 140 | 17 |
| 80–99% | 50.1% | 1,377 | 761 | 616 | 174 | 2 |
| >= 99% | 11.6% | 752 | 0 | 752 | 173 | 4 |

**Flood:**

| KV cache phase | Time fraction | Total tok/s | Prefill tok/s | Decode tok/s | Avg running | Avg waiting |
|---|---|---|---|---|---|---|
| < 80% | 27.9% | 2,396 | 2,075 | 321 | 121 | 225 |
| 80–99% | 15.9% | 2,621 | 2,498 | 122 | 181 | 278 |
| >= 99% | 56.3% | 824 | 101 | 723 | 200 | 300 |

### 3.3 Temporal Behavior

Figure 1 (paced) and Figure 2 (flood) show per-GPU utilization, throughput, KV cache utilization, and scheduler queue depth over time. Red-shaded regions indicate periods where KV cache utilization exceeds 99%.

**Figure 1. Paced submission (rate-limited, concurrency = 177)**

![Paced submission timeseries](/assets/img/posts/2026-03-15-batching-strategy/paced-1.png)

**Figure 2. Flood submission (send-all, 708 requests at once)**

![Flood submission timeseries](/assets/img/posts/2026-03-15-batching-strategy/flood-1.png)

The paced strategy exhibits a periodic pattern: prefill bursts (~4,000 tok/s) when new requests are admitted, followed by decode-dominated periods (~750–1,200 tok/s) as the active batch generates output tokens and completes. KV utilization oscillates between 70% and brief peaks near 100%. The semaphore prevents sustained saturation.

The flood strategy proceeds in three distinct phases:
- **Minutes 0–5** (ramp-up): Requests flood in. Behavior resembles the paced strategy as the KV cache fills. Peak throughput reaches ~4,000 tok/s during prefill.
- **Minutes 5–14** (saturation): KV cache is pinned at 99%. Throughput drops to 650–910 tok/s. The waiting queue holds 300+ requests throughout. Preemption-driven re-prefill is visible as nonzero prefill throughput within the red-shaded regions of Figure 2.
- **Minutes 14–23** (drain): The waiting queue gradually empties. Throughput recovers intermittently before declining as the remaining requests complete.

## 4. Analysis

### 4.1 The Throughput Gap Is a Time-Allocation Effect

Within each KV cache phase, the two strategies achieve comparable throughput: 2,180 vs. 2,396 tok/s at KV < 80%, and 752 vs. 824 tok/s at KV >= 99%. Neither strategy changes the efficiency of individual forward passes — the per-phase throughput is governed by the hardware and the scheduler's batching decisions for a given cache occupancy level.

The aggregate throughput difference arises from the fraction of time spent in each phase. The paced strategy spends 11.6% of its time in the low-throughput KV-full phase. Flood submission spends 56.3% — a 4.9x increase. Because throughput in the KV-full phase is roughly 3x lower than in the mixed prefill+decode phases, the time-weighted average for flood submission is correspondingly lower.

### 4.2 Preemption and Redundant Prefill

At KV >= 99%, no new requests can be admitted — the cache is full. Under paced submission, prefill throughput at this phase is exactly zero, consistent with the scheduler blocking new admissions until space is freed by completing requests.

Under flood submission, prefill throughput at KV >= 99% is 101 tok/s, accounting for 12.3% of the phase's total throughput. Since the cache is full and no new requests can be admitted, this prefill work corresponds to re-prefilling previously preempted requests. The scheduler evicts a partially-decoded request's KV cache, re-queues it, and later re-admits it, requiring a full re-prefill of its prompt tokens.

With 268 preemptions at 1,024 tokens per prompt, the upper bound on redundant prefill is 274,432 tokens — equivalent to 37.8% of the total prompt token count being processed a second time. This compute produces no new output tokens.

### 4.3 Preemption Does Not Degrade Active Request Performance

Decode throughput at KV >= 99% is 752 tok/s (paced) and 723 tok/s (flood), a 3.9% difference. Requests that are actively decoding proceed at approximately the same rate regardless of preemption activity. The overhead of preemption is not borne by the active requests; it manifests as time spent on re-prefill that displaces productive decode work in the aggregate time budget.

### 4.4 Hardware Utilization Reflects the Phase Mix

Average memory bandwidth utilization is 29.8% (paced) and 23.0% (flood), a 22.9% relative reduction that tracks the throughput gap. During KV-full periods with preemption churn, the GPU executes compute-bound re-prefill (high SM utilization, low memory bandwidth utilization) rather than bandwidth-bound decode. The shift in workload composition — more prefill, less decode — reduces bandwidth utilization without a proportional increase in useful output.

SM utilization shows a smaller gap (88.3% vs. 83.6%) because the re-prefill work still utilizes SMs; the SMs are occupied with redundant computation rather than idle.

## 5. Discussion

The results show that for offline batch inference workloads processed through a continuous batching server, the client's batching strategy is a first-order determinant of throughput. Submitting all requests at once does not increase useful parallelism — it shifts the scheduler into a regime dominated by low-throughput decode and preemption-driven re-prefill, reducing aggregate throughput by 23% on this configuration.

The paced strategy achieves higher throughput by keeping the scheduler in a regime where it can freely alternate between prefill and decode without sustained KV cache pressure. The concurrency window — set to the KV cache capacity reported by vLLM at startup — provides this regulation with a single client-side semaphore.

**Why this matters for batch inference.** Continuous batching servers like vLLM are increasingly used not just for online serving but as execution engines for offline batch workloads (dataset annotation, synthetic data generation, bulk evaluation). In this setting, the client controls the submission pattern and can choose a strategy that matches the server's capacity. The results here show that the naive approach of submitting everything at once leaves 23% of potential throughput on the table and increases cost by 30%.

**The concurrency target is computable.** vLLM reports the KV cache size in its startup logs (e.g., "GPU KV cache size: 275,920 tokens"). Dividing by the maximum sequence length yields the concurrency target. No profiling or tuning is required — the optimal semaphore value is deterministic for a given model, hardware, and sequence length configuration.

**Generality.** The mechanism identified here — KV cache saturation leading to preemption churn and time spent in a low-throughput phase — is not specific to this model or hardware. It applies to any configuration where the total request count exceeds the KV cache concurrency. The magnitude of the throughput gap depends on the ratio of workload size to cache capacity, the prompt-to-output length ratio, and the preemption cost (proportional to prompt length).
