---
layout: post
title: "Roofline analysis for prefill and decoding"
tags: [llm inference, roofline analysis]
date: 2025-12-26
category: blog
---

This is my quick access note for roofline analysis for llm inference.

Llama3 8B model with sequence length 1024
- `n_q_head` = 32
- ``n_kv_head`` = 8
- `d_head` = 128 (hidden dimension per head)
- `d_model` = 4096 (= `n_q_head` × `d_head`)
- `d_ffn` = 14336
- `num_layers` = 32
- `vocab_size` = 128256
- `d_type` = 2 (fp16)
- `seq_len`
- `batch`

# Roofline analysis

I will calculate the memory read write bytes and FLOPs for prefill and decoding.
Memory consists of model weights, and activation (including kv cache).
The model weights consists of `W_q`, `W_k`, `W_v`, `W_o`, `W_gate`, `W_up`, `W_down`.

FLOPs in transformer decoding model consists of `flops_Q`, `flops_K`, `flops_V`, `flops_qk`, `flops_av`, `flops_O`, `flops_gate`, `flops_up`, `flops_down`. We will ignore residual connection, layer normalization, and other insignificant computations in this post.

First, let's do prefill.

## Prefill

### Memory

**model weight**

Numbers inside () show the llama3 8B

Embedding = `vocab_size` × `d_model` (1GB)

W_q = `d_model` × `d_model` (32MB)

W_k = `d_model` × `n_kv_head` × `d_head` (8MB)

W_v = `d_model` × `n_kv_head` × `d_head` (8MB) # same as W_k

W_o = `d_model` x `n_q_head` × `d_head` (32MB)

W_gate = `d_model` × `d_ffn` (128MB)

W_up = `d_model` × `d_ffn` (128MB)

W_down = `d_ffn` × `d_model` (128MB)

Total bytes per layer = W_q + W_k + W_v + W_o + W_gate + W_up + W_down (480MB)

Total model weight bytes = 32 x 480MB + 1GB ~= 16GB (~= 8B x 2 bytes)

**activation** 

There are many intermediate tensors, so-called activation. We don't need to write all of them to memory. Optimized kernels will try to avoid the unnecessary read/write by fusing the multiple operations. The exact calculation will depend on the specific implementation of the kernel. However, anyway it is not dominate factor in memory operation, so you don't need to be bothered too much. Let's still do it. Good to be precise at least one time so that we don't look back.


We will consider these activations only assuming well-optimized fused kernel.
- Attention input: `batch` × `seq_len` × `d_model` × 2 (read)
- Attention output: `batch` × `seq_len` × `d_model` × 2 (write)
- FFN output: `batch` × `seq_len` × `d_model` × 2 (write)
- KV cache: `batch` × `seq_len` × `n_kv_head` × `d_head` × 2 × 2 (write: k and v)

Total activation bytes = `batch` × `seq_len` × `d_model` × 2 × 3 + `batch` × `seq_len` × `n_kv_head` × `d_head` × 2 × 2
                       = `batch` × `seq_len` × `d_model` × 6 + `batch` × `seq_len` × `d_model` × 2
                       = `batch` × `seq_len` × `d_model` × 8
                       ≈ `batch` × `seq_len` × `d_model` × 7 (for GQA with `n_kv_head` = n_q_head/4)

All logical activations are listed in below. Again, most of them do not need to be written in memory.

Attention Block - Fused Operations
- layernorm write: [`batch`, `seq_len`, `d_model`] → FUSED with QKV projection
- q write: [`batch`, `seq_len`, `d_model`] → FUSED, written directly as reshaped
- k write: [`batch`, `n_kv_head`, `seq_len`, `d_head`] → **WRITE**
- v write: [`batch`, `n_kv_head`, `seq_len`, `d_head`] → **WRITE**
- QK^T write: [`batch`, `n_q_head`, `seq_len`, `seq_len`] → AVOIDED
- softmax write: [`batch`, `n_q_head`, `seq_len`, `seq_len`] → AVOIDED
- attn output write: [`batch`, `n_q_head`, `seq_len`, `d_head`] → FUSED with concat
- concat write: [`batch`, `seq_len`, `d_model`] → FUSED with O projection
- O projection write: [`batch`, `seq_len`, `d_model`] → **WRITE**
- residual add write: [`batch`, `seq_len`, `d_model`] → FUSED with next layernorm

FFN Block - Fused Operations
- layernorm write: [`batch`, `seq_len`, `d_model`] → FUSED with gate/up
- gate write: [`batch`, `seq_len`, `d_ffn`] → FUSED with activation
- up write: [`batch`, `seq_len`, `d_ffn`] → FUSED with activation
- activation write: [`batch`, `seq_len`, `d_ffn`] → FUSED with down projection
- down projection write: [`batch`, `seq_len`, `d_model`] → **WRITE**
- residual add write: [`batch`, `seq_len`, `d_model`] → FUSED with next layer input

### Computation (FLOPs)

**Attention**

flops_Q = `batch` × `seq_len` × `d_model` × `d_model` x 2

flops_K = `batch` × `seq_len` × `d_model` × (``n_kv_head`` × `d_head`) x 2

flops_V = `batch` × `seq_len` × `d_model` × (``n_kv_head`` × `d_head`) x 2

