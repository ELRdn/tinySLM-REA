# Tokenizer experiment

The tokenizer JSON files are **not committed** because each is several MB. `experiments/tokenizer_fertility.py` downloads them from Hugging Face on first run.

Models used:

| Key | Hugging Face repo |
|---|---|
| `qwen3.5-2b` | `Qwen/Qwen3.5-2B` |
| `smollm3-3b` | `HuggingFaceTB/SmolLM3-3B` |
| `gemma3-270m` | `google/gemma-3-270m-it` |
| `llama3.2-1b` | `unsloth/Llama-3.2-1B-Instruct` |
| `phi4-mini` | `microsoft/Phi-4-mini-instruct` |
| `bitnet2b4t` | `microsoft/bitnet-b1.58-2B-4T` |
| `qwen3-0.6b` | `Qwen/Qwen3-0.6B` |
| `tinylama-1.1b` | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` |

Run:

```bash
python experiments/tokenizer_fertility.py
```

The Japanese sample is one sentence; this is an illustration, not a full fertility study.
