#!/usr/bin/env python3
"""GGUF anatomy + PTQ1_0 block decoder for the Bonsai 2B ternary model.

This is a read-only parser. It intentionally does not import llama.cpp or any
model framework: every number below comes from the shipped bytes plus the
GGUF v3 container layout. The PTQ1_0 block layout is cross-checked against the
PrismML fork's ggml-common.h / ggml-quants.c (see README.md).

Usage:
    python analyze_gguf.py <model.gguf> --json evidence/bonsai2b.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import struct
from pathlib import Path

GGUF_MAGIC = b"GGUF"
T_UINT8, T_INT8, T_UINT16, T_INT16, T_UINT32, T_INT32, T_FLOAT32, T_BOOL, T_STRING, T_ARRAY, T_UINT64, T_INT64, T_FLOAT64 = range(13)
FMT = {
    T_UINT8: "<B", T_INT8: "<b", T_UINT16: "<H", T_INT16: "<h",
    T_UINT32: "<I", T_INT32: "<i", T_FLOAT32: "<f", T_BOOL: "<?",
    T_UINT64: "<Q", T_INT64: "<q", T_FLOAT64: "<d",
}

# GGML type ids used by the file. Only the ids that occur are needed.
TYPE_NAMES = {
    0: "F32", 1: "F16", 2: "Q4_0", 3: "Q4_1", 6: "Q5_0", 7: "Q5_1",
    8: "Q8_0", 9: "Q8_1", 10: "Q2_K", 11: "Q3_K", 12: "Q4_K",
    13: "Q5_K", 14: "Q6_K", 15: "Q8_K", 16: "IQ2_XXS", 17: "IQ2_XS",
    18: "IQ3_XXS", 19: "IQ1_S", 20: "IQ4_NL", 21: "IQ3_S", 22: "IQ2_S",
    23: "IQ4_XS", 24: "I8", 25: "I16", 26: "I32", 27: "I64", 28: "F64",
    29: "IQ1_M", 30: "BF16", 34: "TQ1_0", 35: "TQ2_0", 36: "Q4_0_4_4",
    37: "Q4_0_4_8", 38: "Q4_0_8_8", 39: "TQ1_0", 40: "TQ2_0",
    41: "MXFP4", 42: "Q2_0", 43: "Q2_0", 142: "PQ2_0", 143: "PTQ1_0",
}
# block bytes / elements for the types in this file
BLOCK = {
    "F32": (4, 1), "F16": (2, 1), "BF16": (2, 1),
    "PTQ1_0": (28, 128), "PQ2_0": (34, 128), "Q2_0": (18, 64),
    "Q8_0": (34, 32), "TQ2_0": (66, 256), "TQ1_0": (56, 256),
}


class Reader:
    def __init__(self, f):
        self.f = f

    def read(self, n: int) -> bytes:
        b = self.f.read(n)
        if len(b) != n:
            raise EOFError(f"wanted {n} bytes, got {len(b)}")
        return b

    def u32(self) -> int:
        return struct.unpack("<I", self.read(4))[0]

    def u64(self) -> int:
        return struct.unpack("<Q", self.read(8))[0]

    def string(self) -> str:
        n = self.u64()
        return self.read(n).decode("utf-8", "replace")

    def value(self, t: int):
        if t == T_STRING:
            return self.string()
        if t == T_ARRAY:
            et = self.u32()
            n = self.u64()
            return [self.value(et) for _ in range(n)]
        return struct.unpack(FMT[t], self.read(struct.calcsize(FMT[t])))[0]


def read_header(path: str):
    with open(path, "rb") as f:
        r = Reader(f)
        magic = r.read(4)
        if magic != GGUF_MAGIC:
            raise ValueError(f"not GGUF: {magic!r}")
        version = r.u32()
        n_tensors = r.u64()
        n_kv = r.u64()
        kv = {}
        for _ in range(n_kv):
            k = r.string()
            t = r.u32()
            kv[k] = r.value(t)
        tensors = []
        for _ in range(n_tensors):
            name = r.string()
            nd = r.u32()
            dims = [r.u64() for _ in range(nd)]
            ttype = r.u32()
            off = r.u64()
            tensors.append({"name": name, "dims": dims, "type": ttype, "offset": off})
        alignment = int(kv.get("general.alignment", 32))
        pos = f.tell()
        data_start = (pos + alignment - 1) // alignment * alignment
    return {
        "version": version, "n_tensors": n_tensors, "n_kv": n_kv,
        "kv": kv, "tensors": tensors, "data_start": data_start,
        "alignment": alignment,
    }


def decode_ptq1_block(b: bytes, trit_order: str = "runtime"):
    """Decode one 28-byte block.

    Layout (PrismML fork, ggml-common.h):
        uint8 qs[24]  // 5 base-3 trits per byte, 120 values
        uint8 qh[2]   // 4 base-3 trits per byte, 8 values
        fp16  d       // one scale per 128 weights

    The encoder rescales each base-3 code q (0..242) to a byte with
    ceil(q*256/243), and the decoder uses (byte*3^n mod 256)*3>>8.
    This function reproduces that exact integer path.
    """
    if len(b) != 28:
        raise ValueError("PTQ1_0 block must be 28 bytes")
    qs, qh = b[:24], b[24:26]
    d = struct.unpack("<e", b[26:28])[0]
    pow3 = (1, 3, 9, 27, 81, 243)
    out = []
    j = 0
    for c in (32, 16, 8):
        while j + c <= 24:
            for n in range(5):
                for m in range(c):
                    q = (qs[j + m] * pow3[n]) & 0xFF
                    xi = ((q * 3) >> 8)
                    out.append(xi - 1)
            j += c
    for n in range(4):
        for h in range(2):
            q = (qh[h] * pow3[n]) & 0xFF
            xi = ((q * 3) >> 8)
            out.append(xi - 1)
    if len(out) != 128:
        raise AssertionError(len(out))
    return d, out


def analyze(path: str, block_samples: int = 2000):
    h = read_header(path)
    kv = h["kv"]
    tensors = h["tensors"]
    total_params = 0
    total_bytes = 0
    by_type = collections.Counter()
    by_type_params = collections.Counter()
    tensor_rows = []
    for t in tensors:
        n = math.prod(t["dims"]) if t["dims"] else 1
        name = TYPE_NAMES.get(t["type"], str(t["type"]))
        total_params += n
        bs, be = BLOCK[name]
        nb = math.ceil(n / be) * bs
        total_bytes += nb
        by_type[name] += nb
        by_type_params[name] += n
        tensor_rows.append({
            "name": t["name"], "dims": t["dims"], "type": name,
            "params": n, "bytes": nb, "offset": t["offset"],
        })

    emb = next((x for x in tensor_rows if x["name"] == "token_embd.weight"), None)
    emb_params = emb["params"] if emb else 0

    # PTQ1_0 block samples from token embedding
    block_stats = None
    if emb and emb["type"] == "PTQ1_0":
        base = h["data_start"] + emb["offset"]
        with open(path, "rb") as f:
            f.seek(base)
            data = f.read(28 * block_samples)
        trits = collections.Counter()
        scales = []
        qs_high = 0
        first = None
        for i in range(block_samples):
            b = data[i * 28:(i + 1) * 28]
            d, tr = decode_ptq1_block(b)
            if first is None:
                first = {"hex": b.hex(), "scale": d,
                         "first_32_weights": [round(d * x, 8) for x in tr[:32]],
                         "trit_counts": dict(collections.Counter(tr))}
            trits.update(tr)
            scales.append(d)
            qs_high = max(qs_high, max(b[:24]))
        block_stats = {
            "sample_blocks": block_samples,
            "block_bytes": 28,
            "weights_per_block": 128,
            "bits_per_weight": 1.75,
            "first_block": first,
            "qs_max": qs_high,
            "scale_min": min(scales),
            "scale_max": max(scales),
            "trit_counts": dict(trits),
            "trit_fraction": {str(k): v / (128 * block_samples) for k, v in sorted(trits.items())},
        }

    # KV-cache estimate for the hybrid layout. Only full-attention layers keep
    # a growing K/V cache; linear-attention layers keep a fixed-size state.
    layers = int(kv.get("qwen35.block_count", 0))
    interval = int(kv.get("qwen35.full_attention_interval", 0)) or 1
    kv_heads = int(kv.get("qwen35.attention.head_count_kv", 0))
    key_len = int(kv.get("qwen35.attention.key_length", 0))
    val_len = int(kv.get("qwen35.attention.value_length", 0))
    ctx = int(kv.get("qwen35.context_length", 0))
    full_layers = layers // interval if layers and interval else 0
    kv_bytes_fp16_full = 2 * full_layers * kv_heads * (key_len + val_len) * ctx * 2
    kv_bytes_fp16_all = 2 * layers * kv_heads * (key_len + val_len) * ctx * 2
    kv_cache = {
        "context": ctx, "layers": layers, "full_attention_layers": full_layers,
        "linear_attention_layers": layers - full_layers,
        "kv_heads": kv_heads, "key_length": key_len, "value_length": val_len,
        "fp16_bytes_if_all_layers_full": kv_bytes_fp16_all,
        "fp16_bytes_with_hybrid": kv_bytes_fp16_full,
        "fp16_gib_with_hybrid": kv_bytes_fp16_full / 2**30,
        "note": "one sequence; K and V; 2 bytes/element; ignores allocator overhead and SSM state",
    }

    meta = {}
    for k, v in kv.items():
        if isinstance(v, list):
            meta[k] = {"kind": "list", "length": len(v), "preview": v[:4]}
        elif isinstance(v, str) and len(v) > 300:
            meta[k] = {"kind": "string", "length": len(v), "sha256": hashlib.sha256(v.encode()).hexdigest(),
                       "preview": v[:200]}
        else:
            meta[k] = v

    out = {
        "file": {"path": os.path.abspath(path), "bytes": os.path.getsize(path),
                 "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()},
        "gguf": {"version": h["version"], "tensor_count": h["n_tensors"],
                 "kv_count": h["n_kv"], "data_start": h["data_start"],
                 "alignment": h["alignment"]},
        "architecture": kv.get("general.architecture"),
        "name": kv.get("general.name"),
        "metadata": meta,
        "summary": {
            "total_params": total_params,
            "theoretical_tensor_bytes": total_bytes,
            "file_bytes": os.path.getsize(path),
            "bits_per_param_tensor_only": total_bytes * 8 / total_params,
            "bits_per_param_file": os.path.getsize(path) * 8 / total_params,
            "by_type_bytes": dict(by_type),
            "by_type_params": dict(by_type_params),
            "embedding_params": emb_params,
            "embedding_share": emb_params / total_params if total_params else None,
            "non_embedding_params": total_params - emb_params,
        },
        "tensors": tensor_rows,
        "ptq1_block": block_stats,
        "kv_cache": kv_cache,
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--json", default=None)
    ap.add_argument("--blocks", type=int, default=2000)
    args = ap.parse_args()
    out = analyze(args.model, args.blocks)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")
    print(json.dumps({k: out[k] for k in ("name", "architecture", "summary", "kv_cache")},
                     ensure_ascii=False, indent=2))
    if out["ptq1_block"]:
        b = out["ptq1_block"]
        print(json.dumps({"ptq1_block": {k: b[k] for k in
              ("block_bytes", "weights_per_block", "bits_per_weight", "qs_max",
               "scale_min", "scale_max", "trit_counts")}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
