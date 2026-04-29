# Local LLM Hardware and Context Sizing

Use this reference when a user is choosing hardware for local llama.cpp/Ollama/MLX inference, especially Apple Silicon vs NVIDIA GPU systems, and asks about model size, context length, KV cache, or whether a memory configuration is enough.

## Class of task

The recurring task is: sizing local LLM hardware for a target parameter count and use case by budgeting model weights, KV cache, OS/app overhead, context length, and expected tokens/sec.

## Core mental model

Local inference memory is roughly:

```text
total memory ≈ model weights + KV cache + runtime overhead + OS/apps
```

- **Model weights** are fixed after load: the model's parameters, usually quantized in GGUF/MLX/etc.
- **KV cache** grows with context length: saved attention Key/Value tensors for all tokens currently in context.
- **Runtime overhead** includes buffers, graph/workspace memory, tokenizer/runtime allocations, and backend-specific overhead.
- **OS/apps** matter a lot on unified-memory Macs because browser, IDE, Docker, DBs, and the LLM all share the same RAM.

## KV cache explanation

KV cache is the model's saved intermediate attention state for previous tokens. Without it, the model would need to recompute attention over the full prompt every time it emits the next token. KV cache makes generation fast, but it consumes memory proportional to context length.

Approximate formula:

```text
KV bytes ≈ 2 * n_layers * n_kv_heads * head_dim * context_tokens * bytes_per_KV_element
```

The `2` is for Key and Value. GQA/MQA models have fewer KV heads and therefore much smaller KV cache than full multi-head attention models. KV quantization (`q8`/`q4` KV) can reduce KV memory substantially.

## 27B weight-size rules of thumb

For a 27B dense model, weights alone are approximately:

| Quant | Weights only |
|---|---:|
| Q4-ish, ~4.5 bpw | ~14 GiB |
| Q5-ish, ~5.5 bpw | ~17 GiB |
| Q6-ish, ~6.5 bpw | ~20 GiB |
| Q8 | ~25 GiB |
| FP16/BF16 | ~50 GiB |

Add KV cache, runtime overhead, and OS/apps on top.

## 27B/32B GQA KV cache rough sizing

For modern GQA-ish 27B-32B models, FP16/BF16 KV cache can be roughly:

| Context | FP16 KV | q8 KV | q4 KV |
|---:|---:|---:|---:|
| 8K | ~2 GiB | ~1 GiB | ~0.5 GiB |
| 16K | ~4 GiB | ~2 GiB | ~1 GiB |
| 32K | ~8 GiB | ~4 GiB | ~2 GiB |
| 64K | ~16 GiB | ~8 GiB | ~4 GiB |
| 128K | ~32 GiB | ~16 GiB | ~8 GiB |

Bad case: models with many KV heads can use several times more KV. For a 27B full-MHA-ish shape, 128K FP16 KV can approach ~96 GiB. Always prefer model-specific architecture info when available.

## Context length for coding agents

Coding agents consume context faster than chat because system prompts, tool schemas, search results, file contents, diffs, test logs, and prior tool traces all compete for tokens.

| Context | Coding-agent usefulness |
|---:|---|
| 8K | Very tight; single-file edits or small questions only |
| 16K | Small fixes and a few snippets |
| 32K | Practical minimum; several files + error/diff context |
| 64K | Comfortable for medium tasks |
| 128K | Cloud-frontier-like workflow; large tasks and more repo context |

Long context also slows prefill. Even if memory fits, repeatedly injecting 64K-128K tokens can make first-token latency painful. Prefer search/RAG/file selection, summaries, and subagents instead of dumping the whole repo every turn.

## Apple Silicon sizing guidance

Apple unified memory is flexible but shared. It avoids strict VRAM limits, but OS/apps reduce the practical LLM budget.

For a 27B local coding-agent use case:

- **64GB unified memory**: usable for 27B Q4/Q5 around 16K-32K context; 64K is possible but requires discipline; 128K is not a comfortable default.
- **128GB unified memory**: comfortable for 27B Q4/Q5/Q8 with 64K and can attempt 128K depending on model/KV quantization; much better for IDE + browser + Docker + agent runtime.
- **512GB/Ultra-class systems**: only worth it if the user wants 70B+, huge contexts, multiple models, or heavy local workflows.

If choosing between SSD and unified memory on a Mac for LLM work, prefer memory. SSD can be external; unified memory cannot be upgraded.

## Hardware comparison heuristics

For 27B local inference:

- **Mac Studio M4 Max 128GB**: best quiet all-rounder; strong for daily dev + local LLM; not as fast as high-end NVIDIA for raw tokens/sec.
- **Mac Studio/Mac mini 64GB**: works for Q4/Q5, but becomes memory-management work for coding agents and long context.
- **RTX 4090 24GB**: fast for Q4/Q5 27B but tight for Q8/long contexts.
- **RTX 5090 32GB**: strong speed choice for 27B Q4/Q5/Q8-ish, but has heat/noise/build complexity.
- **RTX PRO 6000/96GB-class workstation**: excellent but overkill/expensive for 27B-only use.
- **DGX Spark/128GB unified**: interesting NVIDIA dev box, but for 27B-only inference judge it by memory bandwidth and real benchmarks, not the DGX name.
- **Ryzen AI Max/Strix Halo 128GB mini PCs**: can load large models cheaply, but tokens/sec may be too low for comfortable 27B coding-agent use.

## Speed intuition

Decode speed is often memory-bandwidth-bound for single-user inference. Naive upper bound:

```text
tokens/sec ≈ memory_bandwidth_GBps / model_weight_size_GB
```

Real speed is lower and depends on backend, quant, prompt length, batch size, model architecture, and CPU/GPU utilization. Long context affects prefill and may also reduce decode speed.

Use published benchmarks when possible, but for early purchase advice, memory capacity + memory bandwidth are the two most important signals.

## Purchase-advice pattern

When a user asks “is X GB enough?”:

1. Identify target model size and quant: e.g. 27B Q4/Q5/Q8.
2. Estimate weights.
3. Estimate KV for requested context length.
4. Add OS/apps and runtime overhead.
5. Decide if the result is “fits”, “comfortable”, or “possible but annoying”.
6. For Macs, explicitly mention that memory is not upgradeable and SSD can be external.

For the user's recurring 27B coding-agent scenario, the default recommendation is:

```text
Minimum: 64GB unified memory with 27B Q4/Q5 and ~32K context.
Comfortable: 128GB unified memory with 27B Q4/Q5/Q8 and ~64K context.
Cloud-like long-context: 128GB+ with KV quantization and careful context management.
```
