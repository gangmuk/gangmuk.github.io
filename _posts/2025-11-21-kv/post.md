---
layout: post
title: "Memory bandwidth and latency for KV load"
tags: [kv cache, memory, bandwidth, latency]
date: 2025-11-21
category: blog
---

This is my quick access note for kv, flops, roofline analysis for llm inference.

# KV size

This is a warm up practice to massage your brain. Let's calculate the KV size of a single token for llama3 8B model.

Llama3 8B model with sequence length 1024
- `seq_len` = 1024
- `d_model` = 4096
- `n_q_head` = 32
- `n_kv_head` = 8  → GQA factor = 4
- `d_head` = 128 (hidden dimension per head)
- `d_type` = 2 (fp16)
- `d_ffn` = 14336
- `num_layers` = 32
- `vocab_size` = 128256

```
KV size per token = num_layers * n_kv_head * d_head * d_type * 2(K and V) 
                  = 32 * 1024 * 2 * 2
                  = 131,072 bytes (0.125 MB)
```

for 1024 tokens, the total KV size is 1024 * 0.125 MB = 128 MB


# KV read latency

This table compares KV cache theorectical read latency from different memory hierarchy. The data size represents the total KV cache footprint for 1024 tokens for llama3 8B model. It does not have analysis when kv cache is on CXL pool. 

| Method | Medium | Bandwidth | GPU_Model | Latency_ms | Notes |
|--------|--------|-----------|-----------|----------------|-------|
| GPU_Retrieval | HBM | 2000_GB/s | A100 | 0.064 | 0.075 | GPU memory |
| CPU_Retrieval | PCIe_Gen4 | 32_GB/s | N/A | 4 - 6 | CPU→GPU |
| CPU_Retrieval | PCIe_Gen5 | 64_GB/s | N/A | 2 - 3 | CPU→GPU |
| NVMe_Traditional | NVMe_SSD | 5_GB/s | N/A | 29 - 43 | Disk→CPU→GPU |
| NVMe_GPUDirect | NVMe_SSD | 7_GB/s | N/A | 19 - 29 | disk→GPU (GDS) |
| RDMA read | RDMA | 50_GB/s | N/A | 3 - 6 | RDMA |
| S3_Retrieval | S3_Standard | 100_MB/s | N/A | 1313 - 1450 | Network + download |
| S3_Retrieval | S3_Express | 1000_MB/s | N/A | 135 - 175 | Low latency S3 |
| Recomputation | GPU_Compute | N/A | A10G_24GB | N/A | 360 - 560 | computation |
| Recomputation | GPU_Compute | N/A | A100_80GB | N/A | 205 | computation |
| Recomputation | GPU_Compute | N/A | H100_80GB | N/A | 80 - 128 | computation |


Typical NVMe data path is Disk → PCIe → CPU(DRAM) → PCIe → GPU. 
- Bandwidth: ~5 GB/s

NVMe GPUDirect data path: Disk→PCIe→GPU (direct DMA from NVMe to GPU memory, single hop, bypasses CPU)
- Bandwidth: ~7 GB/s

# FLOPs table for different models

Q projection: 2×seq×d_m×d_q

K projection: 2×seq×d_m×d_kv

V projection: 2×seq×d_m×d_kv

QxK^T: 2×seq²×d_q

Attn×V: 2×seq²×d_q

O projection: 2×seq×d_q×d_m

MLP up: 2×seq×d_m×d_ff

MLP down: 2×seq×d_ff×d_m

| Model | d_m | d_kv | d_q | d_ff | Layers | Q proj | K proj | V proj | Q×K^T | Attn×V | O proj | MLP up | MLP down | KV/layer | KV total |
|-------|-----|------|-----|------|--------|--------|--------|--------|--------|--------|--------|--------|---------|---------|---------|
| Llama 3 8B | 4096 | 1024 | 4096 | 14336 | 32 | 2×1024×4096×4096=34.4B |  (2×1024×4096×1024=8.6B) | 2×1024×4096×1024=8.6B | 2×1024²×4096=8.6B | 2×1024²×4096=8.6B | 2×1024×4096×4096=34.4B | 2×1024×4096×14336=120.3B | 2×1024×14336×4096=120.3B | seq×4KB (4MB) | seq×128KB (128MB) |
| Llama 3 70B | 8192 | 1024 | 8192 | 28672 | 80 | 2×1024×8192×8192=137.4B | 2×1024×8192×1024=17.2B | 2×1024×8192×1024=17.2B | 2×1024²×8192=17.2B | 2×1024²×8192=17.2B | 2×1024×8192×8192=137.4B | 2×1024×8192×28672=481.4B | 2×1024×28672×8192=481.4B | seq×4KB (4MB) | seq×320KB (320MB) |
| Llama 3.1 405B | 16384 | 1024 | 16384 | 53248 | 126 | 2×1024×16384×16384=549.8B | 2×1024×16384×1024=34.4B | 2×1024×16384×1024=34.4B | 2×1024²×16384=34.4B | 2×1024²×16384=34.4B | 2×1024×16384×16384=549.8B | 2×1024×16384×53248=1788.2B | 2×1024×53248×16384=1788.2B | seq×4KB (4MB) | seq×504KB (504MB) |