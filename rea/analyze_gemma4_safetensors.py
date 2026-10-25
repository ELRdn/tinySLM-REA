#!/usr/bin/env python3
"""Inspect Gemma 4 safetensors headers and measure ternary weight error.

Two modes:

  header  Read the JSON header of one or more shards with HTTP Range, then
          aggregate parameters by component. No tensor bytes are downloaded.

  errors  Download selected 2-D tensors and compute per-channel ternary,
          INT4 and INT8 relative Frobenius error. This is a *weight-space*
          diagnostic, not a quality measurement.

Examples:
    python rea/analyze_gemma4_safetensors.py \
      --url https://huggingface.co/google/gemma-4-E2B-it/resolve/main/model.safetensors \
      --json rea/evidence/gemma4_safetensors_breakdown.json

    python rea/analyze_gemma4_safetensors.py --errors \
      --url https://huggingface.co/google/gemma-4-12B-it/resolve/main/model.safetensors \
      --layers 0,24 --json rea/evidence/gemma4_ternary_error.json

The safetensors format is: uint64 header length, JSON header, data section.
``data_offsets`` are relative to the start of the data section.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

UA = "tinySLM-REA/1.0"


def fetch(url: str, start: int, end: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def header(url: str) -> tuple[dict, int]:
    b = fetch(url, 0, 8 * 1024 * 1024 - 1)
    hl = struct.unpack("<Q", b[:8])[0]
    if 8 + hl > len(b):
        b = fetch(url, 0, 8 + hl - 1)
    return json.loads(b[8:8 + hl].decode("utf-8")), hl


def nbytes(dtype: str) -> int:
    return {"BF16": 2, "F16": 2, "F32": 4, "F64": 8, "I64": 8, "I32": 4,
            "I16": 2, "I8": 1, "U8": 1, "BOOL": 1, "U32": 4, "U16": 2}.get(dtype, 2)


def component(name: str) -> str:
    if name.startswith("model.audio_tower"): return "audio_tower"
    if name.startswith("model.vision_tower"): return "vision_tower"
    if name.startswith("model.vision_embedder"): return "vision_embedder"
    if name.startswith("model.embed_audio"): return "embed_audio"
    if name.startswith("model.embed_vision"): return "embed_vision"
    if name.startswith("model.language_model.embed_tokens_per_layer"): return "text_embed_per_layer"
    if name.startswith("model.language_model.embed_tokens"): return "text_embed_tokens"
    if name.startswith("model.language_model.per_layer_model_projection"): return "text_per_layer_proj"
    if name.startswith("model.language_model.per_layer_projection_norm"): return "text_per_layer_norm"
    if name.startswith("model.language_model.layers"):
        parts = name.split(".")
        rest = ".".join(parts[4:])
        if rest.startswith("self_attn"): return "text_attn"
        if rest.startswith("mlp"): return "text_mlp"
        if rest.startswith("experts"): return "text_moe_experts"
        if rest.startswith("router"): return "text_router"
        if rest.startswith("per_layer_input_gate"): return "text_per_layer_gate"
        if rest.startswith("per_layer_projection"): return "text_per_layer_proj_layer"
        if rest.startswith("post_per_layer_input_norm"): return "text_per_layer_norm_layer"
        return "text_layer_norm_scalar"
    if name.startswith("model.language_model.norm"): return "text_final_norm"
    if name.startswith("model.language_model"): return "text_other"
    if name.startswith("lm_head"): return "lm_head"
    return "other:" + name.split(".")[0]


def breakdown(urls: list[str]) -> dict:
    H = {}
    for u in urls:
        h, _ = header(u)
        H.update({k: v for k, v in h.items() if k != "__metadata__"})
    comp = defaultdict(lambda: {"params": 0, "bytes": 0, "tensors": 0})
    dtype = Counter()
    total = total_b = 0
    for name, v in H.items():
        p = math.prod(v["shape"]) if v["shape"] else 1
        b = p * nbytes(v["dtype"])
        total += p
        total_b += b
        dtype[v["dtype"]] += b
        c = component(name)
        comp[c]["params"] += p
        comp[c]["bytes"] += b
        comp[c]["tensors"] += 1
    text = sum(v["params"] for k, v in comp.items() if k.startswith("text_"))
    embed = sum(v["params"] for k, v in comp.items()
                if k in ("text_embed_tokens", "text_embed_per_layer",
                         "text_per_layer_proj", "text_per_layer_proj_layer"))
    linear = sum(v["params"] for k, v in comp.items()
                 if k in ("text_attn", "text_mlp", "text_moe_experts",
                          "text_per_layer_gate", "text_per_layer_proj_layer"))
    return {
        "total_params": total,
        "total_bytes": total_b,
        "text_params": text,
        "nontext_params": total - text,
        "embed_params": embed,
        "linear_params": linear,
        "dtype_bytes": dict(dtype),
        "components": {k: dict(v) for k, v in comp.items()},
    }


def to_float(b: bytes, dtype: str) -> np.ndarray:
    if dtype == "BF16":
        u16 = np.frombuffer(b, dtype="<u2")
        return (u16.astype(np.uint32) << 16).view(np.float32)
    if dtype == "F16":
        return np.frombuffer(b, dtype="<f2").astype(np.float32)
    if dtype == "F32":
        return np.frombuffer(b, dtype="<f4").astype(np.float32)
    raise SystemExit(f"unsupported dtype for error analysis: {dtype}")


def qerr(W: np.ndarray, mode: str) -> tuple[float, float, float]:
    if mode == "ternary":
        a = np.mean(np.abs(W), axis=1, keepdims=True) + 1e-12
        q = np.clip(np.rint(W / a), -1, 1)
    elif mode == "int4":
        a = (np.max(np.abs(W), axis=1, keepdims=True) + 1e-12) / 7.0
        q = np.clip(np.rint(W / a), -8, 7)
    elif mode == "int8":
        a = (np.max(np.abs(W), axis=1, keepdims=True) + 1e-12) / 127.0
        q = np.clip(np.rint(W / a), -128, 127)
    else:
        raise ValueError(mode)
    rec = q * a
    den = np.linalg.norm(W)
    rel = float(np.linalg.norm(W - rec) / den) if den else 0.0
    return rel, float(np.mean(a)), float(np.mean(q == 0))


def errors(url: str, layers: list[int], tensors: list[str]) -> dict:
    h, hl = header(url)
    base = 8 + hl
    rows = []
    for L in layers:
        for t in tensors:
            name = f"model.language_model.layers.{L}.{t}.weight"
            if name not in h:
                continue
            info = h[name]
            s, e = info["data_offsets"]
            b = fetch(url, base + s, base + e - 1)
            W = to_float(b, info["dtype"]).reshape(info["shape"]).astype(np.float32)
            te, _, tz = qerr(W, "ternary")
            q4, _, _ = qerr(W, "int4")
            q8, _, _ = qerr(W, "int8")
            rows.append({
                "layer": L, "tensor": t, "shape": info["shape"],
                "params": int(np.prod(info["shape"])),
                "ternary_rel": te, "int4_rel": q4, "int8_rel": q8,
                "ternary_zero_frac": tz,
                "std": float(np.std(W)), "absmean": float(np.mean(np.abs(W))),
                "maxabs": float(np.max(np.abs(W))),
            })
            print(f"L{L:<2d} {t:22s} tern={te:.4f} int4={q4:.4f} int8={q8:.4f}")
    by_tensor = {}
    for t in tensors:
        rr = [r for r in rows if r["tensor"] == t]
        if rr:
            by_tensor[t] = {k: float(np.mean([r[k] for r in rr]))
                            for k in ("ternary_rel", "int4_rel", "int8_rel",
                                      "ternary_zero_frac")}
    return {"rows": rows, "by_tensor": by_tensor}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", required=True,
                    help="safetensors URL; repeat for sharded models")
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--layers", default="0,17,34")
    ap.add_argument("--tensors", default="self_attn.q_proj,self_attn.k_proj,"
                                         "self_attn.v_proj,self_attn.o_proj,"
                                         "mlp.gate_proj,mlp.up_proj,mlp.down_proj")
    ap.add_argument("--json", type=Path, default=Path("gemma4_safetensors.json"))
    args = ap.parse_args()

    if args.errors:
        if len(args.url) != 1:
            raise SystemExit("--errors needs exactly one --url")
        layers = [int(x) for x in args.layers.split(",") if x]
        tensors = [x for x in args.tensors.split(",") if x]
        out = errors(args.url[0], layers, tensors)
        out["url"] = args.url[0]
    else:
        out = breakdown(args.url)
        out["urls"] = args.url
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.json}")
    if not args.errors:
        print("total params", f"{out['total_params']:,}",
              "linear", f"{out['linear_params']:,}",
              "embed", f"{out['embed_params']:,}")


if __name__ == "__main__":
    main()
