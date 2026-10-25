# 参考文献・一次資料

**アクセス日:** 2026-10-25  
**モバイル編:** iPhone / Android の参考文献は [`MOBILE-SLM.md`](../MOBILE-SLM.md) 付録D にあります。
**方針:** 論文は arXiv、モデルは Hugging Face のモデルカード、製品は公式ブログを優先。ベンダー主張は「vendor」と明記。URL は執筆時点のもの。

**Gemma 4 編:** 完全な一覧は [`GEMMA4-TERNARY-MOBILE.md`](../GEMMA4-TERNARY-MOBILE.md) 付録D にあります。以下は主要な一次資料の抜粋です。

---

## Gemma 4 / モバイル三値化

- **[G4-01] Gemma 4 Technical Report** — https://arxiv.org/abs/2607.02770 — arXiv:2607.02770v2、2026-07-24。アーキテクチャ、QAT、MTP、Arena、安全ポリシー。
- **[G4-02] Gemma 4 E2B model card** — https://huggingface.co/google/gemma-4-E2B-it — 5.1B total / 2.3B effective、128K、140+ languages pre-trained、35+ out-of-box。
- **[G4-03] Gemma 4 E4B model card** — https://huggingface.co/google/gemma-4-E4B-it — 8B total / 4.5B effective。
- **[G4-04] Gemma 4 12B model card** — https://huggingface.co/google/gemma-4-12B-it — 12B unified、256K。
- **[G4-05] Gemma 4 26B-A4B model card** — https://huggingface.co/google/gemma-4-26B-A4B-it — MoE 128 experts、top-8、3.8B active。
- **[G4-06] Gemma 4 31B model card** — https://huggingface.co/google/gemma-4-31B-it — dense 31B。
- **[G4-07] Gemma 4 QAT blog** — https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/ — 2026-06-05。mobile schema、static activations、2-bit targeted、「E2B 1GB」主張。
- **[G4-08] Gemma 4 license** — https://ai.google.dev/gemma/docs/gemma_4_license — Apache 2.0。
- **[G4-09] LiteRT-LM E2B** — https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm — GPU 2.008GB、generic 2.588GB、S26 / iPhone ベンチマーク。
- **[G4-10] LiteRT-LM E4B** — https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm — GPU 2.969GB、generic 3.660GB。
- **[G4-11] LiteRT-LM 12B** — https://huggingface.co/litert-community/gemma-4-12B-it-litert-lm — GPU 5.986GB、generic 6.883GB、128K。
- **[G4-12] LiteRT-LM 26B-A4B** — https://huggingface.co/litert-community/gemma-4-26B-A4B-it-litert-lm — GPU 15.787GB。
- **[G4-13] LiteRT-LM 31B** — https://huggingface.co/litert-community/gemma-4-31B-it-litert-lm — GPU 19.218GB。
- **[G4-14] LiteRT-LM GitHub** — https://github.com/google-ai-edge/LiteRT-LM — v0.18.1、`CLiteRTLM.xcframework`、`.litertlm` schema。
- **[G4-15] AI Edge Gallery APK 1.0.20** — https://github.com/google-ai-edge/gallery/releases — SHA-256 `036da9de8c57a2ba6226a6e70d2ba00aa4f5546fa2409ee44639c14212f9f6cb`。
- **[G4-16] BitNet b1.58** — https://arxiv.org/abs/2402.17764 — ternary、QAT、専用カーネル。
- **[G4-17] BitNet b1.58 2B4T** — https://arxiv.org/abs/2504.12285 — 2B、4T tokens。
- **[G4-18] Ternary Bonsai 2 whitepaper** — https://github.com/PrismML-Eng/Bonsai-demo — PTQ1_0 1.75bpw。
- **[G4-19] Qwen3.5-2B** — https://huggingface.co/Qwen/Qwen3.5-2B — 24 layers、3:1 Gated DeltaNet、262K、248K vocab。
- **[G4-20] llm-jp-3-3.7b-instruct** — https://huggingface.co/llm-jp/llm-jp-3-3.7b-instruct — 日本語トークナイザの比較対象。
- **[G4-21] MOBILE-SLM.md（本リポジトリ）** — iPhone / Android の予算・帯域・NPU・配布の前提。
- **[G4-22] Chatbot Arena** — https://arxiv.org/abs/2403.04132 — ペアワイズ人手評価。

