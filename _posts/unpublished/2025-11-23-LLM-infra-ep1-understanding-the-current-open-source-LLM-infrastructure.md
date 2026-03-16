---
layout: post
title: "LLM Infrastructure Ep1: Understanding the Current Open Source LLM Infrastructure"
date: 2025-11-23
---

# LLM Infrastructure Ep1: Understanding the Current Open Source LLM Infrastructure

In this series, I will be discussing the current open source LLM infrastructure. After reading this series, you will understand how the current open source LLM infrastructures work, what approach they take, performance of each infrastructure.

This series will consist of two posts:
1. Understanding the current open source LLM infrastructure
2. Benchmarking them

## What do I mean by open source LLM infrastructure?
Let's say you are an owner of a AI chatbot company. The customer sends a request and your chatbot uses a LLM model (e.g., llama-3-70B) to generate a response. You need to provide the service as scale, many customers, many requests, and it means you need many LLM instances, meaning you need many GPUs and nodes. Sounds good. Let's do. How would you build the infrastructure? 

The open source LLM infrastructures answer this question. I will focus on three popular projects; NVIDIA's Dynamo, Bytedance's AIBrix, and Red hat's Llm-d. 

Let's see the common high level approach. All use Kubernetes as the underlying infrastructure. You create a vllm instance with llama3 70 model with a certain configuration, fp16 dtype, chunked prefill, prefix caching enabled, etc. Containerize it and deploy it to Kubernetes. Connect it to the gateway or frontend. Send a curl and you got response! good! done?

