# slm-plc-bench

> 🚧 **Work in progress.** The project is being built step by step. The sections below describe the target scope; only the steps checked in the roadmap are done. No benchmark results on PLC code have been published yet.

**Can small, local language models write reliable PLC code, and at what cost compared to large models?**

`slm-plc-bench` is a benchmark for generating **IEC 61131-3 Structured Text** (the language of industrial controllers) with language models. It compares **small open-weight models running locally** with **large cloud models**. Every generated program is checked automatically, so the comparison measures code that actually works, not code that only looks right.

## Why

Industrial engineering assistants built on large cloud models are expensive and depend on the network. Customer sites often need on-premise deployment. The question is when a small local model is good enough, and when it should hand the task over to a large one.

## What the project will include

### 1. A task set
Industrial automation tasks written in natural language, each with a reference solution and test scenarios:
- motor start/stop with stop priority
- start fault detection with a timer (`TON`)
- tank filling with high/low level sensors
- event counter with edge detection (`R_TRIG`)
- blinking signal

### 2. Automatic verification
- syntax and type checking of the generated Structured Text
- cycle-by-cycle simulation against the test scenarios (no vendor software required)
- tests of the tests: each scenario must reject plausible wrong programs

### 3. Models compared
- small local models served with **Ollama** (e.g. `qwen2.5-coder:1.5b`, larger variants up to ~7B)
- a large model through an OpenAI-compatible API, as the reference

### 4. Generation strategies
- **single shot**: one attempt
- **repair loop**: the verifier's error messages are fed back to the model
- **cascade**: the small model first, escalation to the large model only when verification fails

### 5. Metrics
- task success rate and output validity
- **cost per successful task**
- latency (p50 / p95) and memory usage
- confidence intervals and paired statistical tests (McNemar) between configurations

### 6. Planned extensions
- grammar-constrained / structured generation
- quantization levels and inference engines (llama.cpp, vLLM)
- an agent version with **LangGraph** and tools exposed through **MCP**

## Roadmap

- [x] Step 0: project setup, local model served with Ollama through an OpenAI-compatible API
- [x] Step 1: measuring local inference (throughput, time to first token, prefill vs decode, temperature) for 1.5B and 7B models
- [ ] Task format and first tasks
- [ ] Structured Text verifier and simulator
- [ ] Benchmark runner and result logging
- [ ] Single shot vs repair loop vs cascade
- [ ] Metrics, statistics and report
- [ ] Extensions (constrained generation, quantization, agents)

## Stack

Python · Ollama · OpenAI-compatible API · pytest · Git

Runs on an Apple Silicon laptop (M4 Max, 64 GB) for the local models.

## Author

Maximilien Muller, 4th-year engineering student in Data Science & AI at ESIEE Paris.