flops_qk  = `batch` × `seq_len` × `d_model` × `seq_len` × 2

flops_av = `batch` × `seq_len` × `d_model` × `seq_len` × 2

flops_O = `batch` × `seq_len` × `d_model` × `d_model` x 2

**FFN**

flops_gate,up,down = 3 x (`batch` × `seq_len` × `d_model` × `d_ffn`) x 2

### Analysis

If llama3 8B, `batch` = 32, and `seq_len` = 1024, and `data_type_size` = 2 bytes, then

Total read/write bytes per layer = 436 MB (weights) + 940 MB (activation) ≈ 1300 MB

Total flops per layer ≈ 14.8 TFlops
- Attention: ~3.0 TFLOPs (Q, K, V, QK^T, AV, O)
- FFN: ~12 TFLOPs (gate, up, down)

arithmetic intensity = flops per layer / memory read bytes per layer
                     = 15 TFlops / (1376 * 10^6 bytes)
                     ≈ 10,000 FLOPs/byte

Compared to the hardware's theoretical peak arithmetic intensity, 10,000 FLOPs/byte is much higher than even H100 (295 FLOPs/byte). It means llama3 8B prefill with batch=32, seq_len=1024 is compute-bound.

If the batch size = 1, 
arithmetic intensity ≈ 10,000 / 32 FLOPs/byte ≈ 300 FLOPs/byte

Still compute-bound in theory (above H100's 295 FLOPs/byte).

**Hardware specification**

| GPU Model | Compute (TFLOPs, bf16/fp16) | Memory BW (GB/s) | Intensity (FLOPs/byte) |
|-----------|------------------------------|------------------|-------------------------|
| H100 SXM  | 989                          | 3,350            | 295                      |
| H100 PCIe | 756                          | 2,000            | 378                      |
| A100 SXM  | 312                          | 2,039            | 153                      |
| A100 PCIe | 312                          | 1,555            | 201                      |
| L40S      | 362                          | 864              | 419                      |
| A10       | 125                          | 600              | 208                      |
| V100      | 125 (fp16)                   | 900              | 139                      |


## Decode
Let's see decode phase.
seq_len = 1
seq_len_context = cached context length

### Memory

model weight
- Model weights: number_of_parameters * data_type_size / number_of_layers (same, 480MB)

input tensor
- Input tensor: `batch` × 1 × `d_model` × 2 (32 × 1 × 4096 × 2 = 262,144 bytes) (negligible)

activation
- KV cache READ: `batch` × `seq_len_context` × `n_kv_head` × `d_head` × 2 × 2 (32 x 1024 x 8 x 128 x 2 x 2 = 134,217,728 bytes)
- KV cache WRITE: `batch` × 1 × `n_kv_head` × `d_head` × 2 × 2 (new token only) (32 × 1 × 8 × 128 × 2 × 2 = 131,072 bytes)
- Attention input: `batch` × 1 × `d_model` × 2 (32 x 1 x 4096 x 2 = 262,144 bytes) (negligible)
- Attention output: `batch` × 1 × `d_model` × 2 (32 x 1 x 4096 x 2 = 262,144 bytes) (negligible)
- FFN input: `batch` × 1 × `d_ffn` × 2 (32 x 1 x 14336 x 2 = 884,736 bytes) (negligible)
- FFN output: `batch` × 1 × `d_model` × 2 (32 x 1 x 4096 x 2 = 262,144 bytes) (negligible)

rough total read/write bytes per layer = 480MB (weights) + 135MB (activation) ≈ 600MB

### FLOPs

**Attention**

flops_Q = `batch` × 1 × `d_model` × `d_model` x 2

flops_K = `batch` × 1 × `d_model` × (`n_kv_head` × `d_head`) x 2

flops_V = `batch` × 1 × `d_model` × (`n_kv_head` × `d_head`) x 2

flops_qk = `batch` × `n_q_head` × 1 × `seq_len_context` × `d_head` × 2
         = `batch` × 1 × `d_model` × `seq_len_context` × 2  (since `d_model` = `n_q_head` × `d_head`)

flops_av = `batch` × `n_q_head` × 1 × `seq_len_context` × `d_head` × 2
         = `batch` × 1 × `d_model` × `seq_len_context` × 2  (since `d_model` = `n_q_head` × `d_head`)

flops_O = `batch` × 1 × `d_model` × `d_model` x 2

**FFN**

flops_ffn = 3 × (`batch` × 1 × `d_ffn` × `d_model` x 2)

### Analysis

If llama3 8B, `batch` = 32, `seq_len_context` = 1024, and data_type_size = 2 bytes, then

Total read/write bytes per layer = 480MB (weights) + 135MB (activation) ≈ 600MB

Total flops per layer ≈ 15 GFLOPs = 0.015 TFLOPs
- Attention: ~3.0 GFLOPs (Q, K, V, QK^T, AV, O)
- FFN: ~12 GFLOPs (gate, up, down)

arithmetic intensity = flops per layer / memory read bytes per layer
                     = 15 GFLOPs / (600 * 10^6 bytes)
                     = 0.015 TFLOPs / (600 * 10^6 bytes)
                     ≈ 24 FLOPs/byte << H100 (295 FLOPs/byte)

Memory-bound!
