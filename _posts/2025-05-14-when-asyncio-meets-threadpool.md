The Hidden Performance Killer: When Asyncio Meets ThreadPoolExecutor
Have you ever stared at your performance logs, completely baffled about where your latency is coming from? That was me last week, debugging a GPU-accelerated prediction service that was inexplicably slow. I had timestamps everywhere, yet none of them explained why requests were taking 7+ seconds when the actual predictions took mere milliseconds.
The culprit? A single line of code: await asyncio.gather(*tasks).
This is the story of a mysterious performance bottleneck at the intersection of two popular Python concurrency models: asyncio and ThreadPoolExecutor.
The Mystery: Fast Predictions, Slow Responses
Our machine learning team built a latency prediction service using FastAPI and XGBoost with GPU acceleration. Individual predictions were blazing fast - typically 10-30ms per prediction on GPU. Yet our end-to-end request latency was 6000-8000ms - orders of magnitude slower than expected.
Let me show you a simplified version of what our service looked like:
pythonfrom fastapi import FastAPI
import asyncio
from concurrent.futures import ThreadPoolExecutor
import xgboost as xgb
import pandas as pd
import time

app = FastAPI()
thread_pool = ThreadPoolExecutor(max_workers=8)
model = xgb.XGBRegressor()  # Pretend this is loaded with our trained model

# Process a single prediction in a thread
def process_prediction(input_data):
    # Transform input data
    df = pd.DataFrame([input_data])
    
    # Do the actual prediction
    prediction_start = time.time()
    prediction = model.predict(df)[0]
    prediction_time = (time.time() - prediction_start) * 1000
    
    return {
        "prediction": float(prediction),
        "prediction_time_ms": prediction_time
    }

@app.post("/predict")
async def predict(inputs: list[dict]):
    start_time = time.time()
    
    # Submit all prediction tasks to the thread pool
    tasks = []
    for input_data in inputs:
        task = asyncio.create_task(
            asyncio.to_thread(process_prediction, input_data)
        )
        tasks.append(task)
    
    # Wait for all predictions to complete
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    processing_time = (end_time - start_time) * 1000
    
    return {
        "predictions": results,
        "total_time_ms": processing_time
    }
Seems reasonable, right? The design makes sense:

FastAPI uses asyncio for handling concurrent requests
We're using ThreadPoolExecutor for CPU-bound prediction tasks
We gather all predictions and return them together

But when we tested it with a batch of 10 inputs, we were shocked:
Total time: 6583ms
Prediction times: [23ms, 19ms, 28ms, 15ms, 21ms, 18ms, 16ms, 22ms, 20ms, 17ms]
Something was very wrong. The predictions took a total of ~200ms, but the API response took over 6 seconds!
The Investigation: Tracing the Invisible Time
My first thought was, "I must be missing a timestamp somewhere." So I added more detailed timing:
python@app.post("/predict")
async def predict(inputs: list[dict]):
    start_time = time.time()
    
    timing = {}
    timing["start"] = 0
    
    # Create tasks
    task_start = time.time()
    tasks = []
    for input_data in inputs:
        task = asyncio.create_task(
            asyncio.to_thread(process_prediction, input_data)
        )
        tasks.append(task)
    timing["task_creation"] = (time.time() - task_start) * 1000
    
    # Wait for all predictions
    gather_start = time.time()
    results = await asyncio.gather(*tasks)
    timing["gather"] = (time.time() - gather_start) * 1000
    
    # Process results
    process_start = time.time()
    # (just assemble the response)
    timing["processing"] = (time.time() - process_start) * 1000
    
    total_time = (time.time() - start_time) * 1000
    
    return {
        "predictions": results,
        "timing": timing,
        "total_time_ms": total_time
    }
