---
layout: post
title:  "Journey to find a new research project in my PhD"
date:   2024-05-25 20:11:00
blurb: "A look at an example post using Bay Jekyll theme."
og_image: /assets/img/content/post-example/Banner.jpg
---

This is an essay about my journey to find a new second research project in my PhD.
I decide to write this essay because it is truly non-trivial. In addition, I am doing things that I have not done before.
Why am I writing it
1. It will be useful now. It will be useful for me to understand what I am doing and if I am doing things correctly/efficiently, etc. Right now, I am doing it in a very ad-hoc way. I don't have a roadmap.
2. It will be useful in the future when I need to find a new project again.

## Timeline
NSDI submission: May 7th, Tue
May 8th - May 13th: Chilling + Kivi artifact + Updating SLATE DoNotDistribute version
May 14th: Talking to Fan Lai, Reading some federated learning related papers
  - At this point, federated learning looks sort of done.
  - LLM specific federated learning could be interesting. I don't recall many paper in this area.
May 15th: Taking a glimpse of video Gen pipeline (**TODO: Needs to talk to Rahul**)s
May 15th: Meeting with Brighten
  - I wanna explore new things.
  - ATC attending
  - authorship 
May 16th: Depressed by Jovan and Haoran's publication list
- Jovan's: just idk..
- Haoran's: lots of workshops. interesting.
May 17th: SLATE project meeting
  - Creating SLATE project website
  - Writing README
  - Update paper
  - Reaching out to people
    - Solo.io
      - Louis (xx)
      - John Howard (xx)
    - Tetrate
      - Varun (xx)
      - Jack
    - Google
      - Anna (x)
      - Justin (xx)
    - Snowflake?
      - Charles
    - Uber?
    - Netflix?
    - Robinhood?
Editing SLATE DoNotDistribute version
May 19th - 21st: Reading SmartNIC, RDMA papers:  
  - **RDMA**
    - Azure storage with RDMA
    - Congestion control for RDMA cluster
      - PFC, ECN, etc.
      - Per queue congestion control not per flow
      - Right PFC and ECN config
    - Large scale RDMA cluster
    - Performance isolation, Justitia
    - Resource contention analysis, NSDI '23
    - I was tring to understand how RDMA can be used in AI workload but couldn't understand.
      - found GPU direct storage(GPU <-> SSD?), GPU DMA(GPU <-> Memory?)
    - Forgot many of them...
    - Lesson: RDMA is very much well explored... What about RDMA for microservices?
  - **SmartNIC**
    - Characterization, OSDI '23
    - SoC vs FPGA
    - Enso, OSDI '23 (very interesting problem finding, insane performance improvement)
    - Accelerating (Mostly done by FPGA)
      - Energy efficiency for Microservices (E3, NSDI '19)
      - TCP
      - RPC
      - Filesystem
      - Network function
      - KV, transaction
      - Disaggregated memory
    - Lesson: SmartNIC is also well explored.
May 21st: Talking to Jongyul
  - SmartNIC research
    - NVIDIA SmartNIC load map, accelerator in the SmartNIC chip, SmartNIC for AI workload
    - SmartNIC processing power is weak -> Limited
    - Consensus in the commmunity about SmartNIC usecase.
      - Workload supporting vs running something independently
      - Almost determined as workload supporting (offloading compute to SmartNIC to accelerate app).
      - SmartNIC as a workload supporting. Offloading the workload to SmartNIC. 
  - PTE scanning in SmartNIC
    - PTE scanning:
      - Finding the page table entry that is not used for a long time and evicting it. Basically, hot/cold page tracking
      - Scanning the page table validation bit and keeping track of the counters for each page and classifying hot/cold page.
  - Framework system for CXL
  - The problem of CXL research is hardware. Namsung Kim lab has it only....
  - Lesson
    - In the middle of the meeting: I want to do CXL!
    - Right after the meeting: Hmm.. SmartNIC, RDMA will not be easy and almost impossible considering the fact that I don't have background knowledge but at the same time it is not too late to change the topic.
    - After a bit more of time: CXL will be actually pretty tricky.. hmm.. still.. possible.. 
May 21st: Studying CXL
  - CXL HW: CXL intel CPU cluster
  - How to use it?
    - Adding more DRAM in CXL slot
  - Multiple machines are sharing a large pool of memory in CXL at low latency.
  - CXL memory pool will be recognized as another numa machine
  - CXL latency: 100ns??? don't remember exactly.
  - CXL supports cache coherence
    - What does it mean exactly?
  - HotNet '23
    - A Case Against CXL Memory Pooling (**I like this paper!**). Will CXL disappear eventually?
    - Lesson: CXL
  - Demistifying CXL, MICRO '23 
May 22nd:...?? I don't think I did any meaningful work. What did I do? Don't remember.
May 23rd: **reading LDOS**
  - Two thoughts after reading LDOS
    - **1. This is a kind of big picture that can be a thesis. In this sense, maybe I should.**
      - Should I jump on this project?
      - **I need to talk about it with Brighten.**
    - **[IMPORTANT] 2. It makes me think about SLATE + Cloud project more.**
      - Self-running cloud can be extension of SLATE by adding more components and solve them with machine learning.
        - Request routing component
          - routing
          - circuit break
          - adaptive concurrency
          - request reordering (timebomb)
        - Service mesh oriented autoscaler
          - Measuring instantaneous throughput in each service with the help of proxy
          - Brighten's comment: There are autoscaler using latency as a metric. How is it different? 
        - Request prediction
          - Request path (call tree)
            - where is benchmark though.... 
        - Request routing + Autoscaler
        - Heteorogeneous pod/vm aware routing
          - One pod has less resource
          - Same resource, but one pod is running in 
          - Same resource, same VM, but one pod is running with more noisy neighbor
      - The thing is... I don't think there are many people working on request routing in microservices.. maybe good to work... less competitive and I have SLATE implementation that can be used as a platform.
May 24th, 25th: Learning CUDA
  - Watching Stephen Jones's talk and summarizing it by myself
  - CUDA mode lecture 2,3
May 25th, Sat: Today

More papers that I read
- Of orange to apple, HotNet '23
- Running arbitrary code in GPU with wasm without program modification (ATC '23)

**[INTERESTING] Also, I thought about systems for AI workload**
- LLM serving
  - reponse lenght prediction -> better scheduling in the cluster.
  - Can't we somehow leverage token by token response characteristics in LLM with some network layer optimization?
  - LLM difficulty based modeling selection and scheduling in heterogeneous cluster
    - CPU, Different GPU model, Different GPU vendor, Different GPU architecture
- Video Gen system
  - Multiple steps in the pipeline?
- RAG system
  - After reading some blog post and paper like
  - There are few RAG system paper though!
    - PipeRAG and 

## What I did
- Reading a lot of papers.
- Watching a lot of talks.
- Trying to talk to people.

## Categorizing by area
Serverless
Machine learning based system
System for machine learning
LLM specific system
Cost optimization in cloud
CUDA, GPU


## What I learned (technical stuff)

## What I leanred (non-technical stuff)
