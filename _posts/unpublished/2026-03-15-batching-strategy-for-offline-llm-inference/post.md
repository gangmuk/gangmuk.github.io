---
layout: post
title: "Batching Strategy for Offline LLM Inference"
date: 2026-03-15
tags: [vLLM, LLM inference, batching, KV cache, throughput]
category: blog
---

# Batching Strategy for Offline LLM Inference

## Batch inference vs. online serving

Most writing about LLM inference focuses on online serving — you have a live service, users are waiting, and you optimize for latency: time to first token, time per output token, tail latencies. vLLM, TensorRT-LLM, SGLang — they're all primarily built for this.

- **Synthetic data generation**: generating fine-tuning datasets, distillation outputs, augmentation
But a large chunk of real LLM usage doesn't have a human in the loop at all. You have a fixed dataset and you need to run the model over all of it. Example workload can be anything with bulk input that does not have tight SLO, for example, *'Process my input file which has 10000 input prompt requests over night (~10h SLO)'*. Specific use cases could be code review over night, offline summarization, processing documents, logs, etc. Or it can be an aggregated set of many users' inference requests which has loose SLO (e.g., a set of requests like *'fix my code when I sleep until tomorrow morning'*).

In these workloads the metric is different. Nobody is waiting for individual responses, so latency doesn't matter. What matters is **throughput** and if you're running them on cloud, then **cost per token** is also important metric. If one system can process the same workload at a lower cost while satisfying the SLO, then it is a better batch inference system.

There are many different aspects that we can optimize them for batch inference. What GPUs to use, what parallelism to use, what many parallelism degree to use (which I will talk about in this series). The question I wanted to answer in this post specifically is: *How should we submit a batch of requests to a vLLM server to maximize throughput?*

Here the keyword is *'how to submit'* and it means there will be a client or scheduler which takes requests (promopt) from task pool and send them to the vLLM server. How many requests should be submitted at once? Should we dump all at once? Or should we submit them one by one? Or should we submit them in a certain batch size? If we are going to send them in a certain batch size, how many requests should be in a batch? and what should be the rate of submitting the batches? Or does it even matter at the first place? This blog post will answer it based on real benchmark results run on cloud with vLLM.

Btw, I won't talk about in what order to submit them in this post. It is another interesting question and I will talk about it in another post hopefully soon...

## The benchmark setup

- vLLM 0.10.0
- DeepSeek-R1-Distill-Llama-70B, FP16
- AWS g5.12xlarge, (NVIDIA A10G)
- Tensor Parallelism: 4, Pipeline Parallelism: 3
- Input token length: 1024
- Output token length: 512
- Number of requests: 708

## Two strategies to submit the requests

Everything else identical except the way that the requests are submitted.

**all-at-once**: submit all 708 requests at once. The vLLM server will do what it is supposed to do with its scheduler and kv cache manager.

**paced**: submit a batch of requests at a time and wait for the previous batch to complete before submitting the next batch.

The batch size is 177 which was calculated based on workload input/output token length and vLLM's total KV cache size in tokens. Total kv cache size in tokesn divided by max sequence length in workload gives the number of requests that can be simultaneously active.

## Why this matters: the KV cache and preemption

vLLM's KV cache has a fixed capacity determined by GPU memory. Once it fills up, the scheduler can't admit new requests. What it does instead is **preempt**: it evicts a partially-decoded request's KV cache to free space, re-queues that request, and later re-admits it — which requires re-running the full prefill from scratch. That re-prefill burns real compute while producing zero new output tokens.

In online serving this is fine — request traffic self-regulates and the KV cache pressure ebbs and flows. In offline inference, if you dump your entire workload at once, you force a permanently deep queue. The scheduler ends up with the KV cache pinned at 100% for most of the run, preempting in a loop. The paced strategy avoids this by keeping exactly enough in-flight requests to fill the cache — no more.

## Setup

| Parameter | Value |
|---|---|
| Model | DeepSeek-R1-Distill-Llama-70B (70.55B, LlamaForCausalLM) |
| Hardware | 12x NVIDIA A10G (24 GB, 600 GB/s, PCIe) |
| Topology | 3 nodes x 4 GPUs (AWS g5.12xlarge) |
| Parallelism | TP=4, PP=3 |
| Serving stack | vLLM 0.10.0, Ray distributed executor |
| Workload | 708 requests, 1,024 input / 512 output tokens each |
| Total tokens | 1,087,488 — identical for both strategies |
| KV cache concurrency | 177 |
| Instance cost | $12.29/hr (3 nodes) |

## Results

