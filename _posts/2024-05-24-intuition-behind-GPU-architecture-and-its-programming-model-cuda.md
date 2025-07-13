---
layout: post
title:  "Learning CUDA"
date:   2024-05-14 14:22:40
blurb: "A look at an example post using Bay Jekyll theme."
og_image: /assets/img/content/post-example/Banner.jpg
---

#### Intuition behind NVIDIA GPU architecture

Whenever accelerator company launches their new accelerator, they always say "We have 1000 TFLOPS" or "We have 10x more FLOPS than the previous generation". Most of companies say our accelerator has higher max FLOPS than NVIDIA's XX GPU. Even then there are reasons people don't buy them and there is a reason that NVIDIA is the highest marketcap company in the world. There must be a reason. Instead of just saying "yeah it is CUDA moat", let's try to understand it from technical perspective.

Those FLOPS is theoretical numbers with the assumption that there is no stall and the data is always ready so that the accelerator can compute all the time. And obviously this is almost impossible to achieve in practice. There are many reasons why it is hard to achieve high compute utilization. One, maybe application is not compute intensive. Well, then it is not hardware's problem. Two, program is not written efficiently. In other words, not all the data are loaded in L1 cache at the right time because that's how the program is written. Okay, then why don't we write a better program? There will be two bottlenecks that will make it difficult to write a good program that can saturate the compute. One is the limited memory bandwidth and the other is simply writing a better program. We will focus on the first one in this post.

To understand why achieving peak performance is so challenging, we need to look beyond the raw FLOPS numbers and examine the real constraints that limit GPU performance.

#### FLOPS don't matter but latency does

*FLOPS don't matter* but bandwidth does because of compute intensity. And then bandwidth doesn't really matter as much as latency because latency is long. There are two ways to fix the high latency problem. One is reducing the latency! Ahha...!?! It does not really solve the problem because the latency is limited by the physics, e.g., the speed of light, speed of eletron, physical distance between memory and chip, the way transister works, etc. The other way to reduce the latency is hiding it with parallelism and pipelining.
This brings us to the fundamental design choices that the early NVIDIA GPU architecture engineers made. "Since we can't eliminate latency, we must hide it." and this is where GPU architecture becomes radically different from CPU design.

(compute intensity = FLOPS / Memory bandwidth)


#### Over-subscribing the GPU always
The solution is simple in concept: keep the GPU busy with other work while waiting for data. But implementing this requires careful orchestration of thousands of threads.
The sipmle solution in one sentence is "Load lots of data together and compute them in parallel". While you compute lots of data, load the next data. The latency to load the next batch of data can be hidden by the pipelining. This is well known technique and already has been used. But what's different here is that the hardware (NVIDIA GPU) was designed (maybe 'tailored' is more suitable expression) to achieve it. 
To do that, we need a lot of threads which is one of the most important design point in GPU architecture. 
In addtion, you need to have works to do in the queue always - meaning ready-to-execute threads waiting in the scheduler. When some threads stall waiting for data, you immediately switch to other threads that have their data ready. This constant switching between threads is only feasible because context switch is very cheap in GPU (1 cycle unlike CPU) whic is another important GPU design point. This is because GPU threads have dedicated register space and don't need to save/restore state like CPUs. To do that, GPU must be and is supposed to be always over-subscribed by having threads in waiting. If the data is not ready (loaded), the corresponding threads cannot work (not in waiting queue) and leads to low utilization. In other words, it does not satisfy the compute intensity. If there are threads in waiting, you instantaneously context switch with the one which has the data ready.
The GPU architecture is built with lots of threads in mind and with oversubscription to hide the latency. The gpu is a throughput machine which needs over-subscription instead of being a latency machine which has a fixed amount of work.
However, having thousands of threads working independently isn't always enough. Many algorithms require threads to coordinate and share data, which introduces another layer of complexity to the GPU design.

#### Where is my data: playing the cache hierarchy game

In spite of all, those threads sometimes still need to work **together**. Not everything is element-wise. And so the gpu runs threads is a hierarchy. A big grid of work is broken up into blocks which run in throughput mode and then threads in the block can work together and cooperate on some operations. (e.g., Convolution, Fourier transform, matrix multiplication)

So with latency beaten, we then turned and looked at how the compute intensity of heavy lifting algorithms like matrix multiplication finally begins to balance compute against bandwidth. The way to get high efficiency on small compute intensive pieces of work is really to play the cache hierarchy game. I can beat latency with threads and I can beat bandwidth with locality and then I can get all the flops even from the tensor cores, which is the answer to ''Where's my data'' because my ability to max out the efficiency of all the components in my system, in my threads, in my memory, and in my compute is contingent on **where the data is**. To begin with the low compute intensity (again low compute intensity is what we want), I can get away with fewer threads to hide the latency if the data is in cache. In other words, even if the problem size is small due to data dependency within the problem, the compute intensity can be reached if the data is in cache because compute intensity becomes lower if the data is in cache. And I have more bandwidth to feed the flops but everything really depends on data. Even, my ability to use those flops depends on where my data is.
Now that we understand the theoretical principles, let's examine some concrete numbers to see how these concepts play out in practice.

#### Breakdown with numbers

##### 1.FLOPS
FLOPS = 2000 GFLOPS for FP64
FP64 = 8 bytes
Memory bandwidth = 200 GBytes/s = 200 / 8 GFLOPS = 25 G FP64 /s
Compute intensity = FLOPS / Memory bandwidth = 2000 / 25 = 80

80 is a high compute intensity. So, we can get 80 flops for every byte of data we load, which is not the case for most of the algorithms.