The new timing logs revealed something strange:
Timing breakdown:
- Task creation: 3ms
- Gather operation: 6578ms
- Result processing: 2ms
- Total time: 6583ms
Wait, what? The gather operation was taking 6.5 seconds, but all the predictions combined should take only ~200ms!
I had never suspected that asyncio.gather() itself could be the bottleneck. But there it was.
The Root Cause: When Concurrency Models Collide
After much research and testing, I discovered the fundamental issue: FastAPI/asyncio and ThreadPoolExecutor have fundamentally different concurrency models that create massive overhead when combined.
How Asyncio Works
Asyncio uses a cooperative multitasking model with a single thread:

Tasks voluntarily yield control with await
Perfect for I/O-bound operations (network, disk)
Uses non-blocking operations to handle many concurrent tasks
Control flow is explicit through await points

How ThreadPoolExecutor Works
ThreadPoolExecutor uses preemptive multitasking with multiple OS threads:

Each thread runs independently until completion
Designed for CPU-bound tasks that don't naturally yield
Threads are scheduled by the OS
Control flow is continuous

The Mismatch
When we combine these models with asyncio.to_thread(), we create significant overhead:

The asyncio event loop submits work to the thread pool
The event loop sets up callbacks for when threads complete
Threads execute and then need to synchronize with the event loop
asyncio.gather() must coordinate the completion of multiple threads

This entire chain creates overhead that can be far larger than the actual work being done, especially when the tasks are relatively short (like our 20ms predictions).
Detailed Timing Analysis: Where Does the Time Go?
To better understand the issue, I added even more comprehensive timing instrumentation to track each phase of request processing. Here's what I discovered when looking at a typical request with 7 prediction tasks:
Key Timing Points

Initial Overhead (670ms):

From start to submit: 181ms + 228ms + 262ms = 671ms
This overhead occurs before any prediction work starts
Just setting up the ThreadPoolExecutor and preparing tasks takes almost 700ms!


Task Submission Period (334ms):

From submit to before collect: 335ms
During this period, the first set of prediction logs appear
All the first-target predictions (which take 10-30ms each) happen in this window


Result Collection Period (1647ms):

From before collect to after collect: 1647ms
A significant gap (~988ms) appears between last prediction log and first process_pod_prediction breakdown
All prediction breakdowns (which show ~940-1000ms total) appear during this time
The result collection logs start much later (988ms after the predictions completed)


Final Overhead (178ms):

From after collect to end: 111ms + 67ms = 178ms
Additional overhead after all results are collected



The Critical Insight
The key insight came from examining specific timestamps:
Last prediction log: 08:52:11,849
First prediction breakdown: 08:52:12,330
First result collection: 08:52:12,760
There's a ~481ms gap between the last prediction and the first breakdown, and then another ~430ms gap before the first result is accessed. This suggests there's a significant delay between when the thread completes its work and when the main thread processes the results.
The root cause appears to be a combination of:

ThreadPoolExecutor Overhead: Creating and managing the thread pool takes ~671ms
Thread Synchronization Delays: There's a ~900ms delay between when threads complete work and when their results are collected
Result Collection Inefficiency: The as_completed loop adds additional delays (total 1647ms for collection vs ~1000ms actual work)

Measuring the Mismatch
To understand the problem better, I created a simple benchmark to compare different approaches:
pythonimport asyncio
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Simulate our prediction function (takes 20ms)
def mock_prediction(x):
    time.sleep(0.02)  # Simulate 20ms of work
    return x * 2

async def benchmark_asyncio_thread():
    start = time.time()
    
    tasks = []
    for i in range(10):
        task = asyncio.create_task(
            asyncio.to_thread(mock_prediction, i)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    end = time.time()
    return (end - start) * 1000

def benchmark_direct_threads():
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(mock_prediction, range(10)))
    
    end = time.time()
    return (end - start) * 1000

def benchmark_sequential():
    start = time.time()
    
    results = []
    for i in range(10):
        results.append(mock_prediction(i))
    
    end = time.time()
    return (end - start) * 1000

