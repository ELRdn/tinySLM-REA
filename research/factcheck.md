# Fact-check log

**Project:** tinySLM-REA  
**Date:** 2026-10-25  
**Method:** 3 passes per claim.

1. **Pass 1 — source existence:** Is there a primary source (paper, model card, official blog, shipped artifact)? URL, authors, date, version.
2. **Pass 2 — number/unit/condition:** Does the number match the source? Are units and denominators explicit? Is the comparison set the same?
3. **Pass 3 — context/fairness/falsification:** Is the baseline appropriate? Is the benchmark contaminated or saturated? Is it a vendor claim or independent replication? Is there a counterexample?

Status labels:

- **verified** — primary source read; number/claim checked in context.
- **derived** — calculated by this project from verified inputs.
- **vendor** — vendor/model-card claim; not independently replicated.
- **contested** — sources disagree, or the claim depends on a non-comparable setting.
- **unverified** — not checked; do not treat as settled.

---

## 1. Scaling and training

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F001 | Chinchilla 70B, 1.4T tokens | S01 | ✅ | ✅ 70B/1.4T | ✅ training-optimal, not inference-optimal | verified | Abstract/Sec.1 |
| F002 | Equal scaling of params and tokens | S01 | ✅ | ✅ | ✅ | verified | ~20 tokens/param |
| F039 | ~1B requests -> smaller/longer | S39 | ✅ | ✅ ~1B, 10k tokens/param | ✅ | verified | Inference-aware scaling |
| F040 | Quantization degradation grows with data | S40 | ✅ | ✅ | ✅ | verified | "more data can be harmful at fixed low precision" |
| F041 | Compute halves every ~8 months | S41 | ✅ | ✅ 8 months, CI 5-14 | ✅ | verified | Algorithmic progress |

## 2. Small models and data

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F003 | phi-1 1.3B, HumanEval 50.6/MBPP 55.5 | S03 | ✅ | ✅ 1.3B, 50.6/55.5, 6B+1B | ⚠️ narrow code benchmark; contamination risk | verified | Do not generalize |
| F004 | phi-1.5 ~5x larger | S04 | ✅ | ⚠️ vendor summary | ⚠️ benchmark-dependent | vendor | "comparable" is vague |
| F005 | phi-3-mini 3.8B, MMLU 69, MT-Bench 8.38 | S05 | ✅ | ✅ 3.8B/3.3T/69/8.38 | ⚠️ older baselines, saturated benchmarks | verified | Claim is conditional |
| F006 | phi-4 14B, STEM > GPT-4o/Llama-3.3 70B | S06 | ✅ | ✅ MATH 80.4, GPQA 56.1 | ⚠️ SimpleQA 3.0 vs 39.4 | verified | Wins STEM, loses facts |
| F007 | TinyStories ~10M coherent | S07 | ✅ | ✅ ~10M, restricted vocab | ⚠️ not general language | verified | Domain-limited |
| F008 | SmolLM2 1.7B, 11T tokens | S08 | ✅ | ✅ 1.7B/11T | ✅ deliberate overtraining | verified | 6,470 tokens/param |
| F009 | MobileLLM +2.7%/+4.3% | S09 | ✅ | ✅ 125M/350M | ✅ zero-shot | verified | Architecture matters |
| F055 | Japanese 31 vs 70 tokens | S59/S62 | ✅ | ✅ one sentence | ⚠️ one sentence only | derived | Not a full fertility study |
| F056 | Embedding share 6-63% | S35/S59/S62 | ✅ | ✅ calculated | ⚠️ total parameter definitions differ | derived | Approximate |

## 3. Distillation

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F012 | Distillation beats SL up to a threshold | S12 | ✅ | ✅ | ✅ if student compute is below threshold; otherwise SL wins | verified | The strongest correction |
| F013 | GKD on-policy KD | S13 | ✅ | ✅ | ✅ | verified | No universal 2x claim |
| F014 | MiniLLM reverse KL, 120M-13B | S14 | ✅ | ✅ 120M-13B | ⚠️ mode-seeking can reduce diversity | verified | |
| F049 | Long CoT can degrade SLMs by up to 75% | S50 | ✅ | ✅ 8K/220K examples | ✅ error accumulation | verified | Important limit |
| F050 | IPD 24.55 -> 29.72 on Qwen3-0.6B/s1K | S51 | ✅ | ✅ | ✅ small-model-specific | verified | |

## 4. Architecture

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F054 | Qwen3.5-2B 24 layers, 3:1 hybrid, 262K, 248K vocab | S38/S59 | ✅ | ✅ | ✅ | verified | Bonsai base |
| F026 | Nemotron 8.89B, 10.6T, 128K, up to 6x | S28 | ✅ | ✅ | ⚠️ vendor benchmark | vendor | Hybrid Mamba-Transformer |
| F029 | Gemma 3 1B-27B, 128K, distillation | S31 | ✅ | ✅ | ✅ | verified | Gemma 3 4B ~ Gemma 2 27B is vendor |
| F030 | Qwen3 0.6B-235B, generation compression | S32 | ✅ | ✅ | ⚠️ previous-generation comparison | vendor | Not current same-size |
| F033 | Gemma 3 270M = 170M emb + 100M blocks | S35/S58 | ✅ | ✅ 170M/100M | ⚠️ config gives 167.8M emb; rounding | vendor | 6T tokens |
| F034 | Bonsai 2B 1.88B, 1.75 bpw PTQ, 262K, 18+6 | S36/S37/S62 | ✅ | ✅ | ⚠️ quality claims vendor | verified (structure) | Our parse |
| F035 | File 429,183,456 bytes; 1.7778/1.8245 bpw | S62 | ✅ | ✅ | ✅ | derived | Denominator matters |
| F036 | PTQ1_0 28B/128 = 1.75 | S60/S62 | ✅ | ✅ | ✅ | verified | Cross-checked with fork |
| F037 | Embedding 27.0%, FFN 48.1%, attention 20.7%, SSM 4.1% | S62 | ✅ | ✅ | ✅ | derived | Params, not FLOPs |
| F038 | KV 25.8GB all-full -> 6.0GB hybrid @262K | S62 | ✅ | ✅ | ⚠️ assumptions (FP16, one sequence) | derived | 32K = 0.75GB |
| F059 | Bonsai 2B 0.43GB LM + 0.36GB vision | S37 | ✅ | ✅ | ⚠️ headline is LM-only | verified | Deployment footprint larger |

