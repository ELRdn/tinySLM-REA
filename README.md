# tinySLM-REA

**小さくても勝てる — Tiny LLM / SLM の設計・逆解析・評価の全書**

> 1.88B・1.75bit の実物モデル（言語モデル部分）を分解し、「小さなモデルが大きなモデルを凌駕する条件」を数式・一次資料・実ファイルの証拠で確定する。視覚塔（~0.33B）は別ファイル。

---

## これは何か

小さな言語モデル（SLM / Tiny LLM）が、どのような条件で大きなモデルに勝てるのか。逆に、どこで必ず負けるのか。本書は、**ハイプではなく条件**として、次の3つのレベルで分析します。

1. **仕組みの解剖** — データ、蒸留、アーキテクチャ、量子化、推論システム、RAG、専門化、評価。
2. **実物の逆解析（REA）** — 配布されている Ternary Bonsai 2 2B の GGUF ファイル（429MB）を先頭から解析し、PTQ1_0 の28バイト量子化ブロック、ハイブリッド注意、Hadamard回転、トークナイザーを復元。さらに、ブラウザで動く WebGPU バンドルを静的解析。
3. **主張の監査** — 「3BがGPT-4を超えた」「1.58-bitで十分」などの代表的主張を、一次資料と公平性の観点で分類。

**メイン成果物:** [`REPORT.md`](REPORT.md)（約10万字）

**追加レポート:** [`MOBILE-SLM.md`](MOBILE-SLM.md) — iPhone / Android 別に、どのモデルがどこまで載るのかを帯域・メモリ・NPU・OS・配布から定量化（約6.7万字）。

**Gemma 4 編:** [`GEMMA4-TERNARY-MOBILE.md`](GEMMA4-TERNARY-MOBILE.md) — Gemma 4 E2B / E4B / 12B / 26B-A4B / 31B を、三値化・mobile QAT・iPhone / Android の予算・日本語 tokenizer・roleplay 評価まで分解（約10万字）。

---

## モバイル編の結論（先出し）

- **iPhoneは12GBでも、アプリが使えるのは約6GB。** Bonsaiの測定ではiPhone 17 Pro Maxのper-app limitは約6GB。
- **Androidは8GB≈3.5GB、12GB≈5.5GB、16GB≈7.5GB。** Android 8GBはiPhone 6GBより厳しく、12GBで同等、16GBで逆転。
- **2B三元は4KならiPhone A15以降 / Android 8GB以上で動く。** 262Kは3.75GiBで、iPhone 6GB/Android 12GBは余裕、Android 8GBは不可。
- **4B三元は32KならiPhone/Android 8GB（nominal）。** 9B三元は32KならiPhone/Android 8GB（nominal）、128KはAndroid 16GBのみ（nominal; safeは4B三元）。
- **8B 4-bitは4KならiPhone/Android 12GB（nominal）。** 32Kは8.54GiBで16GB Androidでも予算オーバー。
- **NPUのTOPSはLLMの速さではない。** 帯域・KV・カーネルが支配。同じLiteRT-LMでもAndroid CPUがiPhone CPUより速いことがある。
- **クロスプラットフォームはビルドマトリクス。** Core AI/MLX/Core ML/llama.cpp と LiteRT/ExecuTorch/llama.cpp で artifact が分かれる。

---

## Gemma 4 編の結論（先出し）

- **E2B は「2B」ではない。** 5.12B total / 2.3B effective。E4B は 8.00B / 4.5B。PLE が E2B 2.35B、E4B 2.82B を占める。
- **Google の mobile QAT は、すでに 2/4/8-bit 混合。** E2B の MLP は 2.58bpw、E4B の MLP は 4.02bpw、12B は一律 4.01bpw。三値の比較対象は「4-bit 一様」ではない。
- **E2B の三値化は、ほぼ得しない。** 32K で 2.32 → 2.19GiB（5.6%）。128K では「ternary + FP16 KV」より「QAT + INT8 KV」が軽い。まず KV を INT8 にする。
- **E4B の三値化は、Android 8GB の nominal を確保する。** 32K で 3.37 → 2.62GiB。ただし attention INT4 のハイブリッドは 2.79GiB で、safe 2.8GiB は紙一重。
- **12B の三値化は、iPhone の本命。** 32K で 6.33 → 3.87GiB、ハイブリッドでも 4.50GiB。**QAT は 4K でも 6.11GiB で iPhone に入らない。**
- **26B は 16GB Android の実験枠、31B はスマホ向けではない。** 三値 32K で 6.74 / 10.69GiB。
- **日本語トークナイザは Gemma 3 のまま。** 100文字あたり 61.3（Qwen3.5 56.7、llm-jp 48.4）。名前は 95.2。Gemma 4 は「日本語だから必然」ではなく、多言語・モバイル runtime・QAT を含めた条件付き最適解。
- **roleplay 品質は E2B/E4B/12B では未測定。** Arena は 31B（1451）と 26B-A4B（1438）だけ。MMLU では代用できない。
- **「E2B 1GB」は PLE 抜きの数字。** 実バンドルは 2.008GB、PLE だけで 1.211GB。PLE をストリーミングすれば 0.8GB 級に近づくが、実装依存。
- **最大の敵は、量子化ではなく QAT とカーネル。** 三値の重み誤差は 50〜60%。QAT / 蒸留なしの PTQ では roleplay の名前・敬語が壊れる。三値行列積の標準カーネルは未確認。

