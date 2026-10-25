# Mobile SLM fact-check log

**Project:** tinySLM-REA / MOBILE-SLM.md  
**Date:** 2026-10-25  
**Method:** 3 passes per claim.

1. **Pass 1 — source existence:** primary source (Apple/Google docs, model card, device spec, whitepaper, shipped artifact).
2. **Pass 2 — number/unit/condition:** number, unit, denominator, model size, quantization, context, batch, device.
3. **Pass 3 — context/fairness/falsification:** same runtime? same quantization? vendor or independent? counterexample?

Status labels: **verified / derived / vendor / estimate / unverified**.

---

## 1. Apple platform

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F101 | Foundation Models 4,096 tokens/session | S101/S102 | ✅ | ✅ 4,096 | ✅ system model, not custom | verified | Instructions/tools/schemas consume the window |
| F102 | PCC 32K context, daily quota | S103 | ✅ | ✅ 32K | ⚠️ network + entitlement | verified | Not on-device |
| F103 | Apple Intelligence 8-14GB storage | S104 | ✅ | ✅ 8-14GB | ⚠️ multiple models/assets | verified | Not the 3B LLM alone |
| F104 | Core AI .aimodel, CPU/GPU/ANE, background entitlement | S105 | ✅ | ✅ iOS 27 | ✅ | verified | Requires Xcode 27 |
| F105 | Core ML palettization 1/2/3/4/6/8-bit | S106 | ✅ | ✅ N=1,2,3,4,6,8 | ✅ per-grouped-channel iOS18 | verified | LUT 8-bit iOS18 |
| F106 | Core ML linear 4/8-bit weights, 8-bit activations | S107 | ✅ | ✅ | ⚠️ A17 Pro/M4 for INT8 compute | verified | |
| F116 | iPhone 17 Pro 12GB, A19 Pro 16-core ANE | S113 | ✅ | ✅ | ✅ | verified | Apple does not publish TOPS |
| F117 | iPhone 18 Pro 12GB, A20 Pro dual 16-core ANE, +50% BW | S114/S115/S116 | ✅ | ✅ 12GB, dual 16-core | ⚠️ absolute BW not published | vendor | |
| F118 | A20 Pro ~115.2GB/s | S116 | ✅ leak | ⚠️ 96-bit + 9600MT/s | ⚠️ estimate | estimate | Consistent with +50% claim |
| F140 | iPhone 18 Pro +40% sustained | S115/S116 | ✅ | ⚠️ vendor claim | ⚠️ independent reviews vary | vendor | |

## 2. Android platform

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F119 | S26 Ultra SD 8 Elite Gen 5, 12/16GB | S117 | ✅ | ✅ | ✅ | verified | Android 16/17 |
| F120 | Pixel 11 Pro XL Tensor G6, 12/16GB | S118 | ✅ | ✅ | ✅ | verified | Android 17 |
| F121 | Dimensity 9500 LPDDR5X 10667, NPU 990, >2x, -56% | S119 | ✅ | ✅ 10667 | ⚠️ vendor claims | vendor | Absolute tok/s not given |
| F122 | Android budgets 3.5/5.5/7.5GB | S125 | ✅ | ⚠️ heuristic | ⚠️ not OS limit | estimate | LMK/zRAM/OEM dependent |
| F129 | NNAPI deprecated Android 15 | S124 | ✅ | ✅ | ✅ | verified | May fall back to CPU |
| F130 | LiteRT NPU API 31+, arm64, SD 8 Gen 2+, Dimensity 7300-9500 | S121/S122/S123 | ✅ | ✅ | ✅ | verified | AOT/JIT, Play AI Pack |
| F131 | Google Play 500MB base, 4GB total, 30GB on-demand | S126 | ✅ | ✅ | ✅ | verified | 200MB+ warning |
| F132 | Gemini Nano <4K input, <4K output, no background, quota | S128/S129 | ✅ | ✅ | ✅ | verified | Prompt API beta |
| F133 | Gemini Nano nano-v2/v3/v4 device list | S128 | ✅ | ✅ | ✅ | verified | Feature APIs differ |

