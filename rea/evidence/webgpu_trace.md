# WebGPU bundle — static reverse-engineering note

**Target:** `https://huggingface.co/spaces/webml-community/ternary-bonsai-2-hermes-webgpu`  
**Files analyzed:**
- `assets/index-625vxx6U.js` (107,714 bytes)
- `assets/qwen35-vision-Kzp5MMIJ.js` (2,208,435 bytes)
- `index.html` (1,289 bytes)

**REA operation:** `analyze_javascript_application`  
**REA evidence ID:** `ev_bd837c2925b8a8f56ecc1ead2c4caf866345270ada956c0b8adb89f65371590f`  
**Parent evidence ID:** `ev_60dcd225cdb0ad870ece451b3f6df95520a5da0def387a46717908d9308d5d9f`  
**Mode:** static AST analysis, directory input, summary view  
**Execution:** not executed

---

## 1. REA summary

From the REA summary:

- relevant files: 3
- parsed JavaScript files: 2
- visited AST nodes: 290,975
- findings: 40
- parse failures: 0
- modules: 0
- semantic coverage: partial (100,000-node ceiling)
- application coverage: complete
- unknowns: 46,107 semantic graph unknowns
- limitations include: "JavaScript and HTML were parsed as inert text; bundle bootstrap code was never executed."

This is a static observation, not a runtime trace.

---

## 2. Quantized matmul / dequant formats

The bundle defines a format enum for dequantized matrix multiplication:

```
q4_0, q4_k, q4_k_native_compact, q8_0, iq,
lut32, lut16, lut32_compact, lut16_compact,
lut2_32, lut2_16, q6_k, q5_k, q3_k, q2_k, q1_0
```

It also has separate `kFormat` / `vFormat` enums for KV cache, with a subset:

```
q4_0, q4_k, q8_0, iq, lut32, lut16,
q6_k, q5_k, lut32_compact, lut16_compact,
lut2_32, lut2_16
```

Observation: the browser runtime supports many GGUF-style quant formats plus custom LUT formats and `q1_0`. The model file's PTQ1_0 is not necessarily the same packing as the runtime's `q1_0`; the runtime may repack at load time.

Relevant snippets (minified, excerpted):

```js
format:{kind:`string`,required:!1,oneOf:[`q4_0`,`q4_k`,... ,`q1_0`]}
```

```js
oneOf:[`q4_0`,`q4_k`,`q8_0`,`iq`,`lut32`,`lut16`,...]
```

---

## 3. KV cache quantization

The bundle has a quantized KV-cache path:

```js
{% if quantizedCache %}
  {% include "ops/_shared/attn-quant-cache-load.wgsl.jinja" %}
  {{ emit_quant_load4("int8", "key", "key", "k_scale") }}
  {{ emit_quant_load4("int8", "value", "value", "v_scale") }}
{% else %}
  fn load_key4(indexV4:u32)->vec4<f32>{return vec4<f32>(key[indexV4]);}
  fn load_value4(indexV4:u32)->vec4<f32>{return vec4<f32>(value[indexV4]);}
{% endif %}
```

This is direct static evidence of an INT8 KV-cache path with per-key/value scales. It does not prove the path is enabled for this model at runtime; that depends on configuration.

---

## 4. Speculative decoding

The bundle defines a speculative-decoding interface:

```js
specDecodeRunner(){return null}
```

and a generation path that checks:

```js
if (o) {
  if (a) throw Error(`speculative decoding verifies greedy drafts; it cannot sample`);
  ...
}
```

Observation: the runtime has speculative decoding code, but the Bonsai 2B model class returns `null`, so the feature is disabled. When enabled, it is greedy-only (no sampling). This matches the model card's statement that speculative decoding with a draft model was slower at 2B.

---

## 5. Hadamard transform

The bundle includes WGSL templates:

- `ops/_shared/hadamard-block-stages.wgsl.jinja`
- `ops/_shared/hadamard-column-butterfly.wgsl.jinja`

The block-stages template contains a loop over spans:

```
{% for span in [1, 2, 4, 8, 16, 32, 64, 128, 256] %}
```

and butterfly operations:

```
v[r] = a[r] + a[r+span]
v[r+span] = a[r] - a[r+span]
```

This matches the GGUF metadata:

```
prism.hadamard.block_size = 512
prism.hadamard.transform = normalized-sylvester-walsh-hadamard
prism.hadamard.axis = input-last-dimension
```

---

## 6. Hybrid attention metadata

The bundle reads Qwen3.5-style metadata:

```js
f = Array.from({length: r}, (e, t) =>
  (t + 1) % o === 0 ? `full_attention` : `linear_attention`
)
```

where `r` is the layer count and `o` is `full_attention_interval`. It also reads:

```
qwen35.attention.key_length
qwen35.rope.dimension_count
qwen35.full_attention_interval
qwen35.ssm.group_count
qwen35.ssm.inner_size
qwen35.ssm.state_size
qwen35.ssm.time_step_rank
```

For Bonsai 2B: 24 layers, interval 4 -> 6 full-attention, 18 linear-attention.

---

## 7. Sampling

The bundle's sampling validator:

```js
const t = e.temperature ?? 1;
const n = e.top_k ?? 50;
const r = e.top_p ?? 1;
const i = e.min_p ?? 0;
...
if (!Number.isInteger(n) || n < 1 || n > 64)
  throw RangeError(`top_k must be an integer from 1 to 64 ...`);
if (t === 0 || n === 1) return null;
```

Observation: `top_k` is capped at 64; temperature 0 or top_k 1 means greedy. This is a runtime constraint, not a model property.

---

## 8. What this proves / does not prove

**Proves (static):**
- The runtime has quantized matmul kernels for many formats.
- It has an INT8 KV-cache path.
- It has a speculative-decoding interface, disabled for this model.
- It implements the Hadamard transform in WGSL.
- It reads hybrid-attention metadata and selects full vs linear layers.

**Does not prove:**
- Runtime performance or correctness.
- That the INT8 KV path is enabled for this model.
- That the `q1_0` packing matches GGUF PTQ1_0.
- That the Hadamard kernel is numerically identical to the reference.
- That the model produces the claimed benchmark scores.

**Limitations:**
- Static analysis of a minified bundle; no execution.
- Semantic graph partial due to 100,000-node ceiling.
- The bundle may load weights/model code remotely; not all runtime paths are in these files.
- No browser/WebGPU runtime capture was performed.

**Evidence:** `ev_bd837c2925b8a8f56ecc1ead2c4caf866345270ada956c0b8adb89f65371590f`