---

## 3分でわかる結論

- 小さなモデルは、大きなモデルより「賢い」のではない。**同じ予算・同じ情報・同じ時間・同じ範囲**で比べたときに勝つ。
- 勝ち筋は7つ：**データ、蒸留、アーキテクチャ、圧縮、推論、外部記憶、専門化**。評価は8つ目の「勝ちの測り方」。
- 一番効くのは**データと蒸留**。次に**ハイブリッド注意**と**量子化**。投機的デコードは「最後の2倍」だが、小さなモデルでは逆効果になり得る。
- **「1.58-bit」は魔法ではない。** 実ファイルは1.75〜1.82 bit/weight。スケール、F32テンソル、メタデータを含むため。
- **「小さなモデルがGPT-4を超えた」の9割は比較のインチキ。** 古いGPT-4、狭いベンチ、ベンダー評価、汚染、テスト時計算の差を確認する。
- 実務の正解は、1つのモデルではなく**ルーター＋小型＋大型＋検証器＋ツール**のシステム。

---

## 収録内容

| パス | 内容 |
|---|---|
| [`REPORT.md`](REPORT.md) | 本編（第0〜21章 + 付録A〜F） |
| [`MOBILE-SLM.md`](MOBILE-SLM.md) | モバイル編（iPhone / Android の要件差、モデル別フィット、量子化、KV、熱、配布） |
| [`GEMMA4-TERNARY-MOBILE.md`](GEMMA4-TERNARY-MOBILE.md) | Gemma 4 編（E2B〜31B、三値化、mobile QAT、iPhone / Android、日本語、roleplay 評価） |
| [`rea/analyze_gguf.py`](rea/analyze_gguf.py) | GGUF v3 パーサ + PTQ1_0 ブロックデコーダ |
| [`rea/analyze_litertlm.py`](rea/analyze_litertlm.py) | `.litertlm` の FlatBuffer ヘッダー + TFLite テンソル解析 |
| [`rea/analyze_gemma4_safetensors.py`](rea/analyze_gemma4_safetensors.py) | Gemma 4 の safetensors ヘッダー集計 + 三値化誤差の実測 |
| [`rea/evidence/bonsai2b.json`](rea/evidence/bonsai2b.json) | 実モデルのメタデータ、テンソル一覧、ビット/パラメータ、KVキャッシュ計算 |
| [`rea/evidence/bonsai_4b_9b_header.json`](rea/evidence/bonsai_4b_9b_header.json) | Bonsai 4B/9B のGGUFヘッダー（HTTP Range解析） |
| [`rea/evidence/bonsai_4b_9b_header.md`](rea/evidence/bonsai_4b_9b_header.md) | 4B/9B のパラメータ、層、KV、ビット/パラメータ |
| [`rea/evidence/ptq1_block.md`](rea/evidence/ptq1_block.md) | 28バイト三元ブロックの逆解析メモ |
| [`rea/evidence/webgpu_trace.md`](rea/evidence/webgpu_trace.md) | WebGPU バンドルの静的解析メモ |
| [`research/facts.json`](research/facts.json) | 60+ の事実データベース（出典・判定・注記） |
| [`research/mobile_facts.json`](research/mobile_facts.json) | モバイル編の41の事実データベース |
| [`research/factcheck.md`](research/factcheck.md) | 3パスのファクトチェック記録 |
| [`research/mobile_factcheck.md`](research/mobile_factcheck.md) | モバイル編の3パス・ファクトチェック |
| [`research/gemma4_facts.json`](research/gemma4_facts.json) | Gemma 4 編の186の事実データベース |
| [`research/gemma4_factcheck.md`](research/gemma4_factcheck.md) | Gemma 4 編の3パス + 独立レビュー記録 |
| [`rea/evidence/gemma4_safetensors_breakdown.json`](rea/evidence/gemma4_safetensors_breakdown.json) | 5モデルのパラメータ内訳（safetensors ヘッダー） |
| [`rea/evidence/gemma4_qat_gguf.json`](rea/evidence/gemma4_qat_gguf.json) | QAT Q4_0 GGUF のテンソル型・パラメータ・サイズ |
| [`rea/evidence/gemma4_litertlm_quantization.json`](rea/evidence/gemma4_litertlm_quantization.json) | E2B/E4B の `.litertlm` コンポーネント別実効 bpw |
| [`rea/evidence/gemma4_litertlm_12b_quantization.json`](rea/evidence/gemma4_litertlm_12b_quantization.json) | 12B の INT4 バンドル解析 |
| [`rea/evidence/gemma4_ternary_error.json`](rea/evidence/gemma4_ternary_error.json) | 三値化の重み空間誤差（実測） |
| [`rea/evidence/gemma4_mobile_fit.json`](rea/evidence/gemma4_mobile_fit.json) | Gemma 4 のメモリ/KV/フィット表 |
| [`rea/evidence/gemma4_tokenizer.json`](rea/evidence/gemma4_tokenizer.json) | 日本語トークナイザ + chat template の実験結果 |
| [`research/papers/`](research/papers) | 一次資料のPDF/テキスト（主要30本） |
| [`docs/references.md`](docs/references.md) | 完全な参考文献 |
| [`experiments/mobile_requirements.py`](experiments/mobile_requirements.py) | モバイルSLMのメモリ/KV/帯域/フィット計算 + グラフ生成 |
| [`experiments/gemma4_mobile.py`](experiments/gemma4_mobile.py) | Gemma 4 のメモリ/KV/フィット + 9枚のグラフ生成 |
| [`experiments/gemma4_tokenizer.py`](experiments/gemma4_tokenizer.py) | 日本語トークナイザ + Gemma 4 chat template の実験 |
| [`experiments/tokenizer_fertility.py`](experiments/tokenizer_fertility.py) | 日本語トークン効率の実験 |
| [`experiments/cost_calculator.py`](experiments/cost_calculator.py) | API vs 自前ホストのコスト計算 |

