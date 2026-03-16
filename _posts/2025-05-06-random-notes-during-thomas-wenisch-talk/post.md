---
layout: post
title: "Random notes during Thomas Wenisch talk at UIUC"
tags: [random_notes]
date: 2025-05-06
category: notes
---

# Random notes during Thomas Wenisch talk at UIUC

GPU world underutilization problem
- Unpopular model sitting there in 
- Lack of security for multi-tenancy
- Lack of fast core-provisioning?
- Lack of performance isolation in per-core allocation and 
- Slow reaction of scaling compared to CPU
- Multi-tenancy is not well understood 
- Model loading is much slower. Either
- Network devices are much cheaper so accelerator. So just throw money for network contention problem
- Interference in network is not a big issue in training since mostly

Tiered model checkpoint?
- SSD
- Flash
- Memory

Training
- Everybody wants to talk to everybody together
    - One port not all ports maybe
- Everybody yells at once
- Bursty traffic

In-switch computing
- Encryption is the challenge 
- Key distribution
- Switch needs to participate in encryption (key distribution), 

We don’t want fabric to be bottleneck. 

Planned OCS angles for training

different topology needs different hardware, 
- Cable length
- Shallow buffer vs deeper buffer in switch