**本プロジェクトの証拠:** `rea/evidence/gemma4_safetensors_breakdown.json`、`gemma4_qat_gguf.json`、`gemma4_litertlm_header.json`、`gemma4_litertlm_quantization.json`、`gemma4_litertlm_12b_quantization.json`、`gemma4_ternary_error.json`、`gemma4_mobile_fit.json`、`gemma4_tokenizer.json`。

---

## A. スケーリング・訓練

- **[S01] Training Compute-Optimal Large Language Models (Chinchilla)** — https://arxiv.org/abs/2203.15556 — 70B/1.4T tokens、計算最適はパラメータとトークンを等倍で増やす。訓練最適の基準。
- **[S02] Scaling Laws for Neural Language Models** — https://arxiv.org/abs/2001.08361 — Kaplan らの初期のスケーリング則。損失はパラメータ・データ・計算のべき乗。
- **[S39] Beyond Chinchilla-Optimal: Accounting for Inference in Language Model Scaling Laws** — https://arxiv.org/abs/2401.00448 — 推論需要が大きいほど、小さく長く訓練するのが有利。10,000 tokens/param まで品質が伸びる。
- **[S40] Scaling Laws for Precision** — https://arxiv.org/abs/2411.04330 — 低精度の「実効パラメータ数」を定式化。データを増やすほど、固定低ビットの量子化劣化が大きくなる。
- **[S41] Algorithmic progress in language models** — https://arxiv.org/abs/2403.05812 — 同じ性能に必要な計算量は約8ヶ月で半減（95% CI 5-14ヶ月）。

## B. 小さなモデル・データ・蒸留

- **[S03] Textbooks Are All You Need (phi-1)** — https://arxiv.org/abs/2306.11644 — 1.3B、6B web + 1B synthetic、HumanEval 50.6%、MBPP 55.5%。
- **[S04] Textbooks Are All You Need II: phi-1.5** — https://arxiv.org/abs/2309.05463 — 1.3B が約5倍のモデルに匹敵（ベンダー主張）。
- **[S05] Phi-3 Technical Report** — https://arxiv.org/abs/2404.14219 — 3.8B、3.3T tokens、MMLU 69%、MT-Bench 8.38、 phone。
- **[S06] Phi-4 Technical Report** — https://arxiv.org/abs/2412.08905 — 14B、STEM で GPT-4o/Llama-3.3 70B を上回るが SimpleQA は 3.0。
- **[S07] TinyStories** — https://arxiv.org/abs/2305.07759 — 約10M のモデルが制限語彙で一貫した英語を生成。
- **[S08] SmolLM2** — https://arxiv.org/abs/2502.02737 — 1.7B、11T tokens、FineMath/Stack-Edu/SmolTalk。
- **[S09] MobileLLM** — https://arxiv.org/abs/2402.14905 — sub-1B の深く薄い設計、埋め込み共有、GQA、ブロック重み共有。
- **[S12] Distillation Scaling Laws** — https://arxiv.org/abs/2502.08606 — 蒸留が教師あり学習に勝つ条件と閾値。生徒の計算量が大きいと教師ありが勝つ。
- **[S13] On-Policy Distillation (GKD)** — https://arxiv.org/abs/2306.13649 — 生徒の自己生成系列に対する先生のフィードバック。
- **[S14] MiniLLM** — https://arxiv.org/abs/2306.08543 — 逆KL + オンポリシー蒸留。120M-13B。
- **[S27] Small Language Models are the Future of Agentic AI** — https://arxiv.org/abs/2506.02153 — NVIDIA のポジション論文。7B は 70-175B より 10-30x 安い。
- **[S67] DeepSeek-R1** — https://arxiv.org/abs/2501.12948 — 純粋RLによる推論能力の誘発と、小型モデルへの蒸留。
- **[S56] SmolLM3-3B model card** — https://huggingface.co/HuggingFaceTB/SmolLM3-3B — 3B、11.2T tokens、128K、6言語、hybrid reasoning。
- **[S57] Granite-4.0-H-350M model card** — https://huggingface.co/ibm-granite/granite-4.0-h-350m — 4 attention / 28 Mamba2 のハイブリッド。
- **[S65] DataComp-LM (DCLM)** — https://arxiv.org/abs/2406.11794 — 240T tokens、412M-7B、モデルベースフィルタリング。
- **[S66] Rho-1: Not All Tokens Are What You Need** — https://arxiv.org/abs/2404.07965 — 選択的言語モデリング。

