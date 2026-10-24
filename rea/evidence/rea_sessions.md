# REA session evidence

This project used REA where the target format was supported. GGUF is not a
native REA format, so the GGUF was parsed by `rea/analyze_gguf.py`.

## 1. WebGPU JavaScript application

- Tool: `analyze_javascript_application`
- Input: `rea/webgpu_app` (directory)
- Format: `directory`
- Detail: `summary`
- Evidence ID: `ev_bd837c2925b8a8f56ecc1ead2c4caf866345270ada956c0b8adb89f65371590f`
- Parent evidence ID: `ev_60dcd225cdb0ad870ece451b3f6df95520a5da0def387a46717908d9308d5d9f`
- Files: 3 relevant files, 2 parsed JavaScript files
- AST nodes: 290,975
- Findings: 40
- Parse failures: 0
- Coverage: application complete; semantic graph partial (100,000-node ceiling)
- Limitations: inert static analysis; bundle not executed; 46,107 semantic unknowns

Observed:

- quantized matmul formats: `q4_0`, `q4_k`, `q4_k_native_compact`, `q8_0`, `iq`, `lut32`, `lut16`, `lut32_compact`, `lut16_compact`, `lut2_32`, `lut2_16`, `q6_k`, `q5_k`, `q3_k`, `q2_k`, `q1_0`
- INT8 KV-cache path with key/value scales
- `specDecodeRunner(){return null}` for this model
- `top_k` capped at 64
- Hadamard WGSL templates
- Qwen3.5 hybrid-attention metadata (`full_attention_interval`, `layer_types`)

Not observed: runtime execution, performance, numerical equivalence.

## 2. Ollama PE

- Tool: `open_binary` + `inspect_pe_resources`
- Target: `C:\Users\hiron\AppData\Local\AMD\AI_Bundle\Ollama\ollama.exe`
- SHA-256: `9eaec399fd941073f8ddfbd56e0447f77fca5c006b26b8b1874a7fb12719b2a0`
- Format: PE32+
- Evidence ID: `ev_eeebbf62039e9537176b4b9b414cf49a7f4407f3d0352264eaf4c5f5d801157d`
- Resources: none
- Note: the binary is a Go executable; no PE resources. Not used for the main analysis.

## 3. Native decompilation

Ghidra was not configured on this host (`GHIDRA_INSTALL_DIR` unset). No native
decompilation was performed. `binary_overview` returned `provider_unavailable`.
This is a limitation, not a claim of analysis.

## 4. GGUF

REA `open_binary` rejected the GGUF as `unsupported binary format`. Therefore:

- `rea/analyze_gguf.py` implements the GGUF v3 parser and PTQ1_0 decoder.
- `rea/evidence/bonsai2b.json` records the observations and derived numbers.
- `rea/evidence/ptq1_block.md` documents the 28-byte block layout.

This is a transparent division of labor: REA for supported JavaScript/PE
targets; a custom parser for the model container.
