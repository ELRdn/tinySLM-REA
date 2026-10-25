# Bonsai 4B / 9B GGUF header — range-parse note

**Targets:**
- `prism-ml/Ternary-Bonsai-2-4B-gguf` → `Ternary-Bonsai-2-4B-PTQ1_0.gguf`
- `prism-ml/Ternary-Bonsai-2-9B-gguf` → `Ternary-Bonsai-2-9B-PTQ1_0.gguf`

**Method:** HTTP Range request for the first 16 MiB of each file
(`Range: bytes=0-16777215`), then parse the GGUF v3 header and tensor table
in memory. The tensor data section was **not** downloaded or analyzed.

**Evidence:** `rea/evidence/bonsai_4b_9b_header.json`

---

## 1. Why range parsing is enough

The GGUF v3 header contains:

- magic, version, tensor count, metadata KV count;
- all metadata KV pairs (including architecture, layer count, KV heads,
  context length, Hadamard settings);
- the tensor table (name, dimensions, type, offset).

The 16 MiB prefix is enough for both files because the metadata and tensor
table are at the front. The first tensor data offset is far below 16 MiB in
both files, so the parse is complete for the header and tensor table.

Both servers returned HTTP 206 with the expected `Content-Range`, confirming
that the range was honored.

---

## 2. Results

| Item | Bonsai 4B | Bonsai 9B |
|---|---:|---:|
| File | `Ternary-Bonsai-2-4B-PTQ1_0.gguf` | `Ternary-Bonsai-2-9B-PTQ1_0.gguf` |
| File size | 949,549,920 bytes | 1,997,486,976 bytes |
| GGUF version | 3 | 3 |
| Tensor count | 426 | 427 |
| Metadata KV count | 50 | 49 |
| Total parameters | 4,205,751,296 | 8,953,803,264 |
| PTQ1_0 parameters | 4,200,857,600 | 8,946,450,432 |
| F32 parameters | 4,893,696 | 7,352,832 |
| Architecture | `qwen35` | `qwen35` |
| Layers | 32 | 32 |
| Hidden size | 2,560 | 4,096 |
| FFN size | 9,216 | 12,288 |
| Q heads | 16 | 16 |
| KV heads | 4 | 4 |
| Key/Value length | 256 / 256 | 256 / 256 |
| Full-attention interval | 4 | 4 |
| Full-attention layers | 8 | 8 |
| Context | 262,144 | 262,144 |
| KV per token | 32 KiB | 32 KiB |
| KV at 262K (FP16) | 8.0 GiB | 8.0 GiB |
| File bits/param | 1.8062 | 1.7847 |
| Payload bits/param | 1.75 | 1.75 |

`KV per token = 8 full layers × 4 KV heads × (256 + 256) × 2 bytes = 32,768 bytes`.

---

## 3. Why the file bits/param differ from 1.75

The PTQ1_0 payload is 1.75 bit/param. The whole file includes:

- F32 tensors for norms and SSM state paths;
- tokenizer and metadata;
- alignment/padding;
- the tensor table.

The 4B file has a larger F32 share relative to its size than the 9B file,
so its whole-file bits/param (1.8062) is slightly higher than the 9B's
(1.7847). The 2B file is 1.8245. All three are below 1.83.

---

## 4. What is confirmed

- 4B and 9B use the same hybrid-attention layout: 32 layers, 8 full,
  4 KV heads, 256 key/value dims.
- Both have 32 KiB KV per token, hence 8.0 GiB at 262K.
- Their parameter counts are 4.205B and 8.954B, not marketing-rounded
  "4B"/"9B".
- Their PTQ1_0 payload is 1.75 bit/param; whole-file values are
  1.8062 and 1.7847.

## 5. What is not confirmed

- Full-file SHA-256 (only the header was fetched; the repo provides
  `SHA256SUMS` for the complete files).
- Runtime performance (quoted from the vendor whitepaper, not measured here).
- Quality/benchmarks (vendor claims).
- Exact tensor data values (not downloaded).

---

## 6. Reproduction sketch

```python
import io, struct, urllib.request

class Reader:
    def __init__(self, f): self.f = f
    def read(self, n):
        b = self.f.read(n)
        if len(b) != n: raise EOFError
        return b
    def u32(self): return struct.unpack("<I", self.read(4))[0]
    def u64(self): return struct.unpack("<Q", self.read(8))[0]
    def string(self):
        n = self.u64(); return self.read(n).decode("utf-8", "replace")
    def value(self, t):
        if t == 8: return self.string()
        if t == 9:
            et = self.u32(); n = self.u64()
            return [self.value(et) for _ in range(n)]
        fmt = {0:"<B",1:"<b",2:"<H",3:"<h",4:"<I",5:"<i",6:"<f",
               7:"<?",10:"<Q",11:"<q",12:"<d"}[t]
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))[0]

url = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-4B-gguf/resolve/main/Ternary-Bonsai-2-4B-PTQ1_0.gguf"
req = urllib.request.Request(url, headers={"Range": "bytes=0-16777215"})
data = urllib.request.urlopen(req).read()
r = Reader(io.BytesIO(data))
assert r.read(4) == b"GGUF"
ver, nt, nk = r.u32(), r.u64(), r.u64()
...
```

The full parser and JSON output are in `rea/evidence/bonsai_4b_9b_header.json`.
