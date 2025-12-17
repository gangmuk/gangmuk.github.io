---
layout: post
title: "Memory bandwidth and latency for KV load"
tags: [kv_cache, memory, bandwidth, latency]
date: 2025-11-21
---

The calculation is based on the llama3 7B model with sequence length 1024.
- seq_len = 1024
- d_model (hidden_dim) = 4096
- number of query: 32
- number of heads for key and value (GQA): 8
- d_type = fp16
- num_layers = 32

KV size per token = num_layers * 2 * d_kv * d_type = 32 * 2 * 1024 * 2 = 131,072 bytes (0.125 MB)

This table compares different methods for retrieving KV cache data during inference, showing bandwidth requirements, latency estimates, and storage/retrieval approaches. The data size represents the total KV cache footprint for 1024 tokens across all 32 layers.

| Method | Medium | Bandwidth | GPU_Model | Data_Size_MB | Latency_ms_min | Latency_ms_max | Notes |
|--------|--------|-----------|-----------|--------------|----------------|----------------|-------|
| GPU_Retrieval | HBM | 2000_GB/s | A100 | 128 | 0.064 | 0.075 | Already in GPU memory |
| CPU_Retrieval | PCIe_Gen4 | 32_GB/s | N/A | 128 | 4 | 6 | CPU→GPU transfer |
| CPU_Retrieval | PCIe_Gen5 | 64_GB/s | N/A | 128 | 2 | 3 | CPU→GPU transfer |
| NVMe_Traditional | NVMe_SSD | 5_GB/s | N/A | 128 | 29 | 43 | Disk→CPU→GPU (two-hop) |
| NVMe_GPUDirect | NVMe_SSD | 7_GB/s | N/A | 128 | 19 | 29 | Direct disk→GPU (GDS) |
| Storage_Enterprise | RDMA_Storage | 50_GB/s | N/A | 128 | 3 | 6 | VAST/Dell with GPUDirect |
| S3_Retrieval | S3_Standard | 100_MB/s | N/A | 128 | 1313 | 1450 | Network + download |
| S3_Retrieval | S3_Express | 1000_MB/s | N/A | 128 | 135 | 175 | Low latency S3 |
| Recomputation | GPU_Compute | N/A | A10G_24GB | N/A | 360 | 560 | Lower-end GPU prefill |
| Recomputation | GPU_Compute | N/A | A100_80GB | N/A | 128 | 205 | A100 prefill (~5K tok/s) |
| Recomputation | GPU_Compute | N/A | H100_80GB | N/A | 80 | 128 | H100 prefill (~10K tok/s) |


## Transformer Model Memory Analysis

The following table provides a detailed breakdown of memory operations and KV cache sizes for various large language models, assuming sequence length 1024. All calculations are in FLOPs for forward pass operations and bytes for memory usage.