| Metric | Paced | Flood | Delta |
|---|---|---|---|
| Total throughput (tok/s) | 1,025.8 | 791.5 | -22.8% |
| Elapsed time (s) | 1,060 | 1,374 | +29.6% |
| Preemptions | 37 | 268 | +624% |
| Avg SM utilization (%) | 88.3 | 83.6 | -5.3% |
| Avg memory BW utilization (%) | 29.8 | 23.0 | -22.9% |
| Cost (USD) | 3.62 | 4.69 | +29.6% |
| Cost efficiency (tok/USD) | 300,531 | 231,887 | -22.8% |

Same hardware, same tokens, same weights. Flood hit 7.2x more preemptions, ran 5 minutes 14 seconds longer, and cost $1.07 more per run.

## Where the time goes

The throughput difference isn't about per-forward-pass efficiency — both strategies are running the same model on the same hardware. The difference is about which **phase** you're spending time in.

I bucketed the timeline by KV cache utilization and computed throughput in each bucket:

**Paced:**

| KV cache phase | Time fraction | Total tok/s | Prefill tok/s | Decode tok/s | Avg running | Avg waiting |
|---|---|---|---|---|---|---|
| < 80% | 38.3% | 2,180 | 1,811 | 369 | 140 | 17 |
| 80–99% | 53.7% | 1,377 | 761 | 616 | 174 | 2 |
| >= 99% | 8.0% | 752 | 0 | 752 | 173 | 4 |

**Flood:**

| KV cache phase | Time fraction | Total tok/s | Prefill tok/s | Decode tok/s | Avg running | Avg waiting |
|---|---|---|---|---|---|---|
| < 80% | 27.9% | 2,396 | 2,075 | 321 | 121 | 225 |
| 80–99% | 24.1% | 2,621 | 2,498 | 122 | 181 | 278 |
| >= 99% | 48.0% | 824 | 101 | 723 | 200 | 292 |

Within each phase, the two strategies are close — 2,180 vs. 2,396 tok/s when KV < 80%, 752 vs. 824 tok/s when KV >= 99%. The gap is entirely about time allocation: paced spends 8% of its time in the KV-full, low-throughput regime. Flood spends 48% there — 6x more. Since throughput in that phase is roughly 3x lower than the mixed prefill+decode phases, the time-weighted average collapses.

## What it looks like

The paced run (Figure 1) has a clean periodic pattern. Each cycle: a burst of prefill at ~4,000 tok/s as new requests get admitted, then a decode-dominated stretch at 750–1,200 tok/s as the batch drains. KV utilization oscillates, touching 100% only briefly — just 8% of the 17m 40s run. The semaphore prevents it from staying full.

**Figure 1. Paced submission (concurrency = 177)**

![Paced submission timeseries](/assets/img/posts/2026-03-15-batching-strategy/paced-1.png)

The flood run (Figure 2) is three phases. Minutes 0–5 look normal — requests flood in, KV cache fills, same burst prefill behavior. Then from minutes 5–15 the KV cache is pinned at 99%, throughput drops to 650–910 tok/s, and the waiting queue averages ~290 requests, peaking above 700 early in the saturation phase. The red shading in the throughput plot marks the preemption zone. Minutes 15–23 are a gradual drain as the queue finally empties.

**Figure 2. Flood submission (708 requests at once)**

![Flood submission timeseries](/assets/img/posts/2026-03-15-batching-strategy/flood-1.png)

## The preemption tax

When KV >= 99%, no new requests can be admitted. Under paced, prefill throughput at this phase is zero — the scheduler just waits for completions to free cache space.

Under flood, prefill throughput at KV >= 99% is still 101 tok/s, which is 12.3% of the phase's total output. Since the cache is full and no new requests can get in, that prefill work is entirely **re-prefill** from preempted requests. With 268 preemptions at 1,024 tokens each, the upper bound on wasted prefill is 274,432 tokens — 37.8% of total prompt tokens processed a second time, producing nothing.

The memory BW gap (29.8% vs. 23.0%) reflects this directly. During KV-full periods, the GPU is doing compute-bound re-prefill instead of bandwidth-bound decode. SM utilization barely changes (88.3% vs. 83.6%) because the SMs are still busy — just on redundant work.

## Takeaway

For offline batch inference through vLLM, use a semaphore. The concurrency target is `KV cache tokens / max sequence length`. vLLM logs the KV cache size at startup ("GPU KV cache size: X tokens") — no profiling needed, the number is deterministic for a given model, hardware, and sequence length.

The mechanism generalizes: any time your total request count exceeds the KV cache concurrency, you'll end up in this regime. How bad it is depends on the ratio of workload size to cache capacity and on prompt length (longer prompts = more expensive re-prefill). But the fix is always the same one-liner.
