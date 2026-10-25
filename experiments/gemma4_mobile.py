#!/usr/bin/env python3
"""Gemma 4 mobile fit, KV, quantization and chart reproduction.

Every input is an evidence file produced by the parsers in ``rea/``:

  rea/evidence/gemma4_safetensors_breakdown.json
  rea/evidence/gemma4_qat_gguf.json
  rea/evidence/gemma4_litertlm_quantization.json
  rea/evidence/gemma4_litertlm_12b_quantization.json
  rea/evidence/gemma4_ternary_error.json

The script never downloads a model. It recomputes the report's tables from
observed parameter counts and observed container sizes, then optionally
writes the charts under ``assets/``.

Usage:
    python experiments/gemma4_mobile.py --json rea/evidence/gemma4_mobile_fit.json
    python experiments/gemma4_mobile.py --charts assets

Notes
-----
* 1 GiB = 2**30 bytes; 1 GB = 10**9 bytes. File sizes are reported in GiB.
* ``ternary`` means: linear projections at 1.75 bit/weight (Bonsai PTQ1_0-like
  payload), while embeddings, PLE, gates and norms keep the precision observed
  in Google's shipped LiteRT-LM bundle. It is deliberately *not* "everything at
  1.58 bit".
* ``qat`` means the shipped LiteRT-LM GPU bundle (text decoder) for E2B/E4B/12B,
  and the shipped LiteRT-LM GPU bundle for 26B/31B. GGUF Q4_0 sizes are kept
  separately because they include PLE at Q6_K and are much larger.
* KV bytes use the exact hybrid geometry from the HF configs: full-attention
  layers keep the whole context, sliding layers keep only ``sliding_window``.
* Runtime overhead is a scenario, not a measurement: 0.35 GiB (lean), 1.0 GiB
  (realistic GPU, from the 12B desktop delta) and 1.5 GiB (heavy/web-like).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

GIB = 2**30
ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "rea" / "evidence"


def load(name: str) -> dict:
    with open(EV / name, encoding="utf-8") as f:
        return json.load(f)


SAFE = load("gemma4_safetensors_breakdown.json")
QAT_GGUF = load("gemma4_qat_gguf.json")
LITERT = load("gemma4_litertlm_quantization.json")
LITERT_12B = load("gemma4_litertlm_12b_quantization.json")

# ---------------------------------------------------------------------------
# Observed geometry (HF config.json) and observed container sizes (bytes).
# ---------------------------------------------------------------------------
MODELS: dict[str, dict] = {
    "E2B": dict(
        total=5_123_178_979,
        linear=1_881_953_280,
        embed=2_778_988_544,
        nontext=475_729_088,
        layers=35, full_non=3, sliding_non=12,
        kv_local=1, kv_global=1, win=512, native_ctx=131_072,
        litert_ctx=32_768,
        litert_bytes=2_008_432_640,
        generic_bytes=2_588_147_712,
        gguf_bytes=3_349_516_256,
        mmlu=60.0, mmmu=67.4, ifeval=90.4, arena=None,
        token_bpw=2.04, ple_bpw=4.12,
    ),
    "E4B": dict(
        total=7_996_157_418,
        linear=4_000_342_528,
        embed=3_544_711_168,
        nontext=478_088_384,
        layers=42, full_non=4, sliding_non=20,
        kv_local=2, kv_global=2, win=512, native_ctx=131_072,
        litert_ctx=32_768,
        litert_bytes=2_969_059_328,
        generic_bytes=3_659_530_240,
        gguf_bytes=5_154_941_280,
        mmlu=69.4, mmmu=76.6, ifeval=96.7, arena=None,
        token_bpw=2.02, ple_bpw=2.12,
    ),
    "12B": dict(
        total=11_959_730_224,
        linear=10_899_976_192,
        embed=1_006_632_960,
        nontext=52_379_904,
        layers=48, full_non=8, sliding_non=40,
        kv_local=8, kv_global=1, win=1024, native_ctx=262_144,
        litert_ctx=131_072,
        litert_bytes=5_986_074_624,
        generic_bytes=6_883_278_368,
        gguf_bytes=6_975_879_296,
        mmlu=77.2, mmmu=83.4, ifeval=97.2, arena=None,
        token_bpw=4.02, ple_bpw=0.0,
    ),
    "26B-A4B": dict(
        total=25_805_936_206,
        linear=24_483_448_320,
        embed=738_197_504,
        nontext=572_794_416,
        layers=30, full_non=5, sliding_non=25,
        kv_local=8, kv_global=2, win=1024, native_ctx=262_144,
        litert_ctx=131_072,
        litert_bytes=15_786_524_672,
        generic_bytes=15_786_524_672,
        gguf_bytes=14_439_363_584,
        mmlu=82.6, mmmu=86.3, ifeval=98.5, arena=1438,
        token_bpw=6.56, ple_bpw=0.0,
    ),
    "31B": dict(
        total=31_273_088_876,
        linear=29_286_763_520,
        embed=1_409_286_144,
        nontext=575_743_536,
        layers=60, full_non=10, sliding_non=50,
        kv_local=16, kv_global=4, win=1024, native_ctx=262_144,
        litert_ctx=131_072,
        litert_bytes=19_217_989_632,
        generic_bytes=19_217_989_632,
        gguf_bytes=17_651_001_568,
        mmlu=85.2, mmmu=88.4, ifeval=98.9, arena=1451,
        token_bpw=6.56, ple_bpw=0.0,
    ),
}

# Non-linear bytes actually shipped in the text-only LiteRT bundles.
# E2B/E4B: component sum from the TFLite buffer inventory.
# 12B: component sum from the 12B TFLite buffer inventory.
NONLINEAR_BYTES = {
    "E2B": sum(v["bytes"] for k, v in LITERT["E2B"]["components"].items()
               if k not in ("attention", "mlp")),
    "E4B": sum(v["bytes"] for k, v in LITERT["E4B"]["components"].items()
               if k not in ("attention", "mlp")),
    "12B": sum(v["bytes"] for k, v in LITERT_12B["components"].items()
               if k not in ("attention", "mlp")),
}

DEVICES = [
    ("iPhone 6GiB", 6.0),
    ("Android 8GB", 3.5),
    ("Android 12GB", 5.5),
    ("Android 16GB", 7.5),
]
RUNTIMES = [("lean", 0.35), ("gpu", 1.0), ("heavy", 1.5)]


def kv_gib(tag: str, ctx: int, bytes_per: int = 2) -> float:
    m = MODELS[tag]
    full = m["full_non"] * 2 * m["kv_global"] * 512 * bytes_per
    slide = m["sliding_non"] * 2 * m["kv_local"] * 256 * bytes_per
    return (full * ctx + slide * m["win"]) / GIB


def ternary_bytes(tag: str) -> int:
    m = MODELS[tag]
    if tag in ("E2B", "E4B"):
        return int(NONLINEAR_BYTES[tag] + m["linear"] * 1.75 / 8)
    if tag == "12B":
        return int(m["linear"] * 1.75 / 8 + m["embed"] * m["token_bpw"] / 8
                   + 20 * 1024 * 1024)
    # Conservative for the desktop-only MoE/dense models: token embeddings at
    # the Q6_K precision observed in the QAT GGUF, not the smaller mobile schema.
    return int(m["linear"] * 1.75 / 8 + m["embed"] * m["token_bpw"] / 8
               + 20 * 1024 * 1024)


def total(tag: str, ctx: int, kind: str, runtime: float, kv_bits: int = 16) -> float:
    m = MODELS[tag]
    if kind == "ternary":
        w = ternary_bytes(tag) / GIB
    elif kind == "qat":
        w = m["litert_bytes"] / GIB
    elif kind == "gguf":
        w = m["gguf_bytes"] / GIB
    else:
        raise ValueError(kind)
    return w + kv_gib(tag, ctx, kv_bits // 8) + runtime


def fit_label(value: float, budget: float) -> str:
    if value <= 0.8 * budget:
        return "safe"
    if value <= budget:
        return "nominal"
    return "no"


def build() -> dict:
    out = {
        "schema": "tinySLM-REA/gemma4-mobile-v2",
        "date": "2026-10-25",
        "units": {"memory": "GiB (2^30 bytes)", "bytes": "bytes"},
        "assumptions": {
            "ternary_linear_bpw": 1.75,
            "runtime_gib": {k: v for k, v in RUNTIMES},
            "kv_bits_default": 16,
            "qat_container": "LiteRT-LM GPU text decoder bundle",
        },
        "devices": DEVICES,
        "models": {},
    }
    for tag, m in MODELS.items():
        rec = {k: v for k, v in m.items()}
        rec["nonlinear_bytes_observed"] = int(NONLINEAR_BYTES.get(tag, 0))
        rec["ternary_weights_gib"] = ternary_bytes(tag) / GIB
        rec["qat_weights_gib"] = m["litert_bytes"] / GIB
        rec["gguf_weights_gib"] = m["gguf_bytes"] / GIB
        rec["generic_bundle_gib"] = m["generic_bytes"] / GIB
        rec["kv_gib"] = {str(c): kv_gib(tag, c) for c in
                         (4096, 32768, 131072, 262144)}
        rec["kv_int8_gib"] = {str(c): kv_gib(tag, c, 1) for c in
                              (4096, 32768, 131072, 262144)}
        rec["total_ternary"] = {
            str(c): {name: total(tag, c, "ternary", rt) for name, rt in RUNTIMES}
            for c in (4096, 32768, 131072, 262144)}
        rec["total_qat"] = {
            str(c): {name: total(tag, c, "qat", rt, 8) for name, rt in RUNTIMES}
            for c in (4096, 32768, 131072, 262144)}
        rec["fit"] = {}
        for kind in ("ternary", "qat"):
            rec["fit"][kind] = {}
            for ctx in (32768, 131072):
                for name, rt in RUNTIMES:
                    v = total(tag, ctx, kind, rt, 16 if kind == "ternary" else 8)
                    rec["fit"][kind][f"{ctx}_{name}"] = {
                        "gib": v,
                        "label": {d: fit_label(v, b) for d, b in DEVICES},
                    }
        out["models"][tag] = rec
    return out


def charts(outdir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    outdir.mkdir(parents=True, exist_ok=True)
    data = build()
    M = data["models"]
    order = ["E2B", "E4B", "12B", "26B-A4B", "31B"]
    labels = {
        "E2B": "E2B\n(2.3B eff.)", "E4B": "E4B\n(4.5B eff.)",
        "12B": "12B", "26B-A4B": "26B-A4B\n(3.8B active)", "31B": "31B",
    }
    colors = ["#059669", "#2563eb", "#f59e0b", "#7c3aed", "#dc2626"]

    # 1. parameter components
    comp = {
        "E2B": [2.779, 0.297, 1.557, 0.476, 0.014],
        "E4B": [3.545, 0.642, 3.303, 0.478, 0.028],
        "12B": [1.007, 2.407, 8.493, 0.052, 0.002],
        "26B-A4B": [0.738, 1.110, 23.373, 0.573, 0.002],
        "31B": [1.409, 8.478, 20.809, 0.576, 0.002],
    }
    names = ["Embedding + PLE", "Attention", "MLP / MoE", "Audio / Vision", "Norms"]
    cols = ["#2563eb", "#059669", "#f59e0b", "#7c3aed", "#6b7280"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    y = np.arange(len(order)); left = np.zeros(len(order))
    for i, (n, c) in enumerate(zip(names, cols)):
        vals = np.array([comp[t][i] for t in order])
        ax.barh(y, vals, left=left, color=c, label=n)
        for yi, v, l in zip(y, vals, left):
            if v > 1.2:
                ax.text(l + v / 2, yi, f"{v:.1f}", ha="center", va="center",
                        fontsize=7, color="white")
        left += vals
    ax.set_yticks(y); ax.set_yticklabels([labels[t] for t in order])
    ax.invert_yaxis(); ax.set_xlabel("parameters (billions)")
    ax.set_title("Gemma 4 is not one size: PLE dominates E2B/E4B, experts dominate 26B")
    ax.legend(loc="lower right", fontsize=8); ax.grid(axis="x", alpha=.25)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_components.png", dpi=170)
    plt.close(fig)

    # 2. memory fit at 32K, lean runtime
    fig, ax = plt.subplots(figsize=(10, 5.4))
    x = np.arange(len(order)); w = .36
    t = [M[k]["total_ternary"]["32768"]["lean"] for k in order]
    q = [M[k]["total_qat"]["32768"]["lean"] for k in order]
    b1 = ax.bar(x - w / 2, t, w, label="ternary estimate (FP16 KV)", color="#059669")
    b2 = ax.bar(x + w / 2, q, w, label="Gemma 4 QAT (INT8 KV, LiteRT-LM)", color="#2563eb")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + .12,
                    f"{b.get_height():.1f}", ha="center", fontsize=7)
    for yv, lab, ls in [(3.5, "Android 8GB 3.5GiB", ":"), (5.5, "Android 12GB 5.5GiB", "--"),
                        (6.0, "iPhone ~6GiB", "-"), (7.5, "Android 16GB 7.5GiB", "-.")]:
        ax.axhline(yv, color="#6b7280", linestyle=ls, linewidth=1)
        ax.text(len(order) - .45, yv + .08, lab, fontsize=7, ha="right", color="#374151")
    ax.set_xticks(x); ax.set_xticklabels([labels[k] for k in order])
    ax.set_ylabel("weights + 32K KV + 0.35GiB runtime (GiB)")
    ax.set_title("32K context: ternary changes which phones fit")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_memory_fit.png", dpi=170)
    plt.close(fig)

    # 3. KV growth
    fig, ax = plt.subplots(figsize=(9, 5))
    for k, c in zip(order, colors):
        pts = [(4, M[k]["kv_gib"]["4096"]), (32, M[k]["kv_gib"]["32768"]),
               (128, M[k]["kv_gib"]["131072"]), (256, M[k]["kv_gib"]["262144"])]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o",
                label=k, color=c, linewidth=1.8)
    ax.set_xscale("log", base=2); ax.set_xlabel("context length (K tokens)")
    ax.set_ylabel("FP16 KV cache (GiB)")
    ax.set_title("KV grows linearly; 31B is not a phone model at 128K")
    ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_kv_context.png", dpi=170)
    plt.close(fig)

    # 4. tokenizer fertility (constants from experiments/gemma4_tokenizer.py)
    tok = {"gemma4": "Gemma 4", "gemma3": "Gemma 3", "qwen3.5": "Qwen3.5",
           "llama3.2": "Llama 3.2", "llmjp": "llm-jp"}
    agg = {"gemma4": 61.3, "gemma3": 61.3, "qwen3.5": 56.7, "llama3.2": 68.8, "llmjp": 48.4}
    role = {"gemma4": 67.1, "gemma3": 67.1, "qwen3.5": 58.9, "llama3.2": 69.9, "llmjp": 56.2}
    names_t = {"gemma4": 95.2, "gemma3": 95.2, "qwen3.5": 95.2, "llama3.2": 104.8, "llmjp": 66.7}
    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = np.arange(len(tok)); w = .26
    for i, (d, lab, c) in enumerate([(agg, "all samples", "#2563eb"),
                                    (role, "roleplay", "#059669"),
                                    (names_t, "names", "#f59e0b")]):
        vals = [d[k] for k in tok]
        ax.bar(x + (i - 1) * w, vals, w, label=lab, color=c)
    ax.set_xticks(x); ax.set_xticklabels([tok[k] for k in tok])
    ax.set_ylabel("tokens per 100 Japanese characters")
    ax.set_title("Gemma 4 uses the Gemma 3 tokenizer: Japanese is not its strongest axis")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_tokenizer.png", dpi=170)
    plt.close(fig)

    # 5. vendor latency
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    dev = ["S26 base", "S26 MTP free", "iPhone base"]
    e2b = [51.5, 66.5, 56.5]; e4b = [21.9, 36.7, 25.1]
    x = np.arange(3); w = .36
    ax = axes[0]
    ax.bar(x - w / 2, e2b, w, label="E2B", color="#059669")
    ax.bar(x + w / 2, e4b, w, label="E4B", color="#2563eb")
    for i, (a, b) in enumerate(zip(e2b, e4b)):
        ax.text(i - w / 2, a + .8, f"{a}", ha="center", fontsize=8)
        ax.text(i + w / 2, b + .8, f"{b}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(dev, fontsize=8); ax.set_ylabel("tok/s")
    ax.set_title("Free-form roleplay decode"); ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25)
    axes[1].bar(["E2B\nS26", "E2B\niPhone", "E4B\nS26", "E4B\niPhone"],
                [3808, 2878, 1293, 1189],
                color=["#059669", "#34d399", "#2563eb", "#60a5fa"])
    for i, v in enumerate([3808, 2878, 1293, 1189]):
        axes[1].text(i, v + 40, str(v), ha="center", fontsize=8)
    axes[1].set_ylabel("prefill tok/s"); axes[1].set_title("Prefill is compute-bound")
    axes[1].grid(axis="y", alpha=.25)
    fig.suptitle("LiteRT-LM on mobile: roleplay is free-form, so use the free-form numbers", fontsize=11)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_roleplay_latency.png", dpi=170)
    plt.close(fig)

    # 6. quality vs memory (32K, lean, ternary)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for k, c in zip(order, colors):
        xv = M[k]["total_ternary"]["32768"]["lean"]; yv = M[k]["mmlu"]
        ax.scatter(xv, yv, s=90, color=c, zorder=3)
        ax.annotate(k, (xv, yv), textcoords="offset points", xytext=(6, -12), fontsize=8)
    for xv, lab in [(3.5, "Android 8"), (5.5, "Android 12"), (6.0, "iPhone 6"), (7.5, "Android 16")]:
        ax.axvline(xv, color="#9ca3af", linestyle=":", linewidth=1)
        ax.text(xv + .05, 59.5, lab, rotation=90, fontsize=7, color="#6b7280")
    ax.set_xlabel("ternary weights + 32K FP16 KV + 0.35GiB runtime (GiB)")
    ax.set_ylabel("MMLU Pro (%)")
    ax.set_title("Quality vs mobile memory: E4B and 12B are the useful frontier")
    ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_quality_memory.png", dpi=170)
    plt.close(fig)

    # 7. component bpw
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    comps = ["token", "PLE", "attention", "MLP", "gates"]
    bpw = {
        "E2B": [2.04, 4.12, 3.78, 2.58, 8.04],
        "E4B": [2.02, 2.12, 3.68, 4.02, 8.03],
        "12B": [4.02, None, 4.01, 4.01, None],
    }
    x = np.arange(len(comps)); w = .26
    for i, (k, c) in enumerate([("E2B", "#059669"), ("E4B", "#2563eb"), ("12B", "#f59e0b")]):
        vals = [v if v is not None else 0 for v in bpw[k]]
        ax.bar(x + (i - 1) * w, vals, w, label=k, color=c)
        for xi, v in zip(x + (i - 1) * w, vals):
            if v:
                ax.text(xi, v + .12, f"{v:.1f}", ha="center", fontsize=7)
    ax.axhline(1.75, color="#dc2626", linestyle="--", linewidth=1.2)
    ax.text(4.35, 1.9, "ternary 1.75", color="#dc2626", fontsize=8, ha="right")
    ax.set_xticks(x); ax.set_xticklabels(comps)
    ax.set_ylabel("effective bits per weight")
    ax.set_title("Google's mobile QAT is already mixed: E2B MLP is 2.6 bpw, E4B MLP is 4.0 bpw")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25); ax.set_ylim(0, 9)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_qat_bpw.png", dpi=170)
    plt.close(fig)

    # 8. measured ternary weight error
    try:
        err = load("gemma4_ternary_error.json")
    except FileNotFoundError:
        err = {}
    if err:
        tensors = ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj",
                   "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"]
        short = ["q", "k", "v", "o", "gate", "up", "down"]
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        ax = axes[0]
        x = np.arange(len(tensors)); w = .26
        for i, (k, c) in enumerate([("E2B", "#059669"), ("E4B", "#2563eb"), ("12B", "#f59e0b")]):
            vals = [err[k]["by_tensor"].get(t, {}).get("ternary_rel", 0) * 100 for t in tensors]
            ax.bar(x + (i - 1) * w, vals, w, label=f"{k} ternary", color=c)
        ax.set_xticks(x); ax.set_xticklabels(short)
        ax.set_ylabel("relative Frobenius error (%)")
        ax.set_title("Per-channel ternary weight error (no QAT)")
        ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25)
        ax = axes[1]
        for k, c in zip(["E2B", "E4B", "12B"], ["#059669", "#2563eb", "#f59e0b"]):
            rows = [r for r in err[k]["rows"] if r["tensor"] == "mlp.down_proj"]
            ax.plot([r["layer"] for r in rows], [r["ternary_rel"] * 100 for r in rows],
                    marker="o", label=f"{k} down_proj", color=c)
        ax.set_xlabel("layer index"); ax.set_ylabel("ternary error (%)")
        ax.set_title("Layer dependence is model-specific")
        ax.set_ylim(45, 65)
        ax.text(0.02, 0.03, "axis zoomed: all values are 53-62%",
                transform=ax.transAxes, fontsize=7, color="#6b7280")
        ax.legend(fontsize=8); ax.grid(alpha=.25)
        fig.suptitle("Ternary is a training problem, not a rounding trick", fontsize=11)
        fig.tight_layout(); fig.savefig(outdir / "gemma4_ternary_error.png", dpi=170)
        plt.close(fig)

    # 9. runtime sensitivity at 32K
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    x = np.arange(len(order)); w = .26
    for i, (name, _) in enumerate(RUNTIMES):
        vals = [M[k]["total_ternary"]["32768"][name] for k in order]
        ax.bar(x + (i - 1) * w, vals, w, label=f"runtime +{RUNTIMES[i][1]:.2f}GiB",
               color=["#a7f3d0", "#34d399", "#059669"][i])
    for yv, lab, ls in [(3.5, "Android 8", ":"), (5.5, "Android 12", "--"),
                        (6.0, "iPhone 6", "-"), (7.5, "Android 16", "-.")]:
        ax.axhline(yv, color="#6b7280", linestyle=ls, linewidth=1)
        ax.text(len(order) - .45, yv + .08, lab, fontsize=7, ha="right", color="#374151")
    ax.set_xticks(x); ax.set_xticklabels([labels[k] for k in order])
    ax.set_ylabel("ternary total at 32K (GiB)")
    ax.set_title("Runtime overhead decides the last 1-1.5GiB")
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25)
    fig.tight_layout(); fig.savefig(outdir / "gemma4_runtime_sensitivity.png", dpi=170)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=EV / "gemma4_mobile_fit.json")
    ap.add_argument("--charts", type=Path, default=None)
    args = ap.parse_args()
    data = build()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {args.json}")
    if args.charts:
        charts(args.charts)
        print(f"wrote charts to {args.charts}")

    print(f"{'model':9s} {'ternW':>7s} {'qatW':>7s} {'T32':>7s} {'Q32':>7s} "
          f"{'T128':>7s} {'Q128':>7s}")
    for tag in MODELS:
        m = data["models"][tag]
        print(f"{tag:9s} {m['ternary_weights_gib']:7.2f} {m['qat_weights_gib']:7.2f} "
              f"{m['total_ternary']['32768']['lean']:7.2f} "
              f"{m['total_qat']['32768']['lean']:7.2f} "
              f"{m['total_ternary']['131072']['lean']:7.2f} "
              f"{m['total_qat']['131072']['lean']:7.2f}")


if __name__ == "__main__":
    main()