| Model | d_m | d_kv | d_q | d_ff | Layers | Q proj | K proj | V proj | Q×K^T | Attn×V | O proj | MLP up | MLP down | KV/layer | KV total |
|-------|-----|------|-----|------|--------|--------|--------|--------|--------|--------|--------|--------|---------|---------|---------|
| Llama 3 8B | 4096 | 1024 | 4096 | 14336 | 32 | 2×seq×d_m×d_q (2×1024×4096×4096=34.4B) | 2×seq×d_m×d_kv (2×1024×4096×1024=8.6B) | 2×seq×d_m×d_kv (2×1024×4096×1024=8.6B) | 2×seq²×d_q (2×1024²×4096=8.6B) | 2×seq²×d_q (2×1024²×4096=8.6B) | 2×seq×d_q×d_m (2×1024×4096×4096=34.4B) | 2×seq×d_m×d_ff (2×1024×4096×14336=120.3B) | 2×seq×d_ff×d_m (2×1024×14336×4096=120.3B) | seq×4KB (4MB) | seq×128KB (128MB) |
| Llama 3 70B | 8192 | 1024 | 8192 | 28672 | 80 | 2×seq×d_m×d_q (2×1024×8192×8192=137.4B) | 2×seq×d_m×d_kv (2×1024×8192×1024=17.2B) | 2×seq×d_m×d_kv (2×1024×8192×1024=17.2B) | 2×seq²×d_q (2×1024²×8192=17.2B) | 2×seq²×d_q (2×1024²×8192=17.2B) | 2×seq×d_q×d_m (2×1024×8192×8192=137.4B) | 2×seq×d_m×d_ff (2×1024×8192×28672=481.4B) | 2×seq×d_ff×d_m (2×1024×28672×8192=481.4B) | seq×4KB (4MB) | seq×320KB (320MB) |
| Llama 3.1 405B | 16384 | 1024 | 16384 | 53248 | 126 | 2×seq×d_m×d_q (2×1024×16384×16384=549.8B) | 2×seq×d_m×d_kv (2×1024×16384×1024=34.4B) | 2×seq×d_m×d_kv (2×1024×16384×1024=34.4B) | 2×seq²×d_q (2×1024²×16384=34.4B) | 2×seq²×d_q (2×1024²×16384=34.4B) | 2×seq×d_q×d_m (2×1024×16384×16384=549.8B) | 2×seq×d_m×d_ff (2×1024×16384×53248=1788.2B) | 2×seq×d_ff×d_m (2×1024×53248×16384=1788.2B) | seq×4KB (4MB) | seq×504KB (504MB) |
| Qwen 2.5 7B | 3584 | 512 | 3584 | 18944 | 28 | 2×seq×d_m×d_q (2×1024×3584×3584=26.3B) | 2×seq×d_m×d_kv (2×1024×3584×512=3.8B) | 2×seq×d_m×d_kv (2×1024×3584×512=3.8B) | 2×seq²×d_q (2×1024²×3584=7.5B) | 2×seq²×d_q (2×1024²×3584=7.5B) | 2×seq×d_q×d_m (2×1024×3584×3584=26.3B) | 2×seq×d_m×d_ff (2×1024×3584×18944=139.0B) | 2×seq×d_ff×d_m (2×1024×18944×3584=139.0B) | seq×2KB (2MB) | seq×56KB (56MB) |
| Qwen 2.5 14B | 5120 | 1024 | 5120 | 13824 | 48 | 2×seq×d_m×d_q (2×1024×5120×5120=53.7B) | 2×seq×d_m×d_kv (2×1024×5120×1024=10.7B) | 2×seq×d_m×d_kv (2×1024×5120×1024=10.7B) | 2×seq²×d_q (2×1024²×5120=10.7B) | 2×seq²×d_q (2×1024²×5120=10.7B) | 2×seq×d_q×d_m (2×1024×5120×5120=53.7B) | 2×seq×d_m×d_ff (2×1024×5120×13824=145.1B) | 2×seq×d_ff×d_m (2×1024×13824×5120=145.1B) | seq×4KB (4MB) | seq×192KB (192MB) |
| Qwen 2.5 72B | 8192 | 1024 | 8192 | 29568 | 80 | 2×seq×d_m×d_q (2×1024×8192×8192=137.4B) | 2×seq×d_m×d_kv (2×1024×8192×1024=17.2B) | 2×seq×d_m×d_kv (2×1024×8192×1024=17.2B) | 2×seq²×d_q (2×1024²×8192=17.2B) | 2×seq²×d_q (2×1024²×8192=17.2B) | 2×seq×d_q×d_m (2×1024×8192×8192=137.4B) | 2×seq×d_m×d_ff (2×1024×8192×29568=496.3B) | 2×seq×d_ff×d_m (2×1024×29568×8192=496.3B) | seq×4KB (4MB) | seq×320KB (320MB) |
| Gemma 2 2B | 2304 | 1024 | 2048 | 9216 | 26 | 2×seq×d_m×d_q (2×1024×2304×2048=9.7B) | 2×seq×d_m×d_kv (2×1024×2304×1024=4.8B) | 2×seq×d_m×d_kv (2×1024×2304×1024=4.8B) | 2×seq²×d_q (2×1024²×2048=4.3B) | 2×seq²×d_q (2×1024²×2048=4.3B) | 2×seq×d_q×d_m (2×1024×2048×2304=9.7B) | 2×seq×d_m×d_ff (2×1024×2304×9216=43.5B) | 2×seq×d_ff×d_m (2×1024×9216×2304=43.5B) | seq×4KB (4MB) | seq×104KB (104MB) |
| Gemma 2 9B | 3584 | 2048 | 4096 | 14336 | 42 | 2×seq×d_m×d_q (2×1024×3584×4096=30.1B) | 2×seq×d_m×d_kv (2×1024×3584×2048=15.0B) | 2×seq×d_m×d_kv (2×1024×3584×2048=15.0B) | 2×seq²×d_q (2×1024²×4096=8.6B) | 2×seq²×d_q (2×1024²×4096=8.6B) | 2×seq×d_q×d_m (2×1024×4096×3584=30.1B) | 2×seq×d_m×d_ff (2×1024×3584×14336=105.4B) | 2×seq×d_ff×d_m (2×1024×14336×3584=105.4B) | seq×8KB (8MB) | seq×336KB (336MB) |
| Gemma 2 27B | 4608 | 2048 | 4096 | 36864 | 46 | 2×seq×d_m×d_q (2×1024×4608×4096=38.7B) | 2×seq×d_m×d_kv (2×1024×4608×2048=19.3B) | 2×seq×d_m×d_kv (2×1024×4608×2048=19.3B) | 2×seq²×d_q (2×1024²×4096=8.6B) | 2×seq²×d_q (2×1024²×4096=8.6B) | 2×seq×d_q×d_m (2×1024×4096×4608=38.7B) | 2×seq×d_m×d_ff (2×1024×4608×36864=348.2B) | 2×seq×d_ff×d_m (2×1024×36864×4608=348.2B) | seq×8KB (8MB) | seq×368KB (368MB) |


#### Differences Between the Two NVMe Paths:

Traditional NVMe path (Disk→CPU→GPU):
- Bandwidth: ~5 GB/s (limited by PCIe to CPU, then CPU to GPU)
- Latency: Higher due to two-hop transfer + CPU involvement
- Steps: NVMe → System RAM → CPU processing → PCIe → GPU
- Use case: Standard systems without GPUDirect Storage

NVMe GPUDirect (Disk→GPU):
- Bandwidth: ~7 GB/s (direct DMA from NVMe to GPU memory)
- Latency: ~30-40% lower - single hop, bypasses CPU
- Steps: NVMe → GPU (direct DMA via PCIe)
- Use case: Modern systems with NVIDIA GPUDirect Storage support
- Requirements: 
  - Supported NVMe drives
  - GPUDirect Storage drivers
  - PCIe topology that allows direct NVMe-GPU transfers