async def run_benchmarks():
    # Run each benchmark 5 times and take the average
    asyncio_times = []
    direct_thread_times = []
    sequential_times = []
    
    for _ in range(5):
        asyncio_times.append(await benchmark_asyncio_thread())
        direct_thread_times.append(benchmark_direct_threads())
        sequential_times.append(benchmark_sequential())
    
    print(f"Asyncio + ThreadPoolExecutor: {sum(asyncio_times)/len(asyncio_times):.2f}ms")
    print(f"Direct ThreadPoolExecutor: {sum(direct_thread_times)/len(direct_thread_times):.2f}ms")
    print(f"Sequential Processing: {sum(sequential_times)/len(sequential_times):.2f}ms")

# Run the benchmarks
asyncio.run(run_benchmarks())
The results were eye-opening:
Asyncio + ThreadPoolExecutor: 2451.34ms
Direct ThreadPoolExecutor: 24.78ms
Sequential Processing: 201.45ms
For 10 tasks that each take 20ms:

The theoretical minimum time is 20ms with perfect parallelism
Direct ThreadPoolExecutor gets close at ~25ms
Sequential processing takes ~200ms (as expected)
But asyncio + ThreadPoolExecutor takes a whopping 2.4 seconds!

That's a ~100x overhead compared to direct thread pool usage!
The Solutions: Right Tool for the Right Job
After discovering the root cause, I implemented several solutions and benchmarked them.
Solution 1: Direct ThreadPoolExecutor (No Asyncio)
The simplest fix is to avoid mixing concurrency models:
python@app.post("/predict")
def predict(inputs: list[dict]):
    start_time = time.time()
    
    # Use direct ThreadPoolExecutor without asyncio
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(
            process_prediction, inputs
        ))
    
    total_time = (time.time() - start_time) * 1000
    
    return {
        "predictions": results,
        "total_time_ms": total_time
    }
Note that this endpoint isn't async - and that's intentional. For CPU-bound work, we're better off without the asyncio overhead.
Solution 2: Use a Pre-warmed Dedicated Thread Pool
If you need to keep the async interface (e.g., for non-blocking handling of many requests), create a dedicated thread pool:
python# Global thread pool
prediction_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="predict-")

@app.on_event("shutdown")
def shutdown_thread_pool():
    prediction_pool.shutdown(wait=True)

@app.post("/predict")
async def predict(inputs: list[dict]):
    start_time = time.time()
    
    # Use asyncio.get_running_loop().run_in_executor instead of asyncio.to_thread
    loop = asyncio.get_running_loop()
    
    # Submit directly to executor with less asyncio overhead
    futures = [
        loop.run_in_executor(prediction_pool, process_prediction, input_data)
        for input_data in inputs
    ]
    
    # Wait for completion
    results = await asyncio.gather(*futures)
    
    total_time = (time.time() - start_time) * 1000
    
    return {
        "predictions": results,
        "total_time_ms": total_time
    }
This approach reduces some of the coordination overhead by using a persistent thread pool and a more direct executor interface.
Solution 3: Batch Processing for ML Workloads
For ML predictions specifically, batch processing is usually the most efficient approach. Instead of processing each input separately in its own thread, we can combine all inputs into a single batch and make one prediction call:
python@app.post("/predict")
async def predict_batch(inputs: list[dict]):
    start_time = time.time()
    
    # Create a single batch DataFrame
    df = pd.DataFrame(inputs)
    
    # Do a single prediction call
    predictions = model.predict(df)
    
    # Format results
    results = [{"prediction": float(p)} for p in predictions]
    
    total_time = (time.time() - start_time) * 1000
    
    return {
        "predictions": results,
        "total_time_ms": total_time
    }
