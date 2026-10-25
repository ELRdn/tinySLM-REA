#!/usr/bin/env python3
"""Parse a LiteRT-LM ``.litertlm`` bundle without executing it.

The bundle is a FlatBuffer header followed by sections:

  LITERTLM | version (3 x uint32) | header_end (uint64) | FlatBuffer header
  section 0: LlmMetadataProto
  section 1: tokenizer
  section 2: TFLite model (``TFL3``)

This parser reads only the header (first 8 MiB) and, with ``--tflite``, the
first ``--max-bytes`` of the TFLite section. It never downloads the weights.

Usage:
    python rea/analyze_litertlm.py --url https://.../gemma-4-E2B-it-gpu.litertlm \
        --tflite --json rea/evidence/gemma4_litertlm_header.json
    python rea/analyze_litertlm.py --path model.litertlm --json header.json

Schema sources:
  github.com/google-ai-edge/LiteRT-LM/schema/core/litertlm_header_schema.fbs
  github.com/google-ai-edge/LiteRT/schema (TFLite Model/Tensor/SubGraph)
"""
from __future__ import annotations

import argparse
import json
import struct
import urllib.request
from pathlib import Path


class Reader:
    def __init__(self, path: str | None, url: str | None):
        self.path = Path(path) if path else None
        self.url = url
        if not self.path and not self.url:
            raise SystemExit("give --path or --url")

    def read(self, start: int, end: int) -> bytes:
        n = end - start + 1
        if self.path:
            with open(self.path, "rb") as f:
                f.seek(start)
                return f.read(n)
        req = urllib.request.Request(
            self.url,
            headers={"User-Agent": "tinySLM-REA/1.0", "Range": f"bytes={start}-{end}"},
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()


def u8(B, p): return B[p]
def u16(B, p): return struct.unpack("<H", B[p:p + 2])[0]
def i16(B, p): return struct.unpack("<h", B[p:p + 2])[0]
def u32(B, p): return struct.unpack("<I", B[p:p + 4])[0]
def i32(B, p): return struct.unpack("<i", B[p:p + 4])[0]
def u64(B, p): return struct.unpack("<Q", B[p:p + 8])[0]


def table(B, p):
    vt = p - i32(B, p)
    vs = u16(B, vt)
    os_ = u16(B, vt + 2)
    n = (vs - 4) // 2
    return {"p": p, "vt": vt, "vs": vs, "os": os_,
            "fs": [u16(B, vt + 4 + 2 * i) for i in range(n)]}


def fld(t, i):
    return t["p"] + t["fs"][i] if i < len(t["fs"]) and t["fs"][i] else None


def ind(B, p): return p + u32(B, p)


def vfield(B, t, i):
    p = fld(t, i)
    if p is None:
        return [], 0
    q = ind(B, p)
    n = u32(B, q)
    return [q + 4 + 4 * j for j in range(n)], n


def string(B, p):
    q = ind(B, p)
    n = u32(B, q)
    return B[q + 4:q + 4 + n].decode("utf-8", "replace")


def value(B, vt, p):
    tt = table(B, ind(B, p))
    f = fld(tt, 0)
    if f is None:
        return None
    return {
        1: lambda: u8(B, f),
        2: lambda: struct.unpack("<b", B[f:f + 1])[0],
        3: lambda: u16(B, f),
        4: lambda: i16(B, f),
        5: lambda: u32(B, f),
        6: lambda: i32(B, f),
        7: lambda: struct.unpack("<f", B[f:f + 4])[0],
        8: lambda: bool(u8(B, f)),
        9: lambda: string(B, f),
        10: lambda: u64(B, f),
        11: lambda: struct.unpack("<q", B[f:f + 8])[0],
        12: lambda: struct.unpack("<d", B[f:f + 8])[0],
    }.get(vt, lambda: None)()


def parse_header(reader: Reader) -> dict:
    b = reader.read(0, 8 * 1024 * 1024 - 1)
    if b[:8] != b"LITERTLM":
        raise SystemExit("not a LITERTLM bundle")
    major, minor, patch = struct.unpack("<III", b[8:20])
    hdr_end = u64(b, 24)
    if hdr_end > len(b):
        raise SystemExit(f"header_end {hdr_end} exceeds {len(b)}")
    B = b[32:hdr_end]
    root = table(B, u32(B, 0))
    sys_ = table(B, ind(B, fld(root, 0)))
    sec_ = table(B, ind(B, fld(root, 1)))

    system = {}
    for ep in vfield(B, sys_, 0)[0]:
        kv = table(B, ep + u32(B, ep))
        k = string(B, fld(kv, 0))
        vt = u8(B, fld(kv, 1))
        system[k] = value(B, vt, fld(kv, 2))

    sections = []
    for ep in vfield(B, sec_, 0)[0]:
        so = table(B, ep + u32(B, ep))
        items = {}
        for e in vfield(B, so, 0)[0]:
            kv = table(B, e + u32(B, e))
            k = string(B, fld(kv, 0))
            vt = u8(B, fld(kv, 1))
            items[k] = value(B, vt, fld(kv, 2))
        sections.append({
            "begin": u64(B, fld(so, 1)),
            "end": u64(B, fld(so, 2)),
            "type": u8(B, fld(so, 3)),
            "items": items,
        })
    return {
        "magic": "LITERTLM",
        "version": [major, minor, patch],
        "header_end": hdr_end,
        "system": system,
        "sections": sections,
    }


TYPES = {0: "F32", 1: "F16", 2: "I32", 3: "U8", 4: "I64", 5: "STR", 6: "BOOL",
         7: "I16", 8: "C64", 9: "I8", 10: "F64", 11: "C128", 12: "U64",
         13: "RES", 14: "VAR", 15: "U32", 16: "U16", 17: "I4", 18: "BF16",
         19: "I2", 20: "U4", 21: "F8E4M3", 22: "F8E5M2"}


def parse_tflite(reader: Reader, start: int, section_end: int, max_bytes: int) -> dict:
    end = min(section_end - 1, start + max_bytes - 1)
    b = reader.read(start, end)
    if b[4:8] != b"TFL3":
        raise SystemExit("TFLite section does not start with TFL3")
    m = table(b, u32(b, 0))

    bvec, nb = vfield(b, m, 4)
    bufs = []
    for bp in bvec:
        bt = table(b, bp + u32(b, bp))
        data = fld(bt, 0)
        size = fld(bt, 2)
        if data is not None:
            q = ind(b, data)
            bufs.append(u32(b, q))
        elif size is not None:
            bufs.append(u64(b, size))
        else:
            bufs.append(0)

    sv = ind(b, fld(m, 2))
    st = table(b, sv + 4 + u32(b, sv + 4))
    tvec, nt = vfield(b, st, 0)
    comp = {}
    names = []
    for tp in tvec:
        tt = table(b, tp + u32(b, tp))
        name = string(b, fld(tt, 3)) if fld(tt, 3) is not None else ""
        buf = u32(b, fld(tt, 2)) if fld(tt, 2) is not None else 0
        typ = u8(b, fld(tt, 1)) if fld(tt, 1) is not None else 0
        by = bufs[buf] if buf < len(bufs) else 0
        if name.startswith("transformer.embedder.input_embedding"):
            c = "input_embedding"
        elif name.startswith("transformer.embedder.per_layer_model_projection"):
            c = "per_layer_model_projection"
        elif ".per_layer_embeddings." in name:
            c = "per_layer_embeddings"
        elif ".per_layer_embedding_gate." in name:
            c = "per_layer_gate"
        elif ".per_layer_embedding_projection." in name:
            c = "per_layer_projection"
        elif ".attn." in name:
            c = "attention"
        elif ".mlp." in name:
            c = "mlp"
        elif "norm" in name or name.endswith(".scale"):
            c = "norm"
        else:
            c = "other"
        rec = comp.setdefault(c, {"bytes": 0, "tensors": 0, "types": {}})
        rec["bytes"] += by
        rec["tensors"] += 1
        rec["types"][TYPES.get(typ, str(typ))] = rec["types"].get(TYPES.get(typ, str(typ)), 0) + 1
        if len(names) < 40 and name:
            names.append(name)
    return {
        "tflite_start": start,
        "tflite_end": section_end,
        "sampled_bytes": len(b),
        "buffers": nb,
        "buffer_bytes": sum(bufs),
        "tensors": nt,
        "components": comp,
        "names_sample": names,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--path")
    g.add_argument("--url")
    ap.add_argument("--tflite", action="store_true")
    ap.add_argument("--max-bytes", type=int, default=192 * 1024 * 1024)
    ap.add_argument("--json", type=Path, default=Path("litertlm_header.json"))
    args = ap.parse_args()

    reader = Reader(args.path, args.url)
    out = {"source": args.path or args.url, "header": parse_header(reader)}
    if args.tflite:
        tfl = [s for s in out["header"]["sections"] if s["type"] == 3]
        if not tfl:
            raise SystemExit("no TFLite section")
        s = tfl[-1]
        out["tflite"] = parse_tflite(reader, s["begin"], s["end"], args.max_bytes)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    h = out["header"]
    print(f"{h['magic']} v{'.'.join(map(str, h['version']))} sections={len(h['sections'])}")
    for s in h["sections"]:
        print(f"  type={s['type']} {s['begin']}..{s['end']} items={s['items']}")
    if args.tflite:
        t = out["tflite"]
        print(f"TFLite tensors={t['tensors']} buffers={t['buffers']} bytes={t['buffer_bytes']}")
        for k, v in t["components"].items():
            print(f"  {k:28s} {v['bytes']/1e6:9.2f} MB tensors={v['tensors']}")


if __name__ == "__main__":
    main()