## C. アーキテクチャ・長文

- **[S28] NVIDIA Nemotron Nano 2** — https://arxiv.org/abs/2508.14444 — 8.89B、Mamba2-Transformer ハイブリッド、128K、最大6x throughput（ベンダー）。
- **[S29] MiniCPM** — https://arxiv.org/abs/2404.06395 — 1.2B/2.4B が 7B-13B に匹敵（ベンダー）、WSD scheduler。
- **[S30] TinyLlama** — https://arxiv.org/abs/2401.02385 — 1.1B、1T tokens、3 epochs。
- **[S31] Gemma 3 Technical Report** — https://arxiv.org/abs/2503.19786 — 1B-27B、local/global attention、128K、蒸留。
- **[S32] Qwen3 Technical Report** — https://arxiv.org/abs/2505.09388 — 0.6B-235B、dense/MoE、thinking/non-thinking。世代圧縮の主張。
- **[S33] Apple Intelligence Foundation Language Models 2025** — https://arxiv.org/abs/2507.13575 — 約3B on-device、KV-cache sharing、2-bit QAT。
- **[S34] Meta Llama 3.2 blog** — https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/ — 1B/3B は Llama 3.1 8B から pruning + distillation、128K。
- **[S35] Introducing Gemma 3 270M** — https://developers.googleblog.com/en/introducing-gemma-3-270m/ — 270M = 170M embedding + 100M blocks、INT4 QAT、0.75% battery（ベンダー）。
- **[S58] Gemma 3 270M model card** — https://huggingface.co/google/gemma-3-270m-it — 270M は 6T tokens、32K context。
- **[S38] Qwen3.5-2B model card** — https://huggingface.co/Qwen/Qwen3.5-2B — 24 layers、3:1 Gated DeltaNet:Gated Attention、262K、248K vocab、MTP。
- **[S59] Qwen3.5-2B config/tokenizer** — https://huggingface.co/Qwen/Qwen3.5-2B/tree/main — tokenizer 実験の入力。
- **[S60] PrismML llama.cpp fork (branch prism)** — https://github.com/PrismML-Eng/llama.cpp/tree/prism — PTQ1_0/PQ2_0/Q2_0 の実装。
- **[S61] WebGPU Bonsai 2 Hermes Space** — https://huggingface.co/spaces/webml-community/ternary-bonsai-2-hermes-webgpu — WebGPU バンドル。
- **[S36] Ternary Bonsai 2 2B/4B/9B whitepaper** — https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-small-whitepaper.pdf — 1.88B、ternary、Hadamard、262K、90 tok/s（ベンダー）。
- **[S37] Ternary-Bonsai-2-2B-gguf model card** — https://huggingface.co/prism-ml/Ternary-Bonsai-2-2B-gguf — PTQ1_0 0.43GB、PQ2_0 0.52GB、Q2_0 0.55GB、vision projector。
- **[S63] Ternary Bonsai 8B whitepaper** — https://github.com/PrismML-Eng/Bonsai-demo/blob/main/ternary-bonsai-8b-whitepaper.pdf — 8B: 75.5 avg、1.75GB、27 tok/s iPhone（ベンダー）。
- **[S64] Ternary Bonsai 2 27B whitepaper** — https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-27b-whitepaper.pdf — 27B: 98.2% retention、9.1x smaller、46.8 tok/s laptop（ベンダー）。

## D. 量子化・pruning

- **[S10] BitNet b1.58** — https://arxiv.org/abs/2402.17764 — ternary、同サイズ FP16 に匹敵、専用カーネル前提。
- **[S11] BitNet b1.58 2B4T** — https://arxiv.org/abs/2504.12285 — 2B、4T、0.4GB non-emb、29ms CPU TPOT、0.028J（ベンダー）。
- **[S22] Minitron** — https://arxiv.org/abs/2407.14679 — 15B から 8B/4B、pruning + distillation、40x fewer tokens、<3% data。
- **[S23] SparseGPT** — https://arxiv.org/abs/2301.00774 — 50-60% one-shot pruning、175B を4.5時間。
- **[S24] Wanda** — https://arxiv.org/abs/2306.11695 — 重み×活性化、再訓練なし、50% unstructured。
- **[S25] AWQ** — https://arxiv.org/abs/2306.00978 — 1% salient、TinyChat >3x。
- **[S26] GPTQ** — https://arxiv.org/abs/2210.17323 — 175B を3-4 bit、約4 GPU hours。
- **[S68] SmoothQuant** — https://arxiv.org/abs/2211.10438 — W8A8、活性化の外れ値を移動。
- **[S69] LoRA** — https://arxiv.org/abs/2106.09685 — 低ランク適応。
- **[S70] QLoRA** — https://arxiv.org/abs/2305.14314 — 4-bit + LoRA、65B を48GB GPUで。