## 3. Bonsai / ternary

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F108 | Bonsai 2B 89.9 tok/s iPhone 17 Pro Max, PQ2_0 0.52GB | S109 | ✅ | ✅ PQ2_0 | ⚠️ vendor; not PTQ1_0 | vendor | PTQ1_0 is 0.43GB |
| F109 | Bonsai 4B 39.8, 9B 22.3 tok/s | S109 | ✅ | ✅ | ⚠️ vendor | vendor | Batch 1 |
| F110 | iPhone ~6GB per-app limit | S109 | ✅ | ⚠️ vendor measurement | ⚠️ Apple does not publish | vendor | Device/OS dependent |
| F111 | 2B 429,183,456 bytes, 1.8245 bpw | S132/S135 | ✅ | ✅ | ✅ | derived | Parser + fork |
| F112 | 4B 4,205,751,296 params, 32 layers, 8 full, 4 KV, 32KiB/token | S131 | ✅ | ✅ | ✅ | derived | Header only |
| F113 | 9B 8,953,803,264 params, same KV | S131 | ✅ | ✅ | ✅ | derived | Header only |
| F114 | 4B 949,549,920 bytes, 1.8062 bpw | S111/S131 | ✅ | ✅ | ✅ | derived | Payload 1.75 |
| F115 | 9B 1,997,486,976 bytes, 1.7847 bpw | S112/S131 | ✅ | ✅ | ✅ | derived | Payload 1.75 |
| F134 | 2B 12KiB/token; 262K 3.0GiB | S132 | ✅ | ✅ | ✅ | derived | 6 full, 2 KV, 256 dims |
| F135 | Qwen3 0.6B 112KiB/token; 32K 3.5GiB | S139 | ✅ | ✅ 28 layers, 8 KV, head_dim 128 | ✅ | derived | Config |
| F136 | 2B 0.80GiB at 4K, 3.75GiB at 262K | S132 | ✅ | ✅ | ✅ | derived | Runtime 0.35GiB |
| F137 | 9B 3.21GiB at 32K, 6.21GiB at 128K | S131 | ✅ | ✅ | ✅ | derived | Runtime 0.35GiB |
| F139 | Bonsai 0.125 vs 0.216 mWh/token at 9B | S109 | ✅ | ✅ | ⚠️ M5 Pro board power | vendor | 1.7-2.0x |
| F141 | Qwen3.5 2B 12KiB/token; 262K 3.0GiB | S140 | ✅ | ✅ | ✅ | derived | Same KV geometry as Bonsai 2B |

## 4. Runtime benchmarks

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F123 | Gemma4-E2B S26 Ultra 47/52, iPhone 17 Pro 25/57 | S120 | ✅ | ✅ | ⚠️ vendor benchmark | vendor | Same runtime, different device |
| F124 | Gemma4-E4B 18/22 vs 10/25 | S120 | ✅ | ✅ | ⚠️ vendor | vendor | |
| F125 | Gemma3-1B S24 Ultra 33 CPU / 24 GPU | S120 | ✅ | ✅ | ✅ | vendor | GPU slower |
| F126 | Phi-4-mini 7 CPU / 10 GPU | S120 | ✅ | ✅ | ✅ | vendor | |
| F127 | Qwen2.5-1.5B 34 CPU / 31 GPU | S120 | ✅ | ✅ | ✅ | vendor | |
| F128 | Qwen3-0.6B 9 CPU / 21 GPU | S120 | ✅ | ⚠️ CPU result odd | ⚠️ power config? | vendor | Do not overinterpret |

## 5. Corrections applied during review

1. **Llama 3.2 3B KV double-count fixed.**  
   The first draft used 56KiB/token (missing K+V). Correct is 112KiB/token. 32K total is 5.53GiB, not 3.78GiB.

2. **Llama 3.2 8B KV double-count fixed.**  
   Correct is 128KiB/token. 32K total is 8.54GiB, not 6.54GiB.

3. **8B 4-bit at 32K is not a 16GB Android fit.**  
   Under the 7.5GiB planning budget, 8.54GiB fails. The report now says 24GB-class or a higher app budget.

4. **Android 16GB 262K is not "none".**  
   Bonsai 2B ternary (3.75GiB) and Qwen3.5 2B 4-bit (4.33GiB) fit; only 4B/9B ternary fail. The table now lists both 2B options.

5. **Bonsai 2B 89.9 tok/s is PQ2_0, not PTQ1_0.**  
   The report explicitly separates the 0.52GB PQ2_0 measurement from the 0.43GB PTQ1_0 file analyzed.

6. **A20 Pro 115.2GB/s is an estimate, not an Apple number.**  
   Apple only says +50%; the 96-bit interface is a leak. The report labels it 推測.

7. **Android memory budgets are heuristics, not OS limits.**  
   The report uses 3.5/5.5/7.5GB and labels them 経験則/推測.

8. **Gemini Nano 4K is input, not total context.**  
   The docs say input under 4,000 tokens and output under 4K; the report says the same.

## 6. Unresolved / not checked

- No actual iPhone/Android benchmark was run by this project.
- iPhone 18 Pro per-app limit is assumed to be ~6GB (not measured).
- Android 8/12/16GB budgets are planning heuristics; OEM LMK/zRAM behavior varies.
- A20 Pro absolute bandwidth is not published.
- Dimensity 9500 / Snapdragon 8 Elite Gen 5 NPU LLM performance is vendor-dependent and not independently measured.
- Core AI quantization support and real-world ANE speed are not independently measured.
- Quality impact of 2-bit/4-bit quantization on the golden set was not measured here.

These limitations are repeated in MOBILE-SLM.md and Appendix E.
