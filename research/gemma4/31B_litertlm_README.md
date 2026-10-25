---
license: apache-2.0
base_model:
- google/gemma-4-31B-it
tags:
  - litert-lm
---
# litert-community/gemma-4-31B-it-litert-lm

Main Model Card: [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it)

This model card provides the Gemma 4 31B model in LiteRT-LM format that is ready for deployment on web and desktop.  Please check back here regularly for updates on wider platform support and further functionality improvements.  The current LiteRT-LM version supports text; audio, image, and multitoken prediction support will be available in a future update. 

Gemma is a family of lightweight, state-of-the-art open models from Google, built from the same research and technology used to create the Gemini models. This particular Gemma 4 model is a medium size so it is ideal for desktop use cases. By running this model on device, users can have private access to Generative AI technology without even requiring an internet connection.

These models are provided in the `.litertlm` format for use with the LiteRT-LM framework. LiteRT-LM is a specialized orchestration layer built directly on top of LiteRT, Google’s high-performance multi-platform runtime trusted by millions of Android and edge developers. LiteRT provides the foundational hardware acceleration via XNNPack for CPU and ML Drift for GPU. LiteRT-LM adds the specialized GenAI libraries and APIs, such as KV-cache management, prompt templating, and function calling. This integrated stack is the same technology powering the Google AI Edge Gallery showcase app.

The model is provided as a QAT quantized model with blockwise int4 weights and float activations, specially optimized for running on GPU.

> **Requirement:** Running this model on Desktop requires **LiteRT-LM v0.17.1 or later**.

## Try Gemma 4 31B

<div align="center">

| [<svg xmlns="http://www.w3.org/2000/svg" height="72px" viewBox="0 -960 960 960" width="72px" fill="currentColor"><path d="M320-120v-40l80-80H160q-33 0-56.5-23.5T80-320v-440q0-33 23.5-56.5T160-840h640q33 0 56.5 23.5T880-760v440q0 33-23.5 56.5T800-240H560l80 80v40H320ZM160-440h640v-320H160v320Zm0 0v-320 320Z"/></svg>](https://ai.google.dev/edge/litert-lm/cli) |  [<svg xmlns="http://www.w3.org/2000/svg" height="72px" viewBox="0 -960 960 960" width="72px" fill="currentColor"><path d="M838-79 710-207v103h-60v-206h206v60H752l128 128-42 43Zm-358-1q-83 0-156-31.5T197-197q-54-54-85.5-126.36T80-478q0-83.49 31.5-156.93Q143-708.36 197-762.68 251-817 324-848.5 397-880 480-880t156 31.5q73 31.5 127 85.82 54 54.32 85.5 127.75Q880-561.49 880-478q0 23-2 44.5t-7 43.5h-63q6-21.67 9-43.33 3-21.67 3-44.47 0-22.8-2.95-45.6-2.94-22.8-8.83-45.6H648q2 23 4 45.5t2 45q0 22.5-1.25 44.5T649-390h-61q3-22 4.5-44t1.5-44q0-22.75-1.5-45.5T588-569H373.42q-3.42 23-4.92 45.5t-1.5 45q0 22.5 1.5 44.5t4.5 44h197v60H384q14 53 34 104t62 86q23 0 45-2.5t45-7.5v60q-23 5-45 7.5T480-80ZM151.78-390H312q-2.5-22-3.75-44T307-478q0-22.75 1-45.5t3-45.5H151.71q-5.85 22.8-8.78 45.6-2.93 22.8-2.93 45.6t2.95 44.47q2.94 21.66 8.83 43.33ZM172-629h149.59q11.41-48 28.91-93.5T395-810q-71 24-129.5 69.5T172-629Zm222 478q-26-41-43.5-86T323-330H172q33 67 91 114t131 65Zm-10-478h193q-13-54-36-104t-61-89q-38 40-61 89.5T384-629Zm255.34 0H788q-35-66-93-112t-129-68q27 41 44.5 86.5t28.84 93.5Z"/></svg>](https://huggingface.co/spaces/tylermullen/Gemma4) |
| :---: | :---: |
| [Desktop](https://ai.google.dev/edge/litert-lm/cli)| [Web](https://huggingface.co/spaces/tylermullen/Gemma4) |

</div>


## Build with Gemma 4 31B and LiteRT-LM

Ready to integrate this into your product? Get started [with LiteRT-LM documentation](https://ai.google.dev/edge/litert-lm/overview).

## Gemma 4 31B Performance on LiteRT-LM

Desktop benchmarks were taken using 8192 prefill tokens and 512 decode tokens with a context length of 16384 tokens via LiteRT-LM CLI. Model size is the size of the file on disk.

**Linux**

| Device &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| Backend | Prefill (tokens/sec) | Decode (tokens/sec) | Init. time (sec) | Model size (MB) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| NVidia 4090 24GB  | GPU | 1183 | 28 | 31.30 | 19218 |


**macOS**

| Device &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| Backend | Prefill (tokens/sec) | Decode (tokens/sec) | Init. time (sec) | Model size (MB) | GPU Memory (MB) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Macbook Pro 2024 (M4 Max) 48GB  | GPU | 215 | 18 | 14.49 | 19218 | ~21170 |


**Web**

Web benchmarks were taken in Chrome using 1024 prefill tokens and 256 decode tokens with a context length of 1280 tokens. The model can support up to 80k context length.

| Device &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;| Backend | Quantization | Prefill (tokens/sec) | Decode (tokens/sec) | <span style="white-space: nowrap;">Time-to-first</span>-token (sec) | Model size (MB) | GPU Memory (MB) | Peak CPU Memory (MB) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| MacBook Pro 2024 (M4 Max) 48GB  | GPU | Q4_0 | 148 | 7 | 17.1 | 19218 | ~19600 | ~4500 |