This approach eliminates all threading overhead and leverages the ML model's native batch processing capabilities, which are often GPU-accelerated.
Batch Processing: The Ultimate Solution for ML Inference
In the end, the batch processing approach proved to be the most effective. When we implemented it and ran detailed timing analysis, the results were astounding:
2025-05-14 09:02:20,826 - INFO - requestID: 223, TS_START: 1747213340.825983, starting batch prediction request
2025-05-14 09:02:20,826 - INFO - requestID: 223, TS_BEFORE_RECORDS: 1747213340.826060, delta: 0.08ms
2025-05-14 09:02:20,826 - INFO - requestID: 223, TS_AFTER_RECORDS: 1747213340.826116, delta: 0.06ms, created 7 records
2025-05-14 09:02:20,826 - INFO - requestID: 223, TS_BEFORE_DF: 1747213340.826139, delta: 0.02ms
2025-05-14 09:02:20,826 - INFO - requestID: 223, TS_AFTER_DF: 1747213340.826799, delta: 0.66ms, DataFrame shape: (7, 21)
2025-05-14 09:02:20,832 - INFO - requestID: 223, Used Pipeline predict for avg_tpot
2025-05-14 09:02:20,832 - INFO - requestID: 223, TS_AFTER_TARGET_avg_tpot: 1747213340.832375, delta: 5.38ms, predicted 7 values
2025-05-14 09:02:20,837 - INFO - requestID: 223, Used Pipeline predict for ttft
2025-05-14 09:02:20,837 - INFO - requestID: 223, TS_AFTER_TARGET_ttft: 1747213340.837649, delta: 5.24ms, predicted 7 values
2025-05-14 09:02:20,837 - INFO - requestID: 223, TS_END: 1747213340.837729, batch predictions completed in 11ms for 7 pods
Compare this to our original approach:

Original asyncio + ThreadPoolExecutor: 3087ms
Batch processing approach: 11ms

That's a 280x speedup!
The batch approach eliminates all the threading overhead:

DataFrame creation takes less than 1ms
Each model prediction takes only ~5ms
Total end-to-end latency is just 11ms

The key advantages of batch processing for ML workloads are:

No thread creation/synchronization overhead
Leverages vectorized operations in pandas/numpy
Efficiently utilizes GPU compute capabilities
Reduces context switching and memory overhead

Benchmarks: The Proof Is in the Performance
I implemented all three solutions and tested them with the same workload:
Original (asyncio + to_thread): 6583ms
Solution 1 (Direct ThreadPool): 212ms
Solution 2 (Dedicated Pool): 487ms
Solution 3 (Batch Processing): 11ms
The most dramatic improvement came from batch processing, which is ideal for ML prediction workloads. But even the other solutions showed 10-30x performance improvements over the original approach.
Lessons Learned
Important lessons:

Don't blindly mix concurrency models: Asyncio and ThreadPoolExecutor have fundamentally different designs and combining them can lead to massive overhead.
Choose the right tool for the job:

For I/O-bound tasks: Use asyncio
For CPU-bound tasks: Use ThreadPoolExecutor directly
For ML inference: Use batch processing when possible


Measure everything: Without detailed timing logs, I might never have discovered that asyncio.gather() was the culprit.
Understand the systems you're working with: A deeper understanding of asyncio and ThreadPoolExecutor would have helped me avoid this issue from the start.
Test alternatives: Different concurrency approaches can have dramatically different performance characteristics.

When to Use Each Approach
Here's a quick guide on when to use each concurrency model:

Use asyncio when: You have many I/O-bound tasks (network requests, file operations) and want non-blocking concurrency.
Use ThreadPoolExecutor when: You have CPU-bound tasks that need to run in parallel and don't naturally yield control.
Use both together when: You need to perform CPU-bound tasks within an async framework, but be aware of the overhead and consider alternatives.
Use batch processing when: You're working with ML models or other systems that can efficiently process multiple inputs at once.

Conclusion
Asyncio, which I thought wouldn't be the root cause of performance overhead, was indeed the culprit. Switching to batch processing led to a 280x performance improvement in our prediction service. The most surprising part was that the bottleneck wasn't in our computation or GPU utilization, but in the coordination between concurrency models.
When designing high-performance systems, it's critical to understand not just the individual components, but how they interact. A mismatch between concurrency models can create overhead that dwarfs the actual work being done.
Next time you're designing a service that combines asyncio with ThreadPoolExecutor, remember this cautionary tale. The right approach depends on your specific workload, but being aware of the potential pitfalls will help you make better design decisions from the start.