---

## 実物の逆解析でわかったこと

対象: `Ternary-Bonsai-2-2B-PTQ1_0.gguf`（429,183,456 bytes、SHA-256 `36061ad406df8a4903a6db005be350c50fabfaf717f9ef0acf4b76adcd9929fa`）

- **1.88B パラメータ、320テンソル、49メタデータ。**
- **151個の PTQ1_0 テンソル**（1,880,096,768 params、1.75 bit/weight）と、**169個の F32 テンソル**（1,728,320 params、正規化・SSM状態パス）。
- **ファイル全体で 1.8245 bit/param**。テンソル平均は 1.7778。三元の理論値 1.585 との差は、スケール・F32・メタデータ。
- **24層、18線形注意 + 6全注意**（Qwen3.5-2B の 3:1 ハイブリッド）。
- **262,144 コンテキスト**。ただし FP16 KV キャッシュは 262K で 3.0GiB（全層全注意なら 12.0GiB）。32K なら 0.375GiB。
- **248,320 語彙**、247,587 マージ。埋め込みは 508.6M（27.0%）。
- **PTQ1_0 の 28バイトブロック** = 24B base-3（5 trits/byte）+ 2B 2-bit（4 trits/byte）+ FP16 scale。
- **Hadamard 回転**（block 512）をモデルメタデータと WebGPU シェーダの両方で確認。
- **2B では投機的デコードを搭載していない**（WebGPU の `specDecodeRunner()` も `null`）。小さなターゲットでは逆効果、というベンダーの説明と一致。
- **4B/9B のヘッダーもHTTP Rangeで解析。** 4Bは4,205,751,296 params、9Bは8,953,803,264 params。どちらも32層・8全注意・4 KVヘッドで、**32KiB/token、262Kで8.0GiBのKV**。モバイル編のフィット表の根拠です。

