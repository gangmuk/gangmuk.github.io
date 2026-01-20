---
layout: post
title: "Why Batch Processing Destroyed My Threading Overhead"
tags: [asyncio, threadpool, performance, debugging, ml-inference]
date: 2025-05-14
category: blog
---

Last week I debugged a GPU prediction service that was taking 6+ seconds to respond. The predictions themselves? About 200ms total. I had timestamps everywhere but couldn't figure out where the other 5.8 seconds were going.

Turns out I was measuring the wrong thing.

## The Problem

We built a latency prediction service with FastAPI and XGBoost. Individual predictions were fast—10-30ms on GPU. But somehow our API was taking 6-8 seconds to respond.

Here's roughly what the code looked like:

```python
from fastapi import FastAPI
import asyncio
from concurrent.futures import ThreadPoolExecutor
import xgboost as xgb
import pandas as pd
import time

app = FastAPI()
thread_pool = ThreadPoolExecutor(max_workers=8)
model = xgb.XGBRegressor()  # loaded model

def process_prediction(input_data):
    df = pd.DataFrame([input_data])
    prediction = model.predict(df)[0]
    return {"prediction": float(prediction)}

@app.post("/predict")
async def predict(inputs: list[dict]):
    start = time.time()

    tasks = [
        asyncio.create_task(asyncio.to_thread(process_prediction, data))
        for data in inputs
    ]

    results = await asyncio.gather(*tasks)

    return {
        "predictions": results,
        "total_time_ms": (time.time() - start) * 1000
    }
```

Looks fine, right? FastAPI's async, we're using threads for CPU work, gathering results. Standard stuff.

But with 10 inputs:

```
Total time: 6583ms
Prediction times: [23ms, 19ms, 28ms, 15ms, 21ms, 18ms, 16ms, 22ms, 20ms, 17ms]
```

200ms of work taking 6.5 seconds.

## Finding the Wrong Culprit

I added more timing:

```python
@app.post("/predict")
async def predict(inputs: list[dict]):
    start = time.time()

    # Create tasks
    task_start = time.time()
    tasks = [
        asyncio.create_task(asyncio.to_thread(process_prediction, data))
        for data in inputs
    ]
    task_creation = (time.time() - task_start) * 1000

    # Wait for results
    gather_start = time.time()
    results = await asyncio.gather(*tasks)
    gather_time = (time.time() - gather_start) * 1000

    return {
        "predictions": results,
        "task_creation_ms": task_creation,
        "gather_ms": gather_time,
        "total_ms": (time.time() - start) * 1000
    }
```

Output:
```
Task creation: 3ms
Gather: 6578ms
Total: 6583ms
```

So `asyncio.gather()` was taking 6.5 seconds? That's where I blamed asyncio and threads not playing well together.

Looking at the detailed timing from the actual service, I saw things like:
- 670ms overhead before any work started
- 900ms+ delay between predictions completing and results being collected
- Overall way more time than the actual prediction work

I wrote some benchmarks (simplified from the real code) and saw what looked like massive overhead:

```python
# Simulated benchmark (20ms tasks)
Asyncio + ThreadPoolExecutor: 2451ms
Direct ThreadPoolExecutor: 25ms
```

That looks like ~100x overhead from combining asyncio and threads!

## What Actually Happened

**I was wrong about the root cause.**

I recently re-ran proper benchmarks to verify this claim. Using the exact same patterns from the original code:

```
asyncio.to_thread():        24.6ms
Direct ThreadPoolExecutor:  25.5ms
```

No 100x overhead. Basically identical performance.

Even in pathological cases (100 tiny tasks, constrained thread pools, etc.), the worst overhead I could create was maybe 2x, not 100x.

**So what was really wrong?** I don't know for certain. The original code is gone. But likely candidates:

1. **Thread pool misconfiguration** - Maybe exhausted, maybe wrong size
2. **GIL contention** - XGBoost competing for the GIL
3. **Something in the actual code** - Logging, data serialization, some bottleneck I didn't show in the simplified examples
4. **GPU/XGBoost specifics** - Thread competition for GPU access

The timing breakdown showed 670ms just "setting up ThreadPoolExecutor" which doesn't make sense if we had a global pool. Something else was wrong.

## The Real Solution: Batch Processing

While I was chasing asyncio overhead, I tried batch processing:

```python
@app.post("/predict")
async def predict_batch(inputs: list[dict]):
    start = time.time()

    # Single batch prediction
    df = pd.DataFrame(inputs)
    predictions = model.predict(df)

    results = [{"prediction": float(p)} for p in predictions]

    return {
        "predictions": results,
        "total_time_ms": (time.time() - start) * 1000
    }
```

Results from the actual service:

```
DataFrame creation: <1ms
Model prediction: ~5ms per target
Total: 11ms for 7 predictions
```

Compare to original: 3087ms → 11ms

**280x speedup.**

Not because asyncio was slow. Because **threading individual predictions was the wrong pattern entirely.**

## Why Batch Processing Won

ML models are designed for batches:

1. **Vectorized operations** - NumPy/pandas operate on arrays efficiently
2. **GPU utilization** - GPUs want large batches to saturate compute
3. **No thread overhead** - No context switching, no synchronization
4. **Cache efficiency** - Better memory access patterns

Threading made sense intuitively (parallelize the predictions!), but it fought against how ML inference actually works.

## Lessons

**1. Measure, but measure the right thing**

I had tons of timestamps but still misdiagnosed the problem. The timing showed asyncio.gather() taking 6.5 seconds, but that's just where the thread pool wait happened to be. The real issue was somewhere else.

**2. Understand your tools**

I initially blamed asyncio+threads for having inherent overhead. That's not true—they work fine together when properly configured. My benchmarks now show <5% overhead in normal usage.

But also: for ML inference, neither asyncio nor threading is the right tool. Batch processing is.

**3. Question your architecture**

Threading seemed like the obvious way to parallelize predictions. But ML models already parallelize internally. Adding another layer of parallelism just created overhead.

**4. The real numbers matter**

When I wrote the original version of this analysis, I claimed 100x overhead from asyncio+threads. But I couldn't reproduce it in clean benchmarks. That means either:
- My original measurement was wrong
- Something environment-specific caused it
- I was measuring something else entirely

Without the original code, I can't say for sure. So take this as a lesson: if you can't reproduce it in isolation, you might be blaming the wrong thing.

## When to Use What

Based on what actually works:

**Use asyncio** for I/O-bound concurrency (network calls, file operations, databases)

**Use ThreadPoolExecutor** for CPU-bound work that needs true parallelism

**Use batch processing** for ML inference or anything that naturally operates on arrays

**Avoid** creating threading layers over things that are already parallelized (ML models, vector operations, GPU workloads)

## The Bottom Line

I spent days debugging "asyncio overhead" that probably didn't exist. The real problem was architectural—threading individual predictions when the model could handle batches natively.

The 280x improvement came from choosing the right pattern, not from removing asyncio. If you're doing ML inference, start with batch processing. It's not just faster—it's the right way to use the tools.

And if you're debugging performance: be skeptical of your own conclusions. I had data showing asyncio.gather() taking 6.5 seconds, but that didn't mean asyncio was the problem. Sometimes the timestamps lie about causation.