## 5. Quantization / pruning

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F010 | BitNet b1.58 matches FP16 same size/tokens | S10 | ✅ | ✅ | ⚠️ native kernels required | verified | |
| F011 | BitNet 2B4T 0.4GB, 29ms, 0.028J | S11 | ✅ | ✅ non-emb memory | ⚠️ vendor, generic runtime warning | vendor | |
| F020 | Minitron 8B/4B from 15B, 40x fewer tokens, <3% data | S22 | ✅ | ✅ | ✅ | verified | |
| F021 | SparseGPT 50-60%, 175B, <4.5h | S23 | ✅ | ✅ | ⚠️ unstructured sparsity latency caveat | verified | |
| F022 | Wanda 50% unstructured matches dense at 65B/70B | S24 | ✅ | ✅ | ⚠️ no speedup guarantee | verified | |
| F023 | AWQ 1% salient, >3x | S25 | ✅ | ✅ | ⚠️ includes TinyChat kernels | verified | |
| F024 | GPTQ 175B 3-4 bit, ~4 GPU hours | S26 | ✅ | ✅ | ✅ | verified | |
| F060 | PTQ1_0 integer identity | S60 | ✅ | ✅ | ✅ | verified | Our decoder reproduces |

## 6. Inference

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F015 | Speculative 2-3x, exact | S15/S16 | ✅ | ✅ T5-XXL, Chinchilla 70B | ⚠️ large models; small target may be slower | verified | |
| F016 | Medusa 2.2x / 2.3-2.8x | S17 | ✅ | ✅ | ✅ lossless | verified | |
| F017 | EAGLE-2 3.05-4.26x; EAGLE-3 up to 6.5x | S18/S19 | ✅ | ✅ | ⚠️ large-model regime | verified | |
| F018 | s1 1K, 56.7 AIME | S20 | ✅ | ✅ | ⚠️ 32B is not an SLM | verified | |
| F019 | Test-time compute >4x efficiency | S21 | ✅ | ✅ | ⚠️ prompt difficulty dependent | verified | |
| F046 | FrugalGPT 98% cost reduction | S47 | ✅ | ✅ | ⚠️ API prices/task | verified | |
| F047 | RouteLLM >2x cost reduction | S48 | ✅ | ✅ | ⚠️ router quality | verified | |
| F048 | Co-failure beta 0.052/0.079 | S49 | ✅ | ✅ | ✅ ensemble ceiling | verified | |

## 7. Evaluation

| ID | Claim | Source | P1 | P2 | P3 | Status | Note |
|---|---|---|---|---|---|---|---|
| F044 | MMLU-CF GPT-4o 73.4 | S42 | ✅ | ✅ 73.4/71.9 | ⚠️ different test set from MMLU 88 | verified | Not directly comparable |
| F045 | GSM1k up to 8% drop | S43 | ✅ | ✅ 8% | ✅ frontier models smaller gap | verified | |
| F051 | Phi-4 SimpleQA 3.0 vs GPT-4o 39.4 | S06/S52 | ✅ | ✅ | ✅ | verified | Long-tail factual gap |
| F052 | Embers: probability-sensitive accuracy | S53 | ✅ | ✅ | ✅ | verified | |
| F053 | RAG + Self-RAG | S54/S55 | ✅ | ✅ | ✅ | verified | Knowledge, not reasoning |

## 8. Claims that were corrected or qualified

1. **"1.58-bit" vs "1.75/1.82 bit":** ternary entropy is 1.585; PTQ1_0 is 1.75; whole file is 1.8245. Always state the denominator.
2. **"Bonsai 2B beats BF16 on 5 benchmarks":** this is same-model quantization, not a larger-model win. Vendor claim.
3. **"Phi-3 3.8B equals GPT-3.5":** only on selected saturated benchmarks; GPT-3.5 version/settings unclear.
4. **"MMLU 88 vs MMLU-CF 73.4":** different test sets; not a direct comparison. Use as contamination evidence only.
5. **"Gemma 3 270M 170M embeddings":** blog rounds 170M; config computes 167.8M. Note the rounding.
6. **"Speculative decoding 2-3x":** large-model numbers; 2B can be slower (Bonsai 2B).
7. **"Distillation always beats supervised":** false; threshold and teacher-existence conditions.
8. **"Small models are the future of agentic AI":** position paper, not a universal empirical result.

## 9. Unresolved / not checked

- Independent benchmark reproduction of Bonsai 2B.
- Runtime performance of the WebGPU bundle.
- Japanese tokenizer fertility across multiple genres.
- Quality of ternary quantization on long reasoning, math, code.
- Safety/bias evaluation.
- License/legal review of model redistribution.

These are listed in the report's limitations and appendix E.
