---
layout: post
title:  "Learning CUDA"
date:   2024-05-14 14:22:40
blurb: "A look at an example post using Bay Jekyll theme."
og_image: /assets/img/content/post-example/Banner.jpg
---

This is a record of mine for learning CUDA.

Created: May 24th, 2024

## Intuition behind GPU architecture
Reference: [https://www.youtube.com/watch?v=3l10o0DYJXg][Stephen Jones's talk]
This is by far THE best intro to GPU architecture I've ever seen. The talk is just so perfectly streamlined.

Let's say you bought a GPU. It says 8382059 Bazinga GigaFLOPS. Amazing!
But what does it mean?

### FLOPS don't matter but latency does
*FLOPS don't matter* but bandwidth does because of compute intensity. And then bandwidth doesn't really matter as much as latency because latency is long. There are two ways to fix the high latency problem. One is reducing the latency! Ahha...!?! It does not really solve the problem because the latency is limited by the physics, e.g., the speed of light, speed of eletron, physical distance between memory and chip, the way transister works, etc. The other way to reduce the latency is hiding it with parallelism and pipelining. 

### Over-subscribing the GPU always
Load lots of data together and compute them in parallel. While you compute lots of data, load the next data. The latency to load the next batch of data can be hidden by the pipelining. To do that, we need a lot of threads which is one of the most important design point in GPU architecture. In addtion, you need to have works to do in the queue always. It is okay in GPU because context switch is very cheap in GPU (1 cycle unlike CPU) (another important GPU design point). To do that, GPU must be and is supposed to be always over-subscribed by having threads in waiting. If the data is not ready(loaded), the corresponding threads cannot work (not in waiting queue) and leads to low utilization. In other words, it does not satisfy the compute intensity. If there are threads in waiting, you instantaneously context switch with the one which has the data ready. 
The GPU architecture is built with lots of threads in mind and with oversubscription to hide the latency. The gpu is a throughput machine which needs over-subscription instead of being a latency machine which has a fixed amount of work. 

### Place your data in cache
In spite of all, those threads sometimes still need to work **together**. Not everything is element-wise. And so the gpu runs threads is a hierarchy. a big grid of work is broken up into blocks which run in throughput mode and then threads in the block can work together and cooperate on some operations. (e.g., Convolution, Fourier transform, matrix multiplication)
So with latency beaten, we then turned and looked at how the compute intensity of heavy lifting algorithms like matrix multiplication finally begins to balance compute against bandwidth. The way to get high efficiency on small compute intensive pieces of work is really to play the cache hierarchy game. I can beat latency with threads and I can beat bandwidth with locality and then I can get all the flops even from the tensor cores, which is the answer to ''Where's my data'' because my ability to max out the efficiency of all the components in my system my threads my memory my compute is contingent on **where the data is**. To begin with the low compute intensity (again low compute intensity is what we want), I can get away with fewer threads to hide the latency if the data is in cache. In other words, even if the problem size is small due to data dependency within the problem, the compute intensity can be reached if the data is in cache because compute intensity becomes lower if the data is in cache. And I have more bandwidth to feed the flops but everything really depends on data. Even, my ability to use those flops depends on where my data is.


## Breakdown with numbers

#### The first monster: FLOPS
FLOPS = 2000 GFLOPS for FP64
FP64 = 8 bytes
Memory bandwidth = 200 GBytes/s = 200 / 8 GFLOPS = 25 G FP64 /s
Compute intensity = FLOPS / Memory bandwidth = 2000 / 25 = 80
80 is a high compute intensity. So, we can get 80 flops for every byte of data we load, which is not the case for most of the algorithms.

#### The second mosnter: Latency
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

### Interesting GPU architecture numbers
Threads per SM = 2048
Warps per SM = 64
Active warps per SM = 4 
-> 4 concurrent warps execution. There are four schedulers, four functional units, and four register files(16k*4 per scheduler)
Waiting warps per SM = 60
threads per warp = 32
Active threads per SM = 128
Waiting threads per SM = 1920
Num of SM = 80

### GPU Programming model
Grid is the entire work.
Grid comprises with blocks.
A block is a group of threads that can cooperate.
'Cooperate' means they can share data and synchronize.
Again, what it means is ... (TODO)
Different blocks can run independently in parallel. They should not have data dependency.
GPU is oversubscribed with blocks. If a block is waiting for data, the GPU can context switch to another block.
Many threads in a block work together, sharing data locally.
'Sharing data locally' means they can share data in the **cache**.

### Matrix multiplication
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

## Part 2: Why is CUDA programming like this?

TLDR; by the law of phyics in random memory access.

#### How RAM works
It accesses row by row one at a time. The electricity in the capacitors is read(discharaged) by the amplifier. Once it is read by the amplifier, it is much easier and clearer to read if it is 0 or 1.
When a new data in a different column needs to be read, the previous row in the amplifier should be written(charged) back to the capacitors and then read a new entire row. So, reading data in different rows is very expensive. It is because the amplifier needs to be recharged and discharged. This is called **row buffer hit** and **row buffer miss**. That's why data layout is so important and impacts the performance a lot. If you write a code reading 2D array in a column major order, it is much slower than reading in a row major order. You should not do it and it is your responsibility as a cuda programmer.

### Thread divergence
All the threads on the warp needs to work on adjacent data.

Thread divergence also affects the performance. Different threads in the same warp execute different code path. Then, the warp exeuction time will be dominated by the slowest thread. It is significant because all the threads in the warp(block) proceed in lockstep, executing one instruction at a time before it goes to the next one.

#### Why does WARP have 32 threads?
One row in RAM is page. 1 page is 1024 bytes.
4 active warp per SM. 4 * 32 = 128 threads. 128 threads * 8 bytes(FP64) = 1024 bytes.
Oh! In ideal situation where the data of four warps work on one row in RAM, one SM with four active warps will work with one row load in RAM! That's why the warp has 32 threads by careful HW design!

#### Thread block size must not be less than 128 always. Why?


+ Btw, registers in each SM will not be flushed even if warps are context switched.
+ All the threads in the same block is guaranteed to run at the same time in the same SM.