> これは**構造の観測**であり、品質・速度の独立再現ではありません。ベンチマーク主張はベンダー主張として扱っています。

---

## クイックスタート

```bash
# GGUF の解析（モデルファイルを用意）
python rea/analyze_gguf.py path/to/Ternary-Bonsai-2-2B-PTQ1_0.gguf \
  --json rea/evidence/bonsai2b.json --blocks 2000

# モバイルSLMの要件計算 + グラフ
python experiments/mobile_requirements.py \
  --json rea/evidence/mobile_requirements.json --charts assets

# Gemma 4 のメモリ/KV/フィット表 + 9枚のグラフ
python experiments/gemma4_mobile.py \
  --json rea/evidence/gemma4_mobile_fit.json --charts assets

# Gemma 4 の日本語トークナイザ + chat template（tokenizer.json が必要）
python experiments/gemma4_tokenizer.py \
  --tokenizers research/tokenizers --json rea/evidence/gemma4_tokenizer.json

# .litertlm のヘッダー + TFLite テンソル（HTTP Range）
python rea/analyze_litertlm.py \
  --url https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it-gpu.litertlm \
  --json rea/evidence/gemma4_litertlm_header.json

# Gemma 4 の safetensors ヘッダー集計 + 三値化誤差
python rea/analyze_gemma4_safetensors.py \
  --url https://huggingface.co/google/gemma-4-E2B-it/resolve/main/model.safetensors \
  --json rea/evidence/gemma4_safetensors_breakdown.json

# 日本語トークン効率の実験（tokenizer.json が必要）
python experiments/tokenizer_fertility.py

# コスト計算
python experiments/cost_calculator.py --requests 1000000 --in 1000 --out 300
```

---

## 読み方

### 本編（REPORT.md）

- **10分:** 第0章 → 第1章 → 第2章 → 第12章 → 付録F
- **90分:** 第0〜8章 + 第11〜12章 + 第16章
- **徹底:** 全部。第13〜15章が実物の逆解析、付録Dがファクトチェック。

### モバイル編（MOBILE-SLM.md）

- **10分:** 第0章 → 第2章 → 第5章 → 第6章 → 付録F
- **90分:** 第0〜9章 + 第11章
- **徹底:** 全部。第7章の量子化、第8章のKV、付録Eの再現方法が核心。

### Gemma 4 編（GEMMA4-TERNARY-MOBILE.md）

- **10分:** 第0章 → 第2章 → 第6章 → 第8章 → 付録F
- **90分:** 第0〜11章 + 第13章
- **徹底:** 全部。第4章の実物解析、第5.7節の三値化誤差、第6章のフィット表、第11章のQAT比較、第12章のQATレシピが核心。

---

## 事実ラベル

- **【観測】** 実ファイル・バイト列・配布物から直接確認。
- **【導出】** 観測値からの計算。
- **【論文】** 一次資料（arXiv・技術レポート）。
- **【公式】** モデルカード・ライセンス・公式ドキュメントの記載。
- **【ベンダー主張】** 提供元の自己申告。独立再現なし。
- **【ベンダー自己測定】** 提供元が自社環境で測ったベンチマーク。
- **【デバイス仕様】** SoC・RAM・帯域などの公表仕様。
- **【経験則】** 計画に使う経験値。OS の公式上限ではない。
- **【推測】** 根拠はあるが断定できない。
- **【未検証】** 未確認。断定禁止。

---

## 限界

- ベンチマークの独立再現はしていません。一次資料の報告値を引用しています。
- モデルの品質・速度は測定していません。ファイル構造とメタデータの観測です。
- WebGPU バンドルは実行していません。静的解析のみです。
- 日本語トークン効率は8サンプルの参考値です。
- Gemma 4 の実機ベンチマークは未実施です。速度・メモリ・熱はベンダー値と計画値です。
- Gemma 4 の三値モデルは未訓練です。品質は重み空間の誤差と外部論文からの推定です。
- Gemma 4 の roleplay 人手評価は未実施です。第13章は評価設計の提案です。
- APK の Java/native 逆コンパイルは未完了です（JADX / Ghidra 未設定）。
- ベンダー主張（Bonsai、Phi、Gemma、Llama、Qwen、BitNet など）は、各提供元の自己申告です。

追試・訂正・Issue を歓迎します。

---

## ライセンス

- 本文: CC BY 4.0
- コード: MIT
- 引用した論文・モデルカード・ブログの権利は、各権利者に帰属します。
