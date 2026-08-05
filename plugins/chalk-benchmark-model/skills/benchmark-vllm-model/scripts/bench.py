#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""Sustained-throughput benchmark for an OpenAI-compatible vLLM endpoint.

Measures server-side throughput from vLLM's own Prometheus counters over a
fixed steady-state window, so client-side jitter and ramp-up are excluded.

Usage:
    ./bench.py --base-url http://10.12.25.26:8000 --model my/model
    ./bench.py --base-url https://... --model my/model \
        --input-lens 139,554 --concurrency 8,32,64 --duration 30 --output-tokens 1

Emits a table plus a JSON blob suitable for feeding into a cost calculation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time

import httpx

FILLER = ("The user described their weekend plans and asked several follow up "
          "questions about local restaurants, travel logistics, and weather. ")


def build_prompt(target_tokens: int, seed: int) -> str:
    """Roughly `target_tokens` tokens, with a unique prefix per request.

    The unique `seed` prefix is deliberate: without it every request shares a
    full prefix and vLLM's prefix cache returns nearly everything, which makes
    throughput look far better than it is.
    """
    words = max(1, int(target_tokens * 0.75))
    body = (FILLER * (words // 15 + 1)).split()[:words]
    return f"request-{seed}: " + " ".join(body)


def payload(model: str, prompt: str, out_tokens: int, system: str | None,
            logprobs: bool) -> dict:
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body: dict = {"model": model, "messages": messages,
                  "max_tokens": out_tokens, "temperature": 0.0}
    if logprobs:
        body.update({"logprobs": True, "top_logprobs": 20})
    return body


async def read_counters(client: httpx.AsyncClient, base: str) -> dict[str, float]:
    r = await client.get(f"{base}/metrics", timeout=30)

    def total(name: str) -> float:
        m = re.findall(rf"^{re.escape(name)}\{{[^}}]*}}\s+([0-9.e+]+)$", r.text, re.M)
        return sum(float(x) for x in m) if m else 0.0

    return {
        "prompt_tokens": total("vllm:prompt_tokens_total"),
        "generation_tokens": total("vllm:generation_tokens_total"),
        "requests": total("vllm:request_success_total"),
        "cache_queries": total("vllm:prefix_cache_queries_total"),
        "cache_hits": total("vllm:prefix_cache_hits_total"),
    }


async def run_point(args, input_len: int, concurrency: int) -> dict:
    limits = httpx.Limits(max_connections=concurrency + 20)
    headers = {"Authorization": f"Bearer {args.api_key}"} if args.api_key else {}

    async with httpx.AsyncClient(limits=limits, headers=headers) as client:
        for _ in range(3):  # warm weights / CUDA graphs
            await client.post(f"{args.base_url}/v1/chat/completions",
                              json=payload(args.model, build_prompt(input_len, -1),
                                           args.output_tokens, args.system,
                                           args.logprobs),
                              timeout=180)

        stop = asyncio.Event()
        counter = 0
        lock = asyncio.Lock()

        async def worker() -> None:
            nonlocal counter
            while not stop.is_set():
                async with lock:
                    counter += 1
                    seed = counter
                try:
                    await client.post(
                        f"{args.base_url}/v1/chat/completions",
                        json=payload(args.model, build_prompt(input_len, seed),
                                     args.output_tokens, args.system, args.logprobs),
                        timeout=300)
                except Exception:
                    pass

        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
        await asyncio.sleep(args.ramp)                 # reach steady state
        before = await read_counters(client, args.base_url)
        t0 = time.perf_counter()
        await asyncio.sleep(args.duration)             # measured window
        after = await read_counters(client, args.base_url)
        elapsed = time.perf_counter() - t0

        stop.set()
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    d = {k: after[k] - before[k] for k in after}
    cache_rate = (d["cache_hits"] / d["cache_queries"]) if d["cache_queries"] else 0.0
    return {
        "input_len": input_len, "concurrency": concurrency, "window_s": elapsed,
        "requests": d["requests"], "prompt_tokens": d["prompt_tokens"],
        "generation_tokens": d["generation_tokens"],
        "rps": d["requests"] / elapsed,
        "prompt_tok_per_s": d["prompt_tokens"] / elapsed,
        "gen_tok_per_s": d["generation_tokens"] / elapsed,
        "prefix_cache_hit_rate": cache_rate,
    }


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default=None)
    p.add_argument("--system", default=None, help="optional system prompt")
    p.add_argument("--input-lens", default="128,512",
                   help="comma-separated approx prompt token counts")
    p.add_argument("--concurrency", default="8,32,64",
                   help="comma-separated client concurrency levels")
    p.add_argument("--duration", type=float, default=30.0, help="measured window (s)")
    p.add_argument("--ramp", type=float, default=5.0, help="pre-window ramp (s)")
    p.add_argument("--output-tokens", type=int, default=1)
    p.add_argument("--logprobs", action="store_true",
                   help="request top_logprobs (classifier-style scoring)")
    args = p.parse_args()
    args.base_url = args.base_url.rstrip("/")

    lens = [int(x) for x in args.input_lens.split(",")]
    concs = [int(x) for x in args.concurrency.split(",")]

    print(f"{'in_tok':>7} {'conc':>5} {'win_s':>7} {'reqs':>7} {'req/s':>8} "
          f"{'ptok/s':>10} {'gtok/s':>8} {'cache%':>7}")
    results = []
    for n in lens:
        for c in concs:
            r = await run_point(args, n, c)
            results.append(r)
            print(f"{r['input_len']:>7} {r['concurrency']:>5} {r['window_s']:>7.1f} "
                  f"{r['requests']:>7.0f} {r['rps']:>8.1f} "
                  f"{r['prompt_tok_per_s']:>10.0f} {r['gen_tok_per_s']:>8.0f} "
                  f"{r['prefix_cache_hit_rate']*100:>6.1f}%")

    best = max(results, key=lambda r: r["prompt_tok_per_s"])
    print(f"\npeak prompt throughput: {best['prompt_tok_per_s']:.0f} tok/s "
          f"@ in_tok={best['input_len']} conc={best['concurrency']} "
          f"({best['rps']:.1f} req/s)")
    print("\nJSON:", json.dumps(results))


asyncio.run(main())