##### 2. Latency
But the latency is still there and the latency must be the first citizen. The latency is 89ns from the main memory to register.
89ns * 200 GBytes = 17800 Bytes can be moved at one memory read latency
daxpy operation  = a*x + y
It needs to load x and y which is 16 bytes (two FP64).
daxpy operation has 16/17800 = 0.09% memory bandwidth utilization.
In other words, we need 17800/16 = 1112 daxpy operations to fully utilize the memory bandwidth and hide the latency.

Loop unrolling could be used to hide the latency. To execute the unrolled operation in parallel, we need enough number of threads. And that's why GPU has a lot of threads. Actually, they have more than they need.
Note that the number of parallel operation needed to saturate the memory bandwidth is proportional to the memory bandwitdth and more importantly latency. To enable them, GPU has more number of threads than it needs to achieve 100% memory bandwidth utilization unlike CPU (5x vs 1.2x). That's why you want to locate the data in cache as much as possible. It is the key to reduce the latency.
And that's why GPU has lots of registers. 256KB per SM and 27MB total.
Cache too!
As a result, L1, L2, HBM, NVLINK, PCIE have 8, 39, 100, 520, 6240 compute intensity, respectively.

These numbers help explain the specific architectural choices NVIDIA made in their GPU design. Let's look at some key specifications that directly relate to these performance requirements.

#### Interesting numbers in GPU architecture 
Threads per SM = 2048
Warps per SM = 64
Active warps per SM = 4 
-> 4 concurrent warps execution. There are four schedulers, four functional units, and four register files(16k*4 per scheduler)
Waiting warps per SM = 60
threads per warp = 32
Active threads per SM = 128
Waiting threads per SM = 1920
Num of SM = 80

Understanding these numbers helps us see why GPU programming follows certain patterns and best practices. This leads us to examine how programmers should structure their code to work effectively with this architecture.

#### Data sharing in GPU
Grid is the entire work.
Grid comprises with blocks.
A block is a group of threads that can cooperate.
'Cooperate' means they can share data and synchronize.
Again, what it means is ... (TODO)
Different blocks can run independently in parallel. They should not have data dependency.
GPU is oversubscribed with blocks. If a block is waiting for data, the GPU can context switch to another block.
Many threads in a block work together, sharing data locally.
'Sharing data locally' means they can share data in the **cache**.

To see how this programming model works in practice, let's examine a classic example that demonstrates the principles we've discussed.

##### Matrix multiplication
A X B
A: NxN
B: NxN
for each row in A
  Load the row. Loading N data => load N. This low is loaded once and used N times.
  for each column in B
    Load the column. Loading N data => load N
    N multiplication and one addition => compute N flops
    One output element is computed.

N compute for N^2 times => O(N^3) 
data load = O(N^2)
arithmetic intensity = N^3 / N^2 = N

To achieve compute intensity, increase the size of the matrix.
What if the size of the matrix is small?
Again, use cache.
Even with small matrix size, you can achieve compute intensity for the data in L1 cache.

This matrix multiplication example illustrates the theoretical principles, but to truly understand CUDA programming, we need to dive deeper into the hardware constraints that shape how we write efficient code.

### Why is CUDA programming like this?

**TLDR; by the law of phyics in random memory access.**

The peculiarities of CUDA programming aren't arbitrary design choices—they stem from fundamental physical limitations of how memory systems work. Let's explore these constraints.

#### How RAM works
It accesses row by row one at a time. The electricity in the capacitors is read(discharaged) by the amplifier. Once it is read by the amplifier, it is much easier and clearer to read if it is 0 or 1.
When a new data in a different column needs to be read, the previous row in the amplifier should be written(charged) back to the capacitors and then read a new entire row. So, reading data in different rows is very expensive. It is because the amplifier needs to be recharged and discharged. This is called **row buffer hit** and **row buffer miss**. That's why data layout is so important and impacts the performance a lot. If you write a code reading 2D array in a column major order, it is much slower than reading in a row major order. You should not do it and it is your responsibility as a cuda programmer.

Memory access patterns aren't the only physical constraint that affects CUDA programming. The way threads execute also has important implications for performance.

#### Thread divergence
All the threads on the warp needs to work on adjacent data.

Thread divergence also affects the performance. Different threads in the same warp execute different code path. Then, the warp exeuction time will be dominated by the slowest thread. It is significant because all the threads in the warp(block) proceed in lockstep, executing one instruction at a time before it goes to the next one.

The specific choice of warp size isn't arbitrary either—it's carefully designed to match the memory system characteristics.

#### Why does WARP have 32 threads?
One row in RAM is page. 1 page is 1024 bytes.
4 active warp per SM. 4 * 32 = 128 threads. 128 threads * 8 bytes(FP64) = 1024 bytes.
Oh! In ideal situation where the data of four warps work on one row in RAM, one SM with four active warps will work with one row load in RAM! That's why the warp has 32 threads by careful HW design!

This careful hardware design extends to other aspects of GPU architecture as well, including recommendations for thread block sizing.

#### Thread block size must not be less than 128 always. Why?

[This section appears to be incomplete in the original - you may want to add the explanation here]

These hardware design choices have several important implications for programmers:

+ Btw, registers in each SM will not be flushed even if warps are context switched.
+ All the threads in the same block is guaranteed to run at the same time in the same SM.

Understanding these low-level details helps explain why CUDA programming requires such careful attention to memory patterns, thread organization, and data locality. The performance characteristics that seem arbitrary are actually direct consequences of fundamental physical constraints in how modern memory systems and processors work.

#### Reference
Stephen Jones's talk: https://www.youtube.com/watch?v=3l10o0DYJXg
This is one of the best intro to GPU architecture. Most of the content is based on this talk. I highly recommend watching it.