（S68-S70 は本文の量子化・微調整の節で引用。）


## E. 推論・テスト時計算・ルーティング

- **[S15] Fast Inference via Speculative Decoding** — https://arxiv.org/abs/2211.17192 — 出力分布を変えず2x-3x（T5-XXL）。
- **[S16] Accelerating LLM Decoding with Speculative Sampling** — https://arxiv.org/abs/2302.01318 — Chinchilla 70B で2x-2.5x。
- **[S17] Medusa** — https://arxiv.org/abs/2401.10774 — 2.2x、2.3-2.8x。
- **[S18] EAGLE-2** — https://arxiv.org/abs/2406.16858 — 3.05-4.26x、dynamic draft tree。
- **[S19] EAGLE-3** — https://arxiv.org/abs/2503.01840 — 最大6.5x、training-time test。
- **[S20] s1: Simple test-time scaling** — https://arxiv.org/abs/2501.19393 — 1K examples、budget forcing、s1-32B 56.7 AIME。
- **[S21] Scaling LLM Test-Time Compute Optimally** — https://arxiv.org/abs/2408.03314 — >4x efficiency vs best-of-N、compute-optimal allocation。
- **[S47] FrugalGPT** — https://arxiv.org/abs/2305.05176 — cascade、最大98% cost reduction。
- **[S48] RouteLLM** — https://arxiv.org/abs/2406.18665 — >2x cost reduction、router。
- **[S49] Co-Failure Ceiling** — https://arxiv.org/abs/2606.27288 — 67 models、beta 0.052 math / 0.079 code、ensemble の上限。
- **[S50] Through the Valley** — https://arxiv.org/abs/2506.07712 — SLM の Long CoT Degradation、最大 -75%。
- **[S51] In Their Own Words** — https://arxiv.org/abs/2509.22230 — IPD、Qwen3-0.6B/s1K 24.55 -> 29.72。

## F. RAG・評価

- **[S54] Retrieval-Augmented Generation** — https://arxiv.org/abs/2005.11401 — parametric + non-parametric memory。
- **[S55] Self-RAG** — https://arxiv.org/abs/2310.11511 — adaptive retrieval + self-critique。
- **[S42] MMLU-CF** — https://arxiv.org/abs/2412.15194 — contamination-free MMLU、GPT-4o 73.4%。
- **[S43] GSM1k** — https://arxiv.org/abs/2405.00332 — GSM8K の汚染検査、最大8% drop。
- **[S44] LiveCodeBench** — https://arxiv.org/abs/2403.07974 — contamination-free code benchmark。
- **[S45] Chatbot Arena** — https://arxiv.org/abs/2403.04132 — pairwise human preference、240K votes。
- **[S46] Length-Controlled AlpacaEval** — https://arxiv.org/abs/2404.04475 — length bias correction。
- **[S52] SimpleQA** — https://arxiv.org/abs/2411.04368 — short-form factuality、know what you know。
- **[S53] Embers of Autoregression** — https://arxiv.org/abs/2309.13638 — probability-sensitive accuracy。
- **[S62] 本プロジェクトのREA証拠** — `rea/evidence/bonsai2b.json`、`rea/evidence/webgpu_trace.md` — 観測・導出の一次記録。

---

## 注記

- ベンダー主張（vendor）は、モデル提供元の自己申告であり、本プロジェクトでは独立再現していません。
- ベンチマークの数値は、特に断らない限り、各論文・モデルカードの報告値です。評価設定が異なるため、異なるベンチマーク間の直接比較はできません。
- URL は2026-10-25時点でアクセス可能だったものです。arXiv のバージョンは執筆時点の最新を参照しました。
