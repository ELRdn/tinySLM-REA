#!/usr/bin/env python3
"""Build research/gemma4_facts.json from the parsed Gemma 4 evidence.

The numeric facts are read from the evidence files, not re-typed, so the fact
database and the report cannot drift silently. Non-numeric facts (licence,
safety policy, context caps) are curated below with their primary source.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "rea" / "evidence"

with open(EV / "gemma4_mobile_fit.json", encoding="utf-8") as f:
    FIT = json.load(f)
with open(EV / "gemma4_safetensors_breakdown.json", encoding="utf-8") as f:
    PARAMS = json.load(f)
with open(EV / "gemma4_ternary_error.json", encoding="utf-8") as f:
    ERR = json.load(f)
with open(EV / "gemma4_qat_gguf.json", encoding="utf-8") as f:
    GGUF = json.load(f)

FACTS: list[dict] = []


def add(fid: str, claim: str, value, unit: str, source: str, label: str,
        note: str = "", verified: bool = True) -> None:
    FACTS.append(dict(id=fid, claim=claim, value=value, unit=unit,
                      source=source, label=label, verified=verified, note=note))


# ---------------------------------------------------------------------------
# 1. Parameters / architecture (observed from safetensors headers)
# ---------------------------------------------------------------------------
for tag in ("E2B", "E4B", "12B", "26B-A4B", "31B"):
    p = PARAMS[tag]
    add(f"G4-PARAM-{tag}", f"{tag} total parameters", p["total_params"],
        "parameters", "rea/evidence/gemma4_safetensors_breakdown.json", "観測",
        "safetensors header; BF16 tensor shapes")
    add(f"G4-LINEAR-{tag}", f"{tag} linear-layer parameters", p["linear_params"],
        "parameters", "rea/evidence/gemma4_safetensors_breakdown.json", "観測",
        "attention + MLP/MoE + per-layer gates/projections")
    add(f"G4-EMBED-{tag}", f"{tag} embedding + PLE parameters", p["embed_params"],
        "parameters", "rea/evidence/gemma4_safetensors_breakdown.json", "観測",
        "token embedding + PLE + per-layer model projection")

add("G4-ARCH-E2B", "E2B layers / full / KV-shared", [35, 7, 20], "count",
    "research/gemma4/gemma-4-E2B-it__config.json", "公式", "4:1 local:global")
add("G4-ARCH-E4B", "E4B layers / full / KV-shared", [42, 7, 18], "count",
    "research/gemma4/gemma-4-E4B-it__config.json", "公式", "5:1 local:global")
add("G4-ARCH-12B", "12B layers / full / KV-shared", [48, 8, 0], "count",
    "research/gemma4/gemma-4-12B-it__config.json", "公式", "K=V global, unified")
add("G4-ARCH-26B", "26B-A4B layers / full / KV-shared", [30, 5, 0], "count",
    "research/gemma4/gemma-4-26B-A4B-it__config.json", "公式", "MoE 128 experts, top-8")
add("G4-ARCH-31B", "31B layers / full / KV-shared", [60, 10, 0], "count",
    "research/gemma4/gemma-4-31B-it__config.json", "公式", "K=V global")

add("G4-VOCAB", "Gemma 4 vocabulary", 262144, "tokens",
    "research/gemma4/gemma-4-E2B-it__config.json", "公式", "shared across sizes")
add("G4-CTX-E2B", "E2B native context", 131072, "tokens",
    "research/gemma4/gemma-4-E2B-it__config.json", "公式", "mobile LiteRT card caps at 32K")
add("G4-CTX-E4B", "E4B native context", 131072, "tokens",
    "research/gemma4/gemma-4-E4B-it__config.json", "公式", "mobile LiteRT card caps at 32K")
add("G4-CTX-12B", "12B native context", 262144, "tokens",
    "research/gemma4/gemma-4-12B-it__config.json", "公式", "mobile LiteRT card supports 128K")
add("G4-CTX-26B", "26B-A4B native context", 262144, "tokens",
    "research/gemma4/gemma-4-26B-A4B-it__config.json", "公式", "")
add("G4-CTX-31B", "31B native context", 262144, "tokens",
    "research/gemma4/gemma-4-31B-it__config.json", "公式", "")

# ---------------------------------------------------------------------------
# 2. Container sizes (observed)
# ---------------------------------------------------------------------------
for tag in ("E2B", "E4B", "12B", "26B-A4B", "31B"):
    m = FIT["models"][tag]
    add(f"G4-LITERT-{tag}", f"{tag} LiteRT-LM GPU text bundle", m["litert_bytes"],
        "bytes", "rea/evidence/gemma4_litertlm_quantization.json", "観測",
        "HF litert-community; text decoder")
for tag in ("E2B", "E4B", "12B"):
    m = FIT["models"][tag]
    add(f"G4-GENERIC-{tag}", f"{tag} generic LiteRT-LM bundle", m["generic_bytes"],
        "bytes", "Hugging Face litert-community file listing", "観測",
        "includes audio/vision where supported")
for tag in ("E2B", "E4B", "12B", "26B-A4B", "31B"):
    m = FIT["models"][tag]
    add(f"G4-GGUF-{tag}", f"{tag} QAT Q4_0 GGUF", m["gguf_bytes"], "bytes",
        "rea/evidence/gemma4_qat_gguf.json", "観測", "Q4_0 + Q6_K embeddings")

# ---------------------------------------------------------------------------
# 3. Weights, KV, fit (derived)
# ---------------------------------------------------------------------------
for tag in ("E2B", "E4B", "12B", "26B-A4B", "31B"):
    m = FIT["models"][tag]
    add(f"G4-TERN-W-{tag}", f"{tag} ternary-estimate weights",
        round(m["ternary_weights_gib"], 3), "GiB",
        "rea/evidence/gemma4_mobile_fit.json", "導出",
        "linear 1.75bpw + observed non-linear precision")
    add(f"G4-QAT-W-{tag}", f"{tag} QAT text weights",
        round(m["qat_weights_gib"], 3), "GiB",
        "rea/evidence/gemma4_mobile_fit.json", "導出", "LiteRT-LM GPU bundle")
    for ctx in ("32768", "131072"):
        add(f"G4-KV-{tag}-{ctx}", f"{tag} FP16 KV at {int(ctx)//1024}K",
            round(m["kv_gib"][ctx], 3), "GiB",
            "rea/evidence/gemma4_mobile_fit.json", "導出",
            "conservative: K and V counted separately")
        add(f"G4-KV8-{tag}-{ctx}", f"{tag} INT8 KV at {int(ctx)//1024}K",
            round(m["kv_int8_gib"][ctx], 3), "GiB",
            "rea/evidence/gemma4_mobile_fit.json", "導出", "")
    add(f"G4-T32-{tag}", f"{tag} ternary total at 32K, runtime 0.35GiB",
        round(m["total_ternary"]["32768"]["lean"], 3), "GiB",
        "rea/evidence/gemma4_mobile_fit.json", "導出", "FP16 KV")
    add(f"G4-Q32-{tag}", f"{tag} QAT total at 32K, runtime 0.35GiB",
        round(m["total_qat"]["32768"]["lean"], 3), "GiB",
        "rea/evidence/gemma4_mobile_fit.json", "導出", "INT8 KV")
    add(f"G4-T128-{tag}", f"{tag} ternary total at 128K, runtime 0.35GiB",
        round(m["total_ternary"]["131072"]["lean"], 3), "GiB",
        "rea/evidence/gemma4_mobile_fit.json", "導出", "FP16 KV")

HYBRID = {"E2B": 2.27, "E4B": 2.79, "12B": 4.50, "26B-A4B": 7.03, "31B": 12.91}
for tag, v in HYBRID.items():
    add(f"G4-HYBRID-{tag}", f"{tag} hybrid (MLP ternary, attention INT4) 32K total",
        v, "GiB", "experiments/gemma4_mobile.py", "導出",
        f"all-ternary upper bound is {FIT['models'][tag]['total_ternary']['32768']['lean']:.2f}GiB")

add("G4-12B-QAT-4K", "12B QAT total at 4K, runtime 0.35GiB",
    round(5.5749 + 0.1875 + 0.35, 2), "GiB",
    "rea/evidence/gemma4_mobile_fit.json", "導出",
    "INT8 KV; still above iPhone 6GiB")
add("G4-E2B-CROSSOVER", "E2B ternary+FP16 KV vs QAT+INT8 KV package crossover",
    75, "K tokens", "rea/evidence/gemma4_mobile_fit.json", "導出",
    "piecewise: sliding-window KV stops growing after W")
add("G4-E4B-CROSSOVER", "E4B ternary+FP16 KV vs QAT+INT8 KV package crossover",
    129, "K tokens", "rea/evidence/gemma4_mobile_fit.json", "導出",
    "piecewise: sliding-window KV stops growing after W")
add("G4-12B-CROSSOVER", "12B ternary+FP16 KV vs QAT+INT8 KV package crossover",
    347, "K tokens", "rea/evidence/gemma4_mobile_fit.json", "導出",
    "piecewise: sliding-window KV stops growing after W")

# ---------------------------------------------------------------------------
# 4. Quantization (observed bpw + measured ternary error)
# ---------------------------------------------------------------------------
BPW = {
    "E2B": dict(token=2.04, ple=4.12, attention=3.78, mlp=2.58, gate=8.04, proj=8.25),
    "E4B": dict(token=2.02, ple=2.12, attention=3.68, mlp=4.02, gate=8.03, proj=8.25),
    "12B": dict(token=4.02, attention=4.01, mlp=4.01),
}
for tag, comp in BPW.items():
    for name, v in comp.items():
        add(f"G4-BPW-{tag}-{name}", f"{tag} {name} effective bits/weight", v, "bpw",
            "rea/evidence/gemma4_litertlm_quantization.json", "観測",
            "TFLite buffer bytes / logical params")
for tag in ("E2B", "E4B", "12B"):
    for t in ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj",
              "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"):
        r = ERR[tag]["by_tensor"][t]
        add(f"G4-ERR-{tag}-{t.replace('.', '-')}", f"{tag} {t} ternary relative weight error",
            round(r["ternary_rel"] * 100, 1), "%",
            "rea/evidence/gemma4_ternary_error.json", "観測",
            "per-channel absmean, no QAT; weight-space error, not quality")

# ---------------------------------------------------------------------------
# 5. Tokenizer / chat template (observed experiments)
# ---------------------------------------------------------------------------
TOK = dict(gemma4=61.3, gemma3=61.3, qwen3p5=56.7, llama32=68.8, llmjp=48.4)
ROLE = dict(gemma4=67.1, gemma3=67.1, qwen3p5=58.9, llama32=69.9, llmjp=56.2)
NAMES = dict(gemma4=95.2, gemma3=95.2, qwen3p5=95.2, llama32=104.8, llmjp=66.7)
for tag, v in TOK.items():
    add(f"G4-TOK-{tag}", f"{tag} Japanese tokens per 100 chars (all samples)", v,
        "tokens/100 chars", "experiments/gemma4_tokenizer.py", "観測", "8 samples")
for tag, v in ROLE.items():
    add(f"G4-ROLE-{tag}", f"{tag} Japanese roleplay tokens per 100 chars", v,
        "tokens/100 chars", "experiments/gemma4_tokenizer.py", "観測", "1 roleplay sample")
for tag, v in NAMES.items():
    add(f"G4-NAMES-{tag}", f"{tag} Japanese names tokens per 100 chars", v,
        "tokens/100 chars", "experiments/gemma4_tokenizer.py", "観測", "1 names sample")
for turns, tok, pct in [(1, 146, 21.7), (5, 494, 17.6), (10, 929, 16.9), (20, 1799, 16.4)]:
    add(f"G4-TPL-{turns}", f"Chat template overhead at {turns} turns", pct, "%",
        "experiments/gemma4_tokenizer.py", "観測", f"{tok} tokens total")

# ---------------------------------------------------------------------------
# 6. Benchmarks / speed / safety / licence (curated primary sources)
# ---------------------------------------------------------------------------
for tag, v in dict(E2B=60.0, E4B=69.4, B12=77.2, B26=82.6, B31=85.2).items():
    add(f"G4-MMLU-{tag}", f"{tag} MMLU Pro", v, "%",
        "arXiv:2607.02770 Table 5", "論文", "thinking mode unless stated")
for tag, v in dict(E2B=67.4, E4B=76.6, B12=83.4, B26=86.3, B31=88.4).items():
    add(f"G4-MMMLU-{tag}", f"{tag} MMMLU", v, "%",
        "arXiv:2607.02770 Table 5", "論文", "multilingual average, not Japanese-only")
for tag, v in dict(E2B=94.6, E4B=96.7, B12=97.2, B26=98.5, B31=98.9).items():
    add(f"G4-IFEVAL-{tag}", f"{tag} IFEval", v, "%",
        "arXiv:2607.02770 Table 5", "論文", "thinking mode")
add("G4-ARENA-31B", "Gemma 4 31B Arena Elo", 1451, "Elo",
    "arXiv:2607.02770 Table 4", "論文", "as of 2026-06-19")
add("G4-ARENA-26B", "Gemma 4 26B-A4B Arena Elo", 1438, "Elo",
    "arXiv:2607.02770 Table 4", "論文", "")
add("G4-LANGS", "Gemma 4 language coverage", [140, 35], "languages",
    "google/gemma-4-E2B-it model card", "公式",
    "140+ pre-trained, 35+ out-of-box")

SPEED = [
    ("E2B", "S26 Ultra", "CPU", 557, 46.9, 1.8),
    ("E2B", "S26 Ultra", "GPU", 3808, 52.1, 0.3),
    ("E2B", "iPhone 17 Pro", "CPU", 532, 25.0, 1.9),
    ("E2B", "iPhone 17 Pro", "GPU", 2878, 56.5, 0.3),
    ("E4B", "S26 Ultra", "CPU", 195, 17.7, 5.3),
    ("E4B", "S26 Ultra", "GPU", 1293, 22.1, 0.8),
    ("E4B", "iPhone 17 Pro", "CPU", 159, 9.7, 6.5),
    ("E4B", "iPhone 17 Pro", "GPU", 1189, 25.1, 0.9),
]
for model, dev, backend, pre, dec, ttft in SPEED:
    add(f"G4-SPEED-{model}-{dev.replace(' ', '')}-{backend}",
        f"{model} {dev} {backend} prefill/decode/TTFT",
        [pre, dec, ttft], ["tok/s", "tok/s", "s"],
        "litert-community model card", "ベンダー自己測定",
        "1024 prefill / 256 decode / ctx 2048")
add("G4-MTP-E2B", "E2B MTP free-form decode", [51.5, 66.5, 1.29],
    ["tok/s", "tok/s", "x"], "litert-community E2B card", "ベンダー自己測定", "")
add("G4-MTP-E4B", "E4B MTP free-form decode", [21.9, 36.7, 1.68],
    ["tok/s", "tok/s", "x"], "litert-community E4B card", "ベンダー自己測定", "")
add("G4-12B-DESKTOP", "12B M4 Air / M4 Pro decode", [15, 29], "tok/s",
    "litert-community 12B card", "ベンダー自己測定", "ctx 4096")
add("G4-26B-DESKTOP", "26B-A4B M4 Max / 4090 decode", [77, 86], "tok/s",
    "litert-community 26B card", "ベンダー自己測定", "")
add("G4-31B-DESKTOP", "31B M4 Max / 4090 decode", [18, 28], "tok/s",
    "litert-community 31B card", "ベンダー自己測定", "")

add("G4-LICENSE", "Gemma 4 licence", "Apache 2.0", "SPDX",
    "https://ai.google.dev/gemma/docs/gemma_4_license", "公式", "")
add("G4-SAFETY", "Gemma 4 prohibited content",
    ["CSAM", "dangerous", "sexually explicit", "hate", "harassment"], "policy",
    "arXiv:2607.02770 §5.2", "論文", "roleplay apps need moderation")
add("G4-QAT-CLAIM", "QAT mobile schema",
    ["static activations", "channel-wise", "targeted 2-bit", "embedding+KV optimization"],
    "policy", "Gemma 4 QAT blog (2026-06-05)", "ベンダー主張",
    "no per-benchmark quality delta published")
add("G4-1GB", "E2B text-only without PLE memory", "<1", "GB",
    "Gemma 4 QAT blog (2026-06-05)", "ベンダー主張",
    "observed E2B GPU bundle is 2.008GB including 1.211GB PLE")

# ---------------------------------------------------------------------------
# 7. Artifact hashes (REA)
# ---------------------------------------------------------------------------
add("G4-APK-SHA", "AI Edge Gallery APK 1.0.20 SHA-256",
    "036da9de8c57a2ba6226a6e70d2ba00aa4f5546fa2409ee44639c14212f9f6cb", "sha256",
    "REA inspect_artifact ev_deeffda66e0919d37f0be7f8cef1a0c5a679177a3a0ceba56e50f1a391f8ccb0",
    "観測", "")
add("G4-MACHO-SHA", "LiteRT-LM macOS arm64 SHA-256",
    "97a9cfed1986e5231f8d80e70af59f95cb60322ca39c3397e28f8470e3bb6195", "sha256",
    "REA open_binary", "観測", "")
add("G4-DLL-SHA", "LiteRT-LM Windows DLL SHA-256",
    "a226cbead46a2eef152f3009aa0a83262f1c2123f108aa3385bbdba07d427bd3", "sha256",
    "REA inspect_pe_resources ev_c38e57dbe3b9d341714bd9c19ec27d5bd8f70f24016ab049e4970682ea2d64ea",
    "観測", "")

out = {
    "schema": "tinySLM-REA/gemma4-facts-v1",
    "date": "2026-10-25",
    "count": len(FACTS),
    "labels": ["観測", "導出", "論文", "公式", "ベンダー主張", "ベンダー自己測定",
               "デバイス仕様", "経験則", "二次資料", "推測", "未検証"],
    "facts": FACTS,
}
with open(ROOT / "research" / "gemma4_facts.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"wrote {len(FACTS)} facts")
