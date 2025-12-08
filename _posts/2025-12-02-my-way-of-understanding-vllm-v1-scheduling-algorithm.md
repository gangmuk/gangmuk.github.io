---
title: "My Way of Understanding vLLM V1 Scheduling Algorithm"
date: 2025-12-02
categories: [vllm, scheduling, memory management]
tags: [vllm, scheduling, memory management]
---
<!-- 
- [vLLM V1 Scheduling and Memory Management](#vllm-v1-scheduling-and-memory-management)
  - [Introduction](#introduction)
  - [Overview of Components](#overview-of-components)
      - [Scheduler](#scheduler)
      - [KVCacheManager](#kvcachemanager)
      - [Configs \& Variables](#configs--variables)
  - [Request Lifecycle](#request-lifecycle)
    - [Request Arrives](#request-arrives)
    - [Scheduler Iteration](#scheduler-iteration)
      - [Phase 1: Scheduling Running Requests](#phase-1-scheduling-running-requests)
      - [Phase 2: Scheduling Waiting Requests](#phase-2-scheduling-waiting-requests)
    - [Request Completion](#request-completion)
  - [Memory Allocation Details](#memory-allocation-details)
    - [Block Layout](#block-layout)
    - [Allocation Steps](#allocation-steps)
    - [Reference Counting](#reference-counting)
    - [Lazy Hash Eviction](#lazy-hash-eviction)
  - [Example: Mixed prefill/decode with chunked prefill](#example-mixed-prefilldecode-with-chunked-prefill)
  - [When could preemption happen?](#when-could-preemption-happen) -->

# vLLM V1 Scheduling and Memory Management

## Introduction

vLLM has been a de-facto LLM serving engine. Though it is highly complicated system with many moving parts, the scheduler is the core of the system. This blog is the polished version of my version of understanding on vLLM scheduling algorithm. (my version as in everybody has different way to understand the same thing even if the target is the same). 

Why am I writing this blog post? There are aleady many blog posts that explain the vLLM scheduling. But it is either too shallow, incomplete, or deep and complete but not in a way that I wish. 
Why am I writing this blog post? There are already many blog posts that explain the vLLM scheduling. <span class="side-note">Alexa Gordic's blog post on vLLM is great (https://alexagordic.github.io/vllm-scheduler/). It is more in details. Mine focuses on the scheduling algorithm.</span> But it is either too shallow, incomplete, or deep and complete but not in a way that I wish.


**What I promise to you in this post.**
- What happens in vllm from the time a request arrives to the time it is completed in details.
- My educated guess on why vllm chooses this specific scheduling algorithm.
- Performance implication of the vllm scheduling algorithm in different scenarios.

**What it does not have**
- Other parts of vLLM e.g., tokenizer, how exact paged attention works, model loading, kernel launch, etc.
- How the LLM model is computed in the GPU.
- Benchmark numbers.

I trimmed out others to more cleanly understand the scheduling algorithm.

It has the reason (philosophy) why vllm chooses this specific scheduling algorithm and the complete journey of a request from arrival to completion, how memory allocation and preemption work, and the performance implication of the vllm scheduling algorithm in different scenarios includingn preemption cases.

Let's start by defining the core components.

## Overview of Components

#### Scheduler
The scheduler runs every iteration (one GPU kernel launch) to:
- Decide which requests to process
- Determine how many tokens to schedule per request
- Trigger preemption when memory runs out

It maintains two queues:
- **Waiting queue**: Newly arrived requests (FIFO for FCFS, priority heap for Priority).
- **Running queue**: Requests currently being executed.

#### KVCacheManager
Manages KV cache blocks for all requests:
- Allocates memory blocks when scheduler needs them.
- Checks prefix cache for reusable blocks.
- Frees blocks when requests complete or are preempted.

**KV Block**
KV is divided into fixed-size blocks (typically 16 tokens). Each block contains:
- Physical memory for key/value tensors.
- `block_hash`: SHA256 hash for prefix caching.
- `ref_cnt`: Reference counter (how many requests use this block).

**Block States:**
- **Free**: Available for allocation (in free block queue).
- **Allocated**: Assigned to a request.
- **Cached**: Has valid hash, can be matched by prefix cache.

Note: A block can be free but still has kv content in it. It happens if kv blocks were freed because the request having them was preempted but only a part of freed blocks are used by another request who preempted it. Then the remaining freed blocks are in free block queue but still has kv content in it. So it can go into allocated state again without computation if it is hit.

#### Configs & Variables
- `num_computed_tokens`: The number of tokens that have been processed/computed by the model so far.
- `num_tokens`: The current length of `all_token_ids` (input prompt tokens + output tokens generated so far).
- `num_output_placeholders`: Used in async scheduling to reserve space for potential speculative tokens (draft tokens).
- `num_prompt_tokens`: The length of the initial prompt.
- `max_tokens`: The maximum number of *new* tokens to generate (output limit).
- `max_model_len`: The model's absolute context window limit (prompt + output).
- `token_budget`: The maximum number of tokens the scheduler can schedule in the current iteration/step.

## Request Lifecycle
Now we will traces a request's lifecycle from arrival to completion, covering how the scheduler decides to schedule the request.

### Request Arrives

When a new request arrives, it first enters the waiting queue and the waiting queue in vllm is strict FIFO. And the request state is `WAITING`. And each request has two attributes `num_computed_tokens = 0` that tracks the number of tokens that have been computed and `num_tokens` that tracks the total number of tokens in the request. The request sits in the waiting queue until the scheduler schedules it to the running queue.

### Scheduler Iteration

At the high level, vLLM schedules a batch of tokens in a lock-step manner. All tokens in the batch are executed as a single GPU kernel, regardless of whether there's a single request or multiple requests. One iteration equals one GPU kernel launch.

At the start of each iteration (which will be launched as one GPU kernel), the scheduler resets the `token_budget` to `max_num_batched_tokens`. It then proceeds in two distinct phases to fill this budget.

#### vllm's scheduler algorithm's design choices
vllm scheduler made certain scheduling choices. Before diving into the detailed scheduling logic, let's see what I mean by that. It will help you picture why the scheduling algorithm is designed in such a way.

1.  Batch & Lock-Step Execution: vLLM is a batch scheduler. It groups tokens from multiple requests into a single batch to execute as one GPU kernel launch. This maximizes GPU compute saturation (throughput) at the cost of coupling their execution timing.
2.  Run-to-Completion (mostly): Unlike the Linux CFS (Completely Fair Scheduler) which aggressively context-switches processes to ensure fairness (giving every process a tiny "time slice" of CPU), vLLM tries to keep a request in the `Running` state until it finishes.
    * *Why?*
        1.  High Switch Cost: In a CPU, context switching is cheap (nanoseconds). In LLMs, "context" is the KV Cache—gigabytes of data. Swapping a request out means moving GBs of data to CPU RAM, which is excruciatingly slow.
        2.  Equal Priority: Since most inference requests have the same priority, pausing Request A to run Request B (time-slicing) just delays Request A without adding value, while incurring the swap penalty that delays *both*. Run-to-completion minimizes the average completion time for everyone.
3.  Continuous Batching (Iteration-Level Scheduling): Traditional schedulers might wait to build a batch. vLLM uses "iteration-level" scheduling, meaning it can inject new requests into the *next* token generation step of running requests immediately. This solves the "head-of-line blocking" problem where short requests got stuck behind long ones in older batching systems.
4.  Optimistic Memory Allocation (Zero-Reservation):
    *   *design choice:* Never reserve memory for the *future* tokens of a request. Only allocate for the token being generated *right now*.
    *   *Why?* LLM output lengths are highly unpredictable. Pessimistically reserving memory for `max_tokens` (e.g., 4096) for every request would drastically limit concurrency (batch size). vLLM allocates blocks just-in-time. If the system runs out of memory, it relies on Reactive Preemption (pausing a request) as a safety valve. This trades a rare preemption cost for a massive increase in average concurrency.
5.  Decode-First Prioritization (Heterogeneous Workload Packing):
    * *design choice:* The scheduler strictly prioritizes the `RUNNING` queue (Decode phase) over the `WAITING` queue (Prefill phase).
    *   *Why?*
        1.  QoS: It protects active users (Inter-Token Latency) from stuttering when new users join (Time to First Token).
        2.  Utilization: It enables Heterogeneous Packing. Decodes are memory-bandwidth bound (leaving Compute units idle). Prefills are compute-bound. By scheduling Decodes first and filling the *remaining* budget with a Prefill chunk, vLLM "hides" the memory access latency of decodes behind the heavy arithmetic of prefills, maximizing total hardware efficiency.


#### **Phase 1: Scheduling Running Requests**

The scheduler processes all requests currently in the `RUNNING` queue. It iterates through them one by one in FCFS order (based on when they were admitted).
It has two steps, 1. Calculate Tokens and 2. Allocate & Schedule. In *1. Calculate Tokens*, the scheduler determines the number of tokens to execute (`num_tokens`). In *2. Allocate & Schedule*, the scheduler attempts to allocate KV cache blocks for these tokens.
The following steps are performed sequentially for each request before moving to the next request.

**1. Calculate Tokens**
The scheduler determines the number of tokens to execute (`num_tokens`) by starting with the base calculation: `num_tokens = min(tokens_remaining, long_prefill_token_threshold, token_budget, max_model_len - 1 - num_computed_tokens)`
* Standard Prefill: `num_tokens` = Total Prompt Length (since `computed=0`).
* Chunked Prefill (Resumed): `num_tokens` = Remaining Prompt Length (e.g., `2000 - 512 = 1488`).
* Standard Decode: `num_tokens` = 1.
* Speculative Decode: `num_tokens` = 1 + K (where K is the number of speculative/draft tokens, e.g., 5).

It applies four filters in order:

1) **Completion Check (`max_tokens`):**
- **Purpose:** Prevents over-scheduling when a request is effectively finished but still has "placeholder" tokens from a previous speculative step.
- **Logic:** If the request has effectively reached its completion limit (`max_tokens`), the scheduler skips it entirely for this iteration.
- **Example:** A request with `max_tokens=100` has `num_computed=98` and `2` speculative placeholders. Since `98 + 2 >= 100`, it is skipped.

2) **Fairness Threshold between requests (`long_prefill_token_threshold`):**
- **Purpose:** Prevents a single long request from monopolizing the GPU for too long, which would starve other requests. It forces Chunking—splitting a large prefill into smaller batches across multiple iterations.
- **Logic:** If `required_tokens` (remaining work: `num_tokens - num_computed_tokens`) exceeds the threshold, `num_tokens` is capped (reduced) to equal the threshold.
- **Example:** `long_prefill_token_threshold=512`. `Request A` needs to process 2000 tokens. The scheduler only allows 512 tokens in this step. The remaining 1488 tokens must wait for future iterations.

3) **Token Budget (`max_num_batched_tokens`):**
- **Purpose:**
    - **Latency Control:** Limits the total work in one kernel launch to keep execution time short (crucial for Inter-Token Latency).
    - **System Capacity (KV Cache & Compute):** While higher batch sizes generally improve throughput, there are diminishing returns rooted in GPU microarchitecture.
    - *SM Saturation (Compute Bound):* The NVIDIA A100 has 108 Streaming Multiprocessors (SMs). To maximize utilization, we need enough thread blocks to fill these SMs ("waves"). Once all SMs are fully occupied, adding more tokens linearly increases execution time (latency) without improving throughput (tokens/sec).
    - *FlashAttention Tile Quantization:* FlashAttention splits computation into fixed-size tiles (e.g., 128x64) to fit into the SM's SRAM (192KB). If the batch size creates a "tail effect"—where the total number of tiles isn't a multiple of 108—you get a "partial wave" where some SMs sit idle while others finish, reducing efficiency.
    - *Example:* For a Llama 3 8B model on an A100, throughput often saturates at a batch size of 128-256 sequences (during decode). For prefill, allowing extremely large batches (e.g., >32k tokens) yields minimal throughput gains but causes massive Inter-Token Latency (ITL) spikes for concurrent decode requests. `max_num_batched_tokens` caps this to keep the system in the efficient, low-latency zone.
- **Logic:** If the request needs more tokens than the *remaining* budget (which starts at `max_num_batched_tokens` and decreases as other requests are scheduled), it consumes *all* the remaining budget.
- **Example:** `max_num_batched_tokens=2048`. `Request A` is scheduled for 512 tokens. `Remaining Budget = 1536`. `Request B` (Waiting) needs 2000 tokens. It is capped at 1536 tokens (the remaining budget). It cannot run fully in this step.

4) **Model Context Limit (`max_model_len`):**
- **Purpose:** Hard safety check for model context window.
- **Logic:** `num_tokens` is capped to ensure the total sequence length stays within `max_model_len`.
- **Example:** `max_model_len=8192`. A request asks to generate past this limit. The scheduler caps the tokens so the total length is exactly 8192.

**2. Allocate & Schedule:**
  - For the requests that passed the above filters, the scheduler attempts to allocate physical KV cache blocks for these tokens.
  - *High-Level Allocation Logic:* The scheduler asks the `KVCacheManager` for the needed blocks. The manager first checks the Prefix Cache (to reuse existing blocks with the same token sequence) and then pulls from the Free Block Queue if needed. (The full mechanics of block layout, hashing, and LRU eviction are detailed in the Memory Allocation Details section later).
  - Success: If blocks are successfully allocated, the request is officially scheduled for this iteration. The `token_budget` is reduced.
  - Failure (Preemption Loop): If the system runs out of free blocks, the scheduler *cannot* schedule the current request without freeing up space. (See the Preemption Analysis section below for real-world triggers like *Decode Accumulation* and *Chunked Prefill*). It enters a preemption loop:
    - Logic: It preempts the lowest priority request (or most recently added if FCFS) and retries the allocation for the current request. This repeats until allocation succeeds or the current request itself becomes the victim.
    - If Self-Preemption: If the victim selection logic picks the current request itself (e.g., because it's the lowest priority), the loop breaks. The request is NOT scheduled in this iteration and waits for the next one. It does *not* execute the tokens.
    - If Success: The victim remains preempted (moved to waiting queue), and the current request proceeds to be scheduled.
  - Next Step: If the request is successfully scheduled, the scheduler moves to the next request in the running queue. Once all running requests are processed, if (and only if) no preemptions occurred, it proceeds to Phase 2 (Waiting Requests).
        

#### **Phase 2: Scheduling Waiting Requests**

If it reaches here, awesome! It means all the running requests are successfully scheduled without preemption. If even a single running request triggered preemption, Phase 2 is skipped entirely. It makes sense since if there was a preemption during running queue scheduling, then it means it was not even able to schedule all the running request without memory pressure. Hence, in that case, there is no point of trying to schedule new requests from the waiting queue.

Let's see if we can schedule more!
The scheduling algorithm for waiting requests is almost similar to the running queue scheduling, but with some differences.

1.  Check Constraints: It iterates through the `WAITING` queue (FIFO or Priority order). It stops if the `token_budget` is exhausted or the `RUNNING` queue has reached its size limit (`max_num_seqs`).
2.  Prefix Cache Lookup: For a request being considered for the first time, the scheduler checks the prefix cache to see if any initial blocks can be reused from previous requests.
3.  Calculate Tokens: The logic is similar to Phase 1, but simpler because waiting requests are essentially starting their execution (processing the initial prompt).
    - *Note:* Technically, a request could be in the waiting queue with `num_computed_tokens > 0` if it was preempted previously. In that case, it is resuming, but for scheduling purposes, it's treated as a batch of tokens to be processed (just like a prefill).
    - It calculates the required tokens (`total_len - cached_len`).
    - It applies the same Fairness Threshold and Token Budget caps to ensure the prefill doesn't monopolize the system.
    - *Result:* If the request is huge (e.g., 2000 tokens) and the budget is small (e.g., 512 remaining), it gets chunked—only the first 512 tokens are scheduled, and the rest wait.
4.  Allocate: It attempts to allocate blocks for the request.
    - Success: If successful, the request status changes to `RUNNING`, it is moved to the running queue, and the `token_budget` is reduced.
    - Failure: (difference vs Phase 1) If allocation fails here, the scheduler stops admitting new requests immediately. It does not trigger preemption.
        - *Why?* We never kill an active, running request just to let a new one in. The waiting request simply waits for the next iteration when more memory might be available.

Finally, the scheduler returns the final batch of scheduled requests to be executed by the GPU.

### Request Completion

When a request reaches a stop condition:
- EOS token generated
- Maximum output length reached
- Stop strings matched

**Completion process:**
1. Request removed from running queue
2. KVCacheManager frees all request's blocks
3. For each block: `ref_cnt--`
4. When `ref_cnt = 0`: block moved to free queue (appended to back)
5. Block hash preserved (lazy eviction)
6. Cache remains valid until block reallocated

This enables future requests to benefit from the cached blocks if they share common prefixes.

## Memory Allocation Details
`allocate_slots()` is the function that allocates blocks for a request. It is called when the scheduler attempts to allocate blocks for a request in Phase 1 or Phase 2.
When `allocate_slots()` is called, the KVCacheManager performs this process:

### Block Layout

For a request being scheduled, blocks are organized as:
- Computed blocks: Already allocated from previous iterations
- New computed blocks: From prefix cache hit, just discovered
- New blocks: Freshly allocated for `num_tokens`
- Lookahead blocks: For speculative decoding (if enabled)

### Allocation Steps

1. **Calculate blocks needed:**
   `ceil(num_tokens / block_size)`

2. **Check prefix cache:**
   - For cached tokens, look up block hashes in cache dictionary
   - If found: increment `ref_cnt` on existing blocks, reuse them
   - If not found: need to allocate new blocks

3. **Allocate from free queue:**
   - Pop blocks from front of free block queue (LRU order)
   - Assign to request
   - Set initial `ref_cnt = 1`

4. **Return result:**
   - Success: return allocated blocks
   - Failure: return None (triggers preemption for running requests)

### Reference Counting

Blocks can be shared across multiple requests via prefix caching. The `ref_cnt` tracks how many requests use each block.

**When block is used:**
- `ref_cnt++`

**When request finishes or is preempted:**
- `ref_cnt--`

**When ref_cnt reaches 0:**
- Block moved to free queue (appended to back)
- Block hash **NOT immediately cleared** (lazy eviction)

### Lazy Hash Eviction

When a block is freed (`ref_cnt = 0`), its hash remains in the cache dictionary. The hash is only cleared when the block is actually reallocated for a different token sequence.

**Why?** This enables cache hits even after preemption:

Timeline example:
- T1: Request A computes tokens, uses blocks [B1, B2, B3] with hashes [H1, H2, H3]
- T2: Request A preempted, blocks freed → [B1, B2, B3] added to free queue, hashes intact
- T3: Request B allocates, takes B1 → H1 cleared (block repurposed)
- T4: Request A readmitted, looks for [H1, H2, H3] → finds H2, H3 still cached

The brief window between freeing and reallocation allows preempted requests to benefit from their cached work if rescheduled quickly.


## Example: Mixed prefill/decode with chunked prefill

Let's see an example to make it more concrete.

Configuration: `max_num_batched_tokens = 2048`, `long_prefill_token_threshold = 1024`

Running queue state:
- R1: Prefill (3000 tokens remaining), admitted first
- R2: Decode (1 token), admitted second
- R3: Prefill (500 tokens remaining), admitted third
- R4: Decode (1 token), admitted fourth

**Iteration processing:**

**R1 (Prefill, 3000 tokens):**
- Tokens to process = `min(3000, 1024 threshold, 2048 budget)` = **1024 tokens**
- Allocate blocks for 1024 tokens
- If allocation **succeeds**: Schedule 1024 tokens, budget = 2048 - 1024 = **1024 remaining**
- If allocation **fails**: Enter preemption loop (see below)

**R2 (Decode):**
- Tokens to process = **1 token**
- Allocate blocks for 1 token
- If allocation **succeeds**: Schedule 1 token, budget = 1024 - 1 = **1023 remaining**

**R3 (Prefill, 500 tokens):**
- Tokens to process = `min(500, 1024 threshold, 1023 budget)` = **500 tokens**
- Allocate blocks for 500 tokens
- If allocation **succeeds**: Schedule 500 tokens, budget = 1023 - 500 = **523 remaining**

**R4 (Decode):**
- Tokens to process = **1 token**
- Allocate blocks for 1 token
- If allocation **succeeds**: Schedule 1 token, budget = 523 - 1 = **522 remaining**

**Result batch:** [R1: 1024 tokens, R2: 1 token, R3: 500 tokens, R4: 1 token] → 1526 total tokens in one kernel
 with fresh capacity

## When could preemption happen?

**1. Decode Accumulation**

Multiple concurrent requests generating output tokens. Each token requires small additional KV cache. Over many iterations, this accumulates until memory exhausted.

Example:
- 10 requests each generate 100 tokens
- Per request: 100 × 0.05 = 5 blocks
- Total: 50 blocks consumed

Decode is unbounded. Requests can generate thousands of tokens. Memory fills gradually over minutes until preemption triggered.

**2. Traffic Bursts**

Sudden spike in concurrent arrivals. Scheduler rapidly admits requests to running queue, over-subscribing memory before earlier requests complete.

Example:
- Iteration 1: Admit 5 requests, allocate 500 blocks
- Iteration 2: Admit 5 more, total 1000 blocks
- Iterations 3-10: All 10 decode, accumulating blocks
- Iteration 15: Memory exhausted, preemption begins

**3. Large Individual Requests (Chunked Prefill Case)**

*   **Scenario:** A request with a huge prompt (e.g., 10k tokens) is being processed with **Chunked Prefill**.
    *   *Iteration 1:* Admitted for the first 512 tokens. Allocates ~32 blocks. Moves to `RUNNING`.
    *   *Iteration 2:* Needs to process the next 512 tokens. Needs to allocate **another** ~32 blocks.
*   **Impact:** This is now a **Running Request** demanding new memory.
*   **Result:** If the system memory saturated in the meantime (e.g., due to other decode requests growing), this allocation for the *second chunk* might fail. Since it's a running request, it triggers preemption. It might kill smaller decode requests to secure space for its next chunk.
