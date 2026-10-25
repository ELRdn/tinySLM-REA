#!/usr/bin/env python3
"""Mobile SLM requirement calculator.

Computes weight/KV memory, fit against iPhone/Android app budgets, and
bandwidth-bound decode estimates. Also emits the charts used in
MOBILE-SLM.md.

All hardware numbers are either sourced in MOBILE-SLM.md or explicitly
marked as estimates. This script is a planning tool, not a benchmark.

Usage:
    python mobile_requirements.py
    python mobile_requirements.py --json ../rea/evidence/mobile_requirements.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

GIB = 2**30
MIB = 2**20

# ---------------------------------------------------------------------------
# Models
# params: language-model parameters (billions)
# kv_bytes_per_token: K+V bytes per token for layers whose cache grows
# fixed_kv_bytes: sliding-window / fixed cache (e.g. Gemma 3 270M sliding layers)
# max_ctx: native context
# bits: default storage bits per parameter (payload + scales, not file overhead)
# file_bits: optional measured whole-file bits per parameter
# ---------------------------------------------------------------------------
MODELS = [
    dict(name="Gemma 3 270M", params=0.27, kv_bytes_per_token=3 * 1 * 512 * 2,
         fixed_kv_bytes=15 * 512 * 512 * 2, max_ctx=32768, bits=4.5,
         note="15 sliding layers capped at 512; 3 full layers"),
    dict(name="Qwen3 0.6B", params=0.60, kv_bytes_per_token=28 * 8 * 256 * 2,
         fixed_kv_bytes=0, max_ctx=40960, bits=4.5, note="full attention"),
    dict(name="Llama 3.2 1B", params=1.24, kv_bytes_per_token=16 * 8 * 128 * 2,
         fixed_kv_bytes=0, max_ctx=131072, bits=4.5, note="full attention"),
    dict(name="Qwen3.5 2B", params=1.88, kv_bytes_per_token=6 * 2 * 512 * 2,
         fixed_kv_bytes=0, max_ctx=262144, bits=4.5, note="3:1 hybrid"),
    dict(name="Bonsai 2B (ternary)", params=1.881825088,
         kv_bytes_per_token=6 * 2 * 512 * 2, fixed_kv_bytes=0,
         max_ctx=262144, bits=1.8245413295287092, file_bits=1.8245413295287092,
         note="measured GGUF: 151 PTQ1_0 + 169 F32 tensors"),
    dict(name="SmolLM3 3B", params=3.0, kv_bytes_per_token=36 * 4 * 256 * 2,
         fixed_kv_bytes=0, max_ctx=65536, bits=4.5, note="full attention"),
    dict(name="Llama 3.2 3B", params=3.21, kv_bytes_per_token=28 * 8 * 256 * 2,
         fixed_kv_bytes=0, max_ctx=131072, bits=4.5, note="full attention"),
    dict(name="Qwen3 4B", params=4.0, kv_bytes_per_token=36 * 8 * 256 * 2,
         fixed_kv_bytes=0, max_ctx=262144, bits=4.5, note="full attention"),
    dict(name="Bonsai 4B (ternary)", params=4.205751296,
         kv_bytes_per_token=8 * 4 * 512 * 2, fixed_kv_bytes=0,
         max_ctx=262144, bits=1.806193192456428, file_bits=1.806193192456428,
         note="measured GGUF header: 32 layers, 8 full, 4 KV heads"),
    dict(name="Llama 3.2 8B", params=8.0, kv_bytes_per_token=32 * 8 * 256 * 2,
         fixed_kv_bytes=0, max_ctx=131072, bits=4.5, note="full attention"),
    dict(name="Bonsai 9B (ternary)", params=8.953803264,
         kv_bytes_per_token=8 * 4 * 512 * 2, fixed_kv_bytes=0,
         max_ctx=262144, bits=1.7847048161365544, file_bits=1.7847048161365544,
         note="measured GGUF header: 32 layers, 8 full, 4 KV heads"),
]

# ---------------------------------------------------------------------------
# Devices
# app_budget_gib: effective foreground-app memory available for weights + KV
#   iPhone: Bonsai whitepaper reports ~6 GB per-app limit on iPhone 17 Pro Max.
#   Android: no fixed limit; these are planning heuristics (LMK + zRAM + OS).
# bandwidth_gbs: theoretical peak DRAM bandwidth
#   iPhone 17 Pro: 64-bit LPDDR5X, estimated 76.8 GB/s (Apple does not publish).
#   iPhone 18 Pro: Apple says +50% vs A19 Pro; 96-bit leak -> ~115.2 GB/s.
#   Android flagship: LPDDR5X 10667 (MediaTek Dimensity 9500) 64-bit -> 85.3 GB/s.
# ---------------------------------------------------------------------------
DEVICES = [
    dict(name="iPhone 17 Pro Max (12GB)", platform="iOS", ram_gib=12,
         app_budget_gib=6.0, bandwidth_gbs=76.8, npu="A19 Pro 16-core ANE",
         source="Bonsai whitepaper 6GB; bandwidth estimate"),
    dict(name="iPhone 18 Pro Max (12GB)", platform="iOS", ram_gib=12,
         app_budget_gib=6.0, bandwidth_gbs=115.2, npu="A20 Pro dual 16-core ANE",
         source="budget assumed same as 17 Pro Max; bandwidth derived from +50%"),
    dict(name="Galaxy S26 Ultra (12GB)", platform="Android", ram_gib=12,
         app_budget_gib=5.5, bandwidth_gbs=85.3, npu="Snapdragon 8 Elite Gen 5 Hexagon",
         source="planning heuristic; LPDDR5X 10667 estimate"),
    dict(name="Galaxy S26 Ultra (16GB)", platform="Android", ram_gib=16,
         app_budget_gib=7.5, bandwidth_gbs=85.3, npu="Snapdragon 8 Elite Gen 5 Hexagon",
         source="planning heuristic; LPDDR5X 10667 estimate"),
    dict(name="Pixel 11 Pro XL (16GB)", platform="Android", ram_gib=16,
         app_budget_gib=7.5, bandwidth_gbs=85.3, npu="Google Tensor G6 TPU",
         source="planning heuristic; bandwidth estimate"),
    dict(name="Android 8GB class", platform="Android", ram_gib=8,
         app_budget_gib=3.5, bandwidth_gbs=51.2, npu="varies (often no usable LLM NPU)",
         source="planning heuristic; LPDDR5 6400 estimate"),
]

# LiteRT-LM benchmark table (official docs, accessed 2026-10-25).
# Decode tok/s, batch 1, model size as published. CPU/GPU are separate rows.
LITERT = [
    dict(model="Gemma4-E2B", size_mb=2583, device="Galaxy S26 Ultra", cpu=47, gpu=52, prefill_gpu=3808),
    dict(model="Gemma4-E2B", size_mb=2583, device="iPhone 17 Pro", cpu=25, gpu=57, prefill_gpu=2878),
    dict(model="Gemma4-E4B", size_mb=3654, device="Galaxy S26 Ultra", cpu=18, gpu=22, prefill_gpu=1293),
    dict(model="Gemma4-E4B", size_mb=3654, device="iPhone 17 Pro", cpu=10, gpu=25, prefill_gpu=1189),
    dict(model="Gemma3-1B", size_mb=1005, device="Galaxy S24 Ultra", cpu=33, gpu=24, prefill_gpu=None),
    dict(model="Phi-4-mini", size_mb=3906, device="Galaxy S24 Ultra", cpu=7, gpu=10, prefill_gpu=None),
    dict(model="Qwen2.5-1.5B", size_mb=1598, device="Galaxy S25 Ultra", cpu=34, gpu=31, prefill_gpu=None),
    dict(model="Qwen3-0.6B", size_mb=586, device="Vivo X300 Pro", cpu=9, gpu=21, prefill_gpu=None),
]

# Bonsai measured decode (whitepaper, iPhone 17 Pro Max, PQ2_0).
BONSAI_MEASURED = [
    dict(model="Bonsai 2B", size_gb=0.52, tok_s=89.9),
    dict(model="Bonsai 4B", size_gb=0.95, tok_s=39.8),
    dict(model="Bonsai 9B", size_gb=2.0, tok_s=22.3),
]


def weights_gib(params_b: float, bits: float) -> float:
    return params_b * 1e9 * bits / 8 / GIB


def kv_gib(model: dict, ctx: int) -> float:
    return (model["kv_bytes_per_token"] * ctx + model["fixed_kv_bytes"]) / GIB


def total_gib(model: dict, ctx: int, bits: float | None = None,
              runtime_gib: float = 0.35) -> float:
    b = model["bits"] if bits is None else bits
    return weights_gib(model["params"], b) + kv_gib(model, ctx) + runtime_gib


def decode_estimate(model: dict, ctx: int, bandwidth_gbs: float,
                    efficiency: float, bits: float | None = None) -> float:
    b = model["bits"] if bits is None else bits
    bytes_per_token = (model["params"] * 1e9 * b / 8
                       + model["kv_bytes_per_token"] + model["fixed_kv_bytes"] / max(ctx, 1))
    return bandwidth_gbs * 1e9 * efficiency / bytes_per_token


def build_table() -> list[dict]:
    rows = []
    for m in MODELS:
        row = {"model": m["name"], "params_b": m["params"],
               "bits": m["bits"], "note": m["note"]}
        for ctx in (4096, 32768, 131072, 262144):
            row[f"ctx_{ctx}"] = (total_gib(m, ctx) if ctx <= m["max_ctx"] else None)
        row["weights_gib"] = weights_gib(m["params"], m["bits"])
        row["kv_per_token_kib"] = m["kv_bytes_per_token"] / 1024
        rows.append(row)
    return rows


def fit_rows() -> list[dict]:
    rows = []
    for m in MODELS:
        for ctx in (4096, 32768, 131072, 262144):
            if ctx > m["max_ctx"]:
                continue
            total = total_gib(m, ctx)
            fit = []
            for d in DEVICES:
                if total <= d["app_budget_gib"]:
                    fit.append(d["name"])
            rows.append({"model": m["name"], "ctx": ctx, "total_gib": total,
                         "fits": fit})
    return rows


def write_json(path: Path):
    out = {
        "schema": "tinySLM-REA/mobile-requirements-v1",
        "date": "2026-10-25",
        "assumptions": {
            "runtime_gib": 0.35,
            "iphone_app_budget_gib": 6.0,
            "iphone_note": "Bonsai reports ~6GB; this model treats it as 6.0GiB. If the vendor meant decimal 6GB, the budget is 5.59GiB.",
            "android_budgets_gib": {"8GB": 3.5, "12GB": 5.5, "16GB": 7.5},
            "note": "Android budgets are planning heuristics, not OS limits.",
        },
        "models": MODELS,
        "devices": DEVICES,
        "table": build_table(),
        "fit": fit_rows(),
        "litert": LITERT,
        "bonsai_measured": BONSAI_MEASURED,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {path}")


def charts(outdir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    outdir.mkdir(parents=True, exist_ok=True)

    # 1. Memory fit at 4K and 32K (4-bit / ternary)
    selected = [m for m in MODELS if m["name"] in {
        "Gemma 3 270M", "Qwen3 0.6B", "Llama 3.2 1B", "Qwen3.5 2B",
        "Bonsai 2B (ternary)", "Llama 3.2 3B", "Qwen3 4B",
        "Bonsai 4B (ternary)", "Bonsai 9B (ternary)"}]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharey=True)
    for ax, ctx, title in zip(axes, (4096, 32768), ("4K context", "32K context")):
        names = [m["name"].replace(" (ternary)", "\n(ternary)") for m in selected]
        totals = [total_gib(m, ctx) for m in selected]
        colors = ["#059669" if m["bits"] < 2 else "#2563eb" for m in selected]
        bars = ax.bar(range(len(selected)), totals, color=colors)
        ax.set_xticks(range(len(selected)))
        ax.set_xticklabels(names, rotation=40, ha="right", fontsize=8)
        ax.set_ylabel("weights + KV + runtime (GiB)")
        ax.set_title(f"Mobile memory fit: {title}")
        ax.grid(axis="y", alpha=0.25)
        for b, v in zip(bars, totals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=7)
        for y, label, style in [(3.5, "Android 8GB budget", ":"),
                                (5.5, "Android 12GB budget", "--"),
                                (6.0, "iPhone ~6GB budget", "-"),
                                (7.5, "Android 16GB budget", "-.")]:
            ax.axhline(y, color="#6b7280", linestyle=style, linewidth=1)
            ax.text(len(selected) - 0.4, y + 0.08, label, fontsize=6.5,
                    ha="right", color="#374151")
        ax.set_ylim(0, max(10.5, max(totals) * 1.15))
    fig.tight_layout()
    fig.savefig(outdir / "mobile_memory_fit.png", dpi=160)
    plt.close(fig)

    # 2. KV cache vs context
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ctx = np.arange(1024, 262145, 2048)
    for m, color in [(next(x for x in MODELS if x["name"] == "Qwen3 0.6B"), "#dc2626"),
                     (next(x for x in MODELS if x["name"] == "Llama 3.2 1B"), "#f59e0b"),
                     (next(x for x in MODELS if x["name"] == "Qwen3.5 2B"), "#2563eb"),
                     (next(x for x in MODELS if x["name"] == "Bonsai 2B (ternary)"), "#059669"),
                     (next(x for x in MODELS if x["name"] == "Bonsai 9B (ternary)"), "#7c3aed")]:
        y = [kv_gib(m, int(c)) for c in ctx]
        ax.plot(ctx / 1024, y, label=f"{m['name']} ({m['kv_bytes_per_token']/1024:.0f} KiB/token)",
                color=color, linewidth=1.8)
    ax.set_xlabel("context length (K tokens)")
    ax.set_ylabel("KV cache (GiB, one sequence, FP16)")
    ax.set_title("KV cache grows linearly with context (except sliding-window models)")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(outdir / "mobile_kv_context.png", dpi=160)
    plt.close(fig)

    # 3. Peak vs effective bandwidth
    fig, ax = plt.subplots(figsize=(9, 4.8))
    devs = [d for d in DEVICES if d["name"] in {
        "iPhone 17 Pro Max (12GB)", "iPhone 18 Pro Max (12GB)",
        "Galaxy S26 Ultra (12GB)", "Android 8GB class"}]
    labels = [d["name"].replace(" (12GB)", "").replace(" (16GB)", "") for d in devs]
    x = np.arange(len(devs))
    ax.bar(x - 0.2, [d["bandwidth_gbs"] for d in devs], width=0.4,
           label="theoretical peak", color="#93c5fd")
    ax.bar(x + 0.2, [d["bandwidth_gbs"] * 0.55 for d in devs], width=0.4,
           label="55% efficiency (planning)", color="#2563eb")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("DRAM bandwidth (GB/s)")
    ax.set_title("Mobile decode is bandwidth-bound: peak vs realistic")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "mobile_bandwidth.png", dpi=160)
    plt.close(fig)

    # 4. Bonsai effective bandwidth (measured)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    eff = [b["size_gb"] * b["tok_s"] for b in BONSAI_MEASURED]
    bars = ax.bar([b["model"] for b in BONSAI_MEASURED], eff,
                  color=["#059669", "#2563eb", "#7c3aed"])
    ax.axhline(76.8, color="#dc2626", linestyle="--", label="iPhone 17 Pro peak (est. 76.8 GB/s)")
    ax.set_ylabel("effective read bandwidth (GB/s)")
    ax.set_title("Bonsai on iPhone 17 Pro Max: effective bandwidth")
    ax.legend(fontsize=8)
    for b, v in zip(bars, eff):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}", ha="center",
                va="bottom", fontsize=9)
    ax.set_ylim(0, 90)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "mobile_bonsai_bandwidth.png", dpi=160)
    plt.close(fig)

    # 5. LiteRT-LM Android vs iPhone
    pairs = [("Gemma4-E2B", 2583), ("Gemma4-E4B", 3654)]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    width = 0.35
    for i, (model, _) in enumerate(pairs):
        android = next(x for x in LITERT if x["model"] == model and x["device"] == "Galaxy S26 Ultra")
        iphone = next(x for x in LITERT if x["model"] == model and x["device"] == "iPhone 17 Pro")
        ax.bar(i - width / 2, android["gpu"], width, label="Galaxy S26 Ultra GPU" if i == 0 else None,
               color="#2563eb")
        ax.bar(i + width / 2, iphone["gpu"], width, label="iPhone 17 Pro GPU" if i == 0 else None,
               color="#059669")
        ax.text(i - width / 2, android["gpu"] + 1, str(android["gpu"]), ha="center", fontsize=9)
        ax.text(i + width / 2, iphone["gpu"] + 1, str(iphone["gpu"]), ha="center", fontsize=9)
    ax.set_xticks(range(len(pairs)))
    ax.set_xticklabels([p[0] for p in pairs])
    ax.set_ylabel("decode tok/s (batch 1)")
    ax.set_title("Same runtime (LiteRT-LM), different platform")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "mobile_litert_bench.png", dpi=160)
    plt.close(fig)

    print(f"wrote charts to {outdir}")


def print_table():
    print(f"{'model':24s} {'bits':>6s} {'wGiB':>6s} {'4K':>6s} {'32K':>6s} {'128K':>7s} {'262K':>7s}")
    for r in build_table():
        def f(v):
            return "—" if v is None else f"{v:.2f}"
        print(f"{r['model']:24s} {r['bits']:6.3f} {r['weights_gib']:6.2f} "
              f"{f(r['ctx_4096']):>6s} {f(r['ctx_32768']):>6s} "
              f"{f(r['ctx_131072']):>7s} {f(r['ctx_262144']):>7s}")
    print("\nFit (total GiB <= device app budget):")
    for r in fit_rows():
        if r["ctx"] in (4096, 32768, 131072, 262144):
            print(f"{r['model']:24s} {r['ctx']:>6d} {r['total_gib']:6.2f}  "
                  f"{', '.join(r['fits']) if r['fits'] else 'none'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--charts", default=None)
    args = ap.parse_args()
    print_table()
    if args.json:
        write_json(Path(args.json))
    if args.charts:
        charts(Path(args.charts))


if __name__ == "__main__":
    main()
