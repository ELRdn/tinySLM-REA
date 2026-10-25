#!/usr/bin/env python3
"""Japanese tokenizer fertility and Gemma 4 chat-template overhead.

Inputs (not committed; download from Hugging Face):
  research/tokenizers/gemma4__tokenizer.json      google/gemma-4-E2B-it
  research/tokenizers/gemma3__tokenizer.json      unsloth/gemma-3-4b-it
  research/tokenizers/qwen3.5__tokenizer.json     Qwen/Qwen3.5-2B
  research/tokenizers/llama3.2__tokenizer.json    unsloth/Llama-3.2-1B-Instruct
  research/tokenizers/llmjp__tokenizer.json       llm-jp/llm-jp-3-3.7b-instruct

Usage:
    python experiments/gemma4_tokenizer.py \
      --tokenizers research/tokenizers \
      --json rea/evidence/gemma4_tokenizer.json

The eight samples are original text written for this report. They are short
by design: the result is a *relative* comparison, not a corpus estimate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SAMPLES = {
    "keigo": "お客様のご注文内容を確認いたしました。恐れ入りますが、ご登録のメールアドレスに届いた確認リンクを再度クリックしていただけますでしょうか。",
    "roleplay": "「……どうして、そんなに優しいの？　私、あなたに何も返せないのに」\n彼女は俯いたまま、震える声でそう言った。窓の外では、雨が静かに降り続いている。",
    "emotion": "嬉しいけれど、素直に喜べない。だって、その笑顔はきっと、私に向けたものじゃないから。",
    "names": "葛城美咲さん、本条薫様、藤堂院華子お嬢様。",
    "code_switch": "このAPIのrate limit、ちょっと厳しすぎない？　Retry-Afterを見てから、exponential backoffで再試行しよう。",
    "onomatopoeia": "どきどき、わくわく、ふわふわ、ざわざわ、しんみり、じんわり。",
    "prose": "夜明け前の街は、まだ眠っているように見えた。街灯の光が濡れた路面に溶け、遠くの踏切の音だけが、静かに響いている。",
    "system": "あなたは落ち着いた口調で話す執事です。敬語を保ち、相手の感情に寄り添いながら、簡潔に答えてください。",
}

PERSONA = SAMPLES["system"]
# A single 73-character roleplay turn, matching the report's template table.
USER = "「……どうして、そんなに優しいの？　私、あなたに何も返せないのに」\n彼女は俯いたまま、震える声でそう言った。"
ASSISTANT = "「お嬢様が、何かを返そうとお考えになる必要はございません。ただ、今この瞬間に、あなたがここにいてくださること。それだけで、私には十分でございます」"


def load_tokenizers(base: Path) -> dict:
    from tokenizers import Tokenizer
    out = {}
    for tag in ("gemma4", "gemma3", "qwen3.5", "llama3.2", "llmjp"):
        p = base / f"{tag}__tokenizer.json"
        if p.exists():
            out[tag] = Tokenizer.from_file(str(p))
    return out


def fertility(tok: dict) -> dict:
    per_sample = {}
    for name, text in SAMPLES.items():
        row = {}
        for tag, t in tok.items():
            ids = t.encode(text, add_special_tokens=False).ids
            row[tag] = {
                "tokens": len(ids),
                "chars": len(text),
                "tokens_per_100_chars": round(len(ids) * 100 / max(1, len(text)), 1),
            }
        per_sample[name] = row
    aggregate = {}
    for tag in tok:
        total_tokens = sum(r[tag]["tokens"] for r in per_sample.values())
        total_chars = sum(r[tag]["chars"] for r in per_sample.values())
        aggregate[tag] = {
            "tokens": total_tokens,
            "chars": total_chars,
            "tokens_per_100_chars": round(total_tokens * 100 / total_chars, 1),
        }
    return {"per_sample": per_sample, "aggregate": aggregate}


def template_overhead(tok_dir: Path) -> dict:
    from jinja2 import Environment
    from tokenizers import Tokenizer

    tpl_path = ROOT / "research" / "gemma4" / "gemma-4-E2B-it__chat_template.jinja"
    tok_path = tok_dir / "gemma4__tokenizer.json"
    if not tpl_path.exists() or not tok_path.exists():
        return {}
    tpl = tpl_path.read_text(encoding="utf-8")
    tok = Tokenizer.from_file(str(tok_path))
    env = Environment(trim_blocks=False, lstrip_blocks=False)
    # The canonical template uses tojson for tool arguments; not needed here,
    # but register it so rendering never fails on a tool branch.
    env.filters["tojson"] = lambda x: json.dumps(x, ensure_ascii=False)

    def render(messages):
        t = env.from_string(tpl)
        return t.render(messages=messages, add_generation_prompt=True,
                        enable_thinking=False, preserve_thinking=False,
                        bos_token="<bos>", eos_token="<eos>")

    rows = []
    for turns in (1, 5, 10, 20):
        msgs = [{"role": "system", "content": PERSONA}]
        for _ in range(turns):
            msgs.append({"role": "user", "content": USER})
            msgs.append({"role": "assistant", "content": ASSISTANT})
        msgs.append({"role": "user", "content": "……ありがとう。もう少しだけ、そばにいてくれる？"})
        rendered = render(msgs)
        n = len(tok.encode(rendered, add_special_tokens=False).ids)
        raw = "".join(m["content"] for m in msgs)
        raw_n = len(tok.encode(raw, add_special_tokens=False).ids)
        rows.append({
            "turns": turns,
            "rendered_chars": len(rendered),
            "rendered_tokens": n,
            "raw_chars": len(raw),
            "raw_tokens": raw_n,
            "overhead_tokens": n - raw_n,
            "overhead_pct": round((n - raw_n) * 100 / max(1, raw_n), 1),
        })
    return {"rows": rows, "sample_rendered": render([
        {"role": "system", "content": PERSONA},
        {"role": "user", "content": USER},
    ])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokenizers", type=Path,
                    default=ROOT / "research" / "tokenizers")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "rea" / "evidence" / "gemma4_tokenizer.json")
    args = ap.parse_args()

    tok = load_tokenizers(args.tokenizers)
    if not tok:
        raise SystemExit(f"no tokenizer.json found under {args.tokenizers}")
    data = {
        "schema": "tinySLM-REA/gemma4-tokenizer-v1",
        "date": "2026-10-25",
        "samples": len(SAMPLES),
        "tokenizers": fertility(tok),
        "chat_template": template_overhead(args.tokenizers),
        "notes": [
            "Eight short samples; use for relative comparison, not corpus estimates.",
            "Gemma 4 and Gemma 3 share the same tokenizer in this test.",
            "Chat-template overhead uses the canonical Gemma 4 template, enable_thinking=false.",
        ],
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.json}")
    print("aggregate tokens/100 chars:",
          {k: v["tokens_per_100_chars"] for k, v in data["tokenizers"]["aggregate"].items()})
    if data["chat_template"]:
        print("template overhead:",
              [(r["turns"], r["overhead_pct"]) for r in data["chat_template"]["rows"]])


if __name__ == "__main__":
    main()
