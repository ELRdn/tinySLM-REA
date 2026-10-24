#!/usr/bin/env python3
"""Simple API vs self-host cost calculator.

Usage:
    python cost_calculator.py --requests 1000000 --in 1000 --out 300
    python cost_calculator.py --requests 1000000 --in 1000 --out 300 \
        --api-in 0.10 --api-out 0.30 --gpu-hour 2.0 --tok-s 2000

All prices are illustrative; replace with your own.
"""
from __future__ import annotations

import argparse


def api_cost(req, tin, tout, p_in, p_out):
    return req * (tin * p_in + tout * p_out) / 1e6


def self_host_cost(req, tout, gpu_hour, tok_s, gpu_count=1, utilization=1.0):
    # output-token throughput; assumes one request = tout output tokens
    seconds_per_req = tout / tok_s if tok_s else 0.0
    gpu_hours = req * seconds_per_req / 3600.0 / max(gpu_count * utilization, 1e-9)
    return gpu_hours * gpu_hour, gpu_hours


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=float, default=1_000_000, help="requests per day")
    ap.add_argument("--in", dest="tin", type=float, default=1000, help="input tokens per request")
    ap.add_argument("--out", dest="tout", type=float, default=300, help="output tokens per request")
    ap.add_argument("--api-in", type=float, default=0.10, help="$ per 1M input tokens")
    ap.add_argument("--api-out", type=float, default=0.30, help="$ per 1M output tokens")
    ap.add_argument("--gpu-hour", type=float, default=2.0, help="$ per GPU hour")
    ap.add_argument("--tok-s", type=float, default=2000, help="output tokens/s per GPU")
    ap.add_argument("--gpu-count", type=int, default=1)
    ap.add_argument("--utilization", type=float, default=1.0, help="0..1")
    args = ap.parse_args()

    a = api_cost(args.requests, args.tin, args.tout, args.api_in, args.api_out)
    s, gh = self_host_cost(args.requests, args.tout, args.gpu_hour, args.tok_s,
                           args.gpu_count, args.utilization)
    print(f"requests/day:       {args.requests:,.0f}")
    print(f"input/output:       {args.tin:,.0f} / {args.tout:,.0f} tokens")
    print(f"API cost/day:       ${a:,.2f}")
    print(f"self-host cost/day: ${s:,.2f}  ({gh:,.1f} GPU-hours)")
    print(f"API/self-host:      {a/s:,.2f}x" if s else "API/self-host: n/a")
    print("\nAssumptions: output-token throughput; no prefill, network, memory, or idle cost.")
    print("Prices are illustrative. Replace with your own.")


if __name__ == "__main__":
    main()
