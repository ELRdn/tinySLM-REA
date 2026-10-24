#!/usr/bin/env python3
"""Measure tokenizer fertility on Japanese / English / code.

This is a small, reproducible illustration used in REPORT.md chapter 5.
It downloads tokenizer.json + config.json from Hugging Face unless a local
cache is present.

Usage:
    python tokenizer_fertility.py
    python tokenizer_fertility.py --local-dir ../research/tokenizers

Note: one sentence is not a full fertility study. Treat the numbers as
illustrative, especially for languages with byte fallback.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

MODELS = {
    "qwen3.5-2b": "Qwen/Qwen3.5-2B",
    "smollm3-3b": "HuggingFaceTB/SmolLM3-3B",
    "gemma3-270m": "google/gemma-3-270m-it",
    "llama3.2-1b": "unsloth/Llama-3.2-1B-Instruct",
    "phi4-mini": "microsoft/Phi-4-mini-instruct",
    "bitnet2b4t": "microsoft/bitnet-b1.58-2B-4T",
    "qwen3-0.6b": "Qwen/Qwen3-0.6B",
    "tinylama-1.1b": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
}

TEXTS = {
    "ja": "小さなモデルが大きなモデルに勝つためには、データの質、蒸留、量子化、推論時の工夫、そして評価の公正さが重要です。",
    "ja2": "今日は良い天気ですね。公園を散歩して、アイスクリームを食べました。",
    "en": "A small model can outperform a large model when the task is narrow, the data is clean, and inference cost matters.",
    "code": "def fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)\n",
}


def ensure_files(name: str, repo: str, local_dir: Path):
    d = local_dir / name
    d.mkdir(parents=True, exist_ok=True)
    for fn in ("tokenizer.json", "config.json", "tokenizer_config.json"):
        p = d / fn
        if p.exists():
            continue
        from huggingface_hub import hf_hub_download
        src = hf_hub_download(repo_id=repo, filename=fn, repo_type="model")
        p.write_bytes(Path(src).read_bytes())
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-dir", default=str(Path(__file__).resolve().parent.parent / "research" / "tokenizers"))
    args = ap.parse_args()
    local_dir = Path(args.local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    try:
        from tokenizers import Tokenizer
    except ImportError as e:
        raise SystemExit("pip install tokenizers huggingface_hub") from e

    rows = []
    for name, repo in MODELS.items():
        try:
            d = ensure_files(name, repo, local_dir)
            tok = Tokenizer.from_file(str(d / "tokenizer.json"))
            cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
            c = cfg.get("text_config", cfg)
            vocab = c.get("vocab_size")
            hidden = c.get("hidden_size")
            row = {
                "name": name,
                "vocab": vocab,
                "hidden": hidden,
                "layers": c.get("num_hidden_layers"),
                "intermediate": c.get("intermediate_size"),
                "emb_params": (vocab * hidden) if vocab and hidden else None,
            }
            for key, text in TEXTS.items():
                row[key] = len(tok.encode(text).ids)
                row[key + "_chars"] = len(text)
            rows.append(row)
        except Exception as e:
            print(f"# {name}: {type(e).__name__}: {e}")

    header = f"{'model':16s} {'vocab':>8s} {'hidden':>7s} {'emb(M)':>8s} {'ja':>4s} {'ja2':>4s} {'en':>4s} {'code':>5s}"
    print(header)
    print("-" * len(header))
    for r in rows:
        emb = f"{r['emb_params']/1e6:.1f}" if r["emb_params"] else "-"
        print(f"{r['name']:16s} {str(r['vocab']):>8s} {str(r['hidden']):>7s} {emb:>8s} "
              f"{r['ja']:>4d} {r['ja2']:>4d} {r['en']:>4d} {r['code']:>5d}")

    print("\nNote: token counts include special tokens for some tokenizers (e.g., BOS).")
    print("The Japanese sentence is one sample; do not generalize without a larger corpus.")


if __name__ == "__main__":
    main()
