---
layout: post
title:  "Journey to find a new research project in my PhD"
date:   2024-05-25 20:11:00
blurb: "A look at an example post using Bay Jekyll theme."
og_image: /assets/img/content/post-example/Banner.jpg
---

This is an essay about my journey to find a new second research project in my PhD.
I decide to write this essay because it is truly non-trivial. In addition, I am doing things that I have not done before. I need to look back what I did by myself as well.
Why am I writing it
1. It is useful for me to understand what I am doing and tell if I am doing things correctly/efficiently. Right now, I am doing it in a very ad-hoc way. I don't have a roadmap.
2. It will be useful for future me when I need to find a new project again.
3. It might be useful for other phd students. It might resonate with other PhD students going through the same thing and let them know that it is common hardship!
4. Also, it is useful to justify the time that I spent. Hynotize myself that it is not a waste of time! [Expecto Patronum][https://harrypotterspellscursesandcharms.fandom.com/wiki/Expecto_Patronum]!


Alert! It is NOT organized at all. It is something like me speaking to myself randomly in a stream of consciousness. If it were handwritten, it would have been unreadable.

## Timeline
NSDI submission: May 7th, Tue

*May 8th - 13th*
- Chilling
- Kivi artifact
- Updating SLATE DoNotDistribute version

*May 14th* (federated learning)
- Reading some **federated learning** related papers
- Talking to **Fan Lai**
- At this point, federated learning looks sort of done.
- LLM specific federated learning could be interesting. I don't recall many paper in this area.
- It seems it won't be not easy to initiate collaboration without having at least some rough idea of a potential project. 

*May 15th*
- Taking a glimpse of **video Gen pipeline** (**TODO: Needs to talk to Rahul**)s
- Meeting with B
  - I wanna explore new things.
  - ATC/OSDI ?

*May 16th*
- I don't recall what I did
  
*May 17th*
- **SLATE project meeting**
  - Creating SLATE project website
  - Writing README
  - Update paper
  - Reaching out to people
    <!-- - Solo.io
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
    - Robinhood? -->
  - Editing SLATE DoNotDistribute version

*May 19th - 21st* SmartNIC, RDMA papers
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
  - *Lesson: RDMA is very much well explored... What about RDMA for microservices?*
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
  - *Lesson: SmartNIC is also well explored.*

*May 21st*
- Talking to **Jongyul**
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

*May 21st*: CXL
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
- *Lesson*
  - In the middle of the meeting: I want to do CXL!
  - Right after the meeting: Hmm.. SmartNIC, RDMA will not be easy and almost impossible considering the fact that I don't have background knowledge but at the same time it is not too late to change the topic.
  - After a bit more of time: CXL will be actually pretty tricky.. hmm.. still.. possible.. 

*May 22nd*
- I don't think I did any meaningful work. What did I do? Don't remember.

*May 23rd*: **reading LD**
<!-- - Two thoughts after reading LD
  - **1. This is a kind of big picture that can be a thesis. In this sense, maybe I should.**
    - Should I jump on this project?
    - **I need to talk about it with B.**
  - **[IMPORTANT] 2. It makes me think about SLATE + Cloud project more.**
    - Self-running cloud can be extension of SLATE by adding more components and solve them with machine learning.
      - Request routing component
        - routing
        - circuit break
        - adaptive concurrency
        - request reordering (timebomb)
      - Service mesh oriented autoscaler
        - Measuring instantaneous throughput in each service with the help of proxy
        - B's comment: There are autoscaler using latency as a metric. How is it different? 
      - Request prediction
        - Request path (call tree)
          - where is benchmark though.... 
      - Request routing + Autoscaler
      - Heteorogeneous pod/vm aware routing
        - One pod has less resource
        - Same resource, but one pod is running in 
        - Same resource, same VM, but one pod is running with more noisy neighbor
    - The thing is... I don't think there are many people working on request routing in microservices.. maybe good to work... less competitive and I have SLATE implementation that can be used as a platform. -->

*May 24th, 25th*: Learning CUDA
- Watching Stephen Jones's talk and summarizing it by myself
- CUDA mode lecture 2,3
- There is a separate (very messy) blog post for it. Go take a look!

*May 25th*: Today

**[INTERESTING] Also, I thought about systems for AI workload**
**LLM serving**
  - reponse lenght prediction -> better scheduling in the cluster.
  - Can't we somehow leverage token by token response characteristics in LLM with some network layer optimization?
  - LLM difficulty based modeling selection and scheduling in heterogeneous cluster
    - CPU, Different GPU model, Different GPU vendor, Different GPU architecture
    - 
**Video Gen system**
  - Multiple steps in the pipeline?

**RAG system**
  - After reading some blog post and paper like
  - There are few RAG system paper though!
    - PipeRAG and ?(there were two more)

#### [IMPORTANT] What I am going to do
1. No more arbitrary paper shopping.
2. More likely to choose LD or SLATE
3. SLATE
   1. Look at May 23rd the second bullet point.
4. LD
  1. Needs to talk to B
     1. What's the status
     2. It is a large fund and I see each one having subproblem. Does it matter?
     3. **Collaboration**?
5. Two projects would be good. Ideally, one in SLATE and the other in ML related (LD or MLSys)

#### What I learned 
After the project is done, when you are in the phase of finding a new project intensively as a main task, **the concrete plan and deadline must be set**. Otherwise, it will be indefinite process.

*Why?*
1. **Otherwise, you will find yourself reading papers forever for nothing**. There is no answer for how many paper you have to read or how many papers will guarantee you to find a project. 
2. Let's say a few ideas come up but you are not sure about them. So what you end up doing is learning more to weigh up if that will be good project(good paper). Hence, you sit back and resume reading more papers, watching more talks, reading more blog posts. When are you able to tell if a potential project is good or will be good or even feasible? (Feasibility should be considered more seriously and carefully though). You **CANNOT**. In other words, **reading papers will not give you anwser, hence you should stop at some point**.
3. **Moreover, you will feel like you are doing something (learning specifically)**. It is easy way to learn new things. However, as you notice, the pitfall is 
4. **There are indefinitely endless number of papers and talks**. When will you think that you read enough papers? There is no rule of thumb. When will you stop? You don't know and you won't find the answer because there is no! It is very dangerous.

***Problem summary***:
Basically, it is swamp. You don't know you are in the middle of swamp and slowly sinking because you are learning something. Learning is not the goal. Learning is easy. People will not pay you because you know a lot. There are tons of people who know a lot. Why? Because it is easy and you might feel you are doing a great job, landing on excessive self-satisfaction.

**Solution**
1. **Set a exact timeline**. Max two weeks. Intensive one week is better.
2. **Set areas**. In my case, it was RDMA, SmartNIC, CXL, RAG, LLM serving, Video Gen, Federated learning. And try not to be distracted when encountering papers in other areas.

**Conclusion**
Be mindful when you are exclusively spending time on finding a new project. It is very easy to be trapped in the swamp of learning. Write down the plan with the timeline for it.

More papers that I read
- Of orange to apple, HotNet '23
- Running arbitrary code in GPU with wasm without program modification (ATC '23)
- Orion and the three rights, OSDI '22