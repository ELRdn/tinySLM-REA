# PTQ1_0 28-byte ternary block — reverse engineering note

**Target:** `Ternary-Bonsai-2-2B-PTQ1_0.gguf`  
**SHA-256:** `36061ad406df8a4903a6db005be350c50fabfaf717f9ef0acf4b76adcd9929fa`  
**Tensor sampled:** `token_embd.weight` (first block), offset `data_start + 8192`  
**Data start:** 10,999,008 bytes  
**Block size:** 28 bytes / 128 weights = 1.75 bits/weight

---

## 1. Container evidence

The GGUF header reports:

- version 3
- 320 tensors
- 49 metadata KV
- alignment 32
- `general.file_type = 143` (PTQ1_0)

The tensor table shows:

```
output_norm.weight          [2048]        F32       offset 0
token_embd.weight           [2048,248320] PTQ1_0    offset 8192
blk.0.attn_gate.weight      [2048,2048]   PTQ1_0    offset 111255552
...
```

The first PTQ1_0 tensor is `token_embd.weight` with 508,559,360 parameters.  
`508,559,360 / 128 = 3,973,120` blocks; `3,973,120 × 28 = 111,247,360` bytes.  
The next tensor offset is `111,255,552`; difference = `111,247,360` bytes. This confirms the 28-byte block size and row-major block layout.

---

## 2. Block layout (confirmed against PrismML fork)

From `ggml/src/ggml-common.h` in the PrismML fork (`prism` branch):

```c
#define QK_PTQ1_0 128
typedef struct {
    uint8_t qs[(QK_PTQ1_0 - 4*QK_PTQ1_0/64)/5]; // 24 B, 5 trits per byte -> 120 values
    uint8_t qh[QK_PTQ1_0/64];                   //  2 B, 4 trits per byte ->   8 values
    ggml_half d;                                // scale
} block_ptq1_0;
```

So:

| Field | Bytes | Contents |
|---|---:|---|
| `qs` | 24 | first 120 ternary values, base-3 packed, 5 trits/byte |
| `qh` | 2 | last 8 ternary values, 4 base-3 trits/byte (3^4=81 codes rescaled to 8 bits) |
| `d` | 2 | FP16 scale |

Total 28 bytes.

---

## 3. Raw bytes

First block of `token_embd.weight`:

```
06 97 4d 48 d8 85 6b a5 e1 65 49 9d 58 b3 d3 0a
60 16 25 de dd 98 2f 05 f4 cb f5 24
```

Split:

```
qs = 06 97 4d 48 d8 85 6b a5 e1 65 49 9d 58 b3 d3 0a
     60 16 25 de dd 98 2f 05
qh = f4 cb
d  = f5 24   (little-endian FP16)
```

FP16 decode:

```python
struct.unpack('<e', bytes.fromhex('f524'))[0]
# 0.0193634033203125
```

The parser reads `b[26:28]` (bytes `f5 24`) as little-endian FP16 and gets `0.0193634033203125`. The bytes at 24..25 are `f4 cb` (`qh[2]`).

---

## 4. Base-3 decode

The encoder (from `ggml-quants.c`):

```c
for (size_t n = 0; n < 5; ++n) {
    int xi = lroundf(x[m + n*c] * id) + 1; // -1,0,1 -> 0,1,2
    q *= 3;
    q += xi;
}
q = ((uint16_t)q * 256 + (243 - 1)) / 243;
```

The decoder:

```c
const uint8_t pow3[6] = {1, 3, 9, 27, 81, 243};
uint8_t q = x[i].qs[j + m] * pow3[n];  // uint8_t wrap
int16_t xi = ((uint16_t) q * 3) >> 8;
*y++ = (float) (xi - 1) * d;
```

The `uint8_t` wrap and `>>8` recover the base-3 digit without floating point. Our Python decoder:

```python
q = (qs[j + m] * pow3[n]) & 0xFF
xi = ((q * 3) >> 8)
value = (xi - 1) * d
```

The `qs` loop uses stages `(32, 16, 8)` because 24 bytes cannot fit 32 at once; the effective order is:

- stage 16: 16 bytes, 5 trits each = 80 values
- stage 8: 8 bytes, 5 trits each = 40 values
- total 120 values

Then `qh` gives the last 8 values.

---

## 5. First-block result

```
scale = 0.0193634033203125
trit counts: -1: 42, 0: 42, +1: 44
first 8 weights: -0.019363, 0, -0.019363, -0.019363, 0.019363, 0, 0, 0
```

Over 2,000 blocks:

```
trit counts: -1: 85,970, 0: 83,543, +1: 86,487
scale range: 0.0092163 .. 0.0258789
qs max: 255
```

`qs max = 255` is expected because the encoder rescales 0..242 to 0..255 via `ceil(q*256/243)`. It is **not** a sign of a different format.

---

## 6. Why 1.75 and not 1.58?

- Ternary entropy: `log2(3) = 1.58496` bits/weight.
- One FP16 scale per 128 weights: `16/128 = 0.125` bits/weight.
- Base-3 packing overhead: 28 bytes vs the ideal `(128*1.58496 + 16)/8 = 27.36` bytes.
- 28 bytes = 1.75 bits/weight exactly.

The whole file is 1.8245 bits/param because it includes:
- 169 F32 tensors (1,728,320 params; 6,913,280 bytes),
- tokenizer (248,320 tokens + 247,587 merges),
- metadata, alignment, padding.

---

## 7. What is confirmed / not confirmed

**Confirmed:**
- 28-byte block size and 128-weight group.
- 24 B `qs` + 2 B `qh` + 2 B FP16 scale.
- Base-3 5-trit packing for the first 120 values, 4-trit/byte packing for the last 8.
- Exact integer decode path.
- Tensor offset arithmetic.

**Not confirmed:**
- Quality of the quantized model (no benchmark execution).
- Exact behavior on every runtime (WebGPU `q1_0` may use a different packing).
- Whether the Hadamard rotation is applied exactly as described in all kernels.

**Evidence:**
- `rea/evidence/bonsai2b.json`
- `rea/analyze_gguf.py`
- PrismML fork: `ggml/src/ggml-common.h`, `ggml/src/ggml-quants.c` (branch `prism`)
