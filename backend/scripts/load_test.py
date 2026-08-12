#!/usr/bin/env python3
"""
Load-test script for the Masar Adaptive Assessment API.

Uses httpx.AsyncClient to send concurrent requests and measures:
  - Requests per second (RPS)
  - Latency percentiles (p50, p90, p95, p99)
  - Min / Max / Mean latency
  - Error rate

Usage:
    python scripts/load_test.py --url http://127.0.0.1:8000
    python scripts/load_test.py --url http://127.0.0.1:8000 --concurrency 20 --requests 200
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field

import httpx


# ── Endpoints to test ──────────────────────────────────────────────────────────

ENDPOINTS = [
    {"method": "GET", "path": "/admin/sessions",    "label": "GET /admin/sessions"},
    {"method": "GET", "path": "/admin/assessments",  "label": "GET /admin/assessments"},
    {"method": "GET", "path": "/health",             "label": "GET /health"},
]


@dataclass
class RequestResult:
    status: int
    latency_ms: float
    error: str | None = None


@dataclass
class EndpointReport:
    label: str
    results: list[RequestResult] = field(default_factory=list)

    @property
    def latencies(self) -> list[float]:
        return [r.latency_ms for r in self.results if r.error is None]

    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.error is not None or r.status >= 400)

    def summary(self) -> dict:
        lats = self.latencies
        if not lats:
            return {"label": self.label, "total": len(self.results), "errors": self.errors, "note": "no successful requests"}
        lats_sorted = sorted(lats)
        n = len(lats_sorted)
        total_time_s = sum(lats) / 1000
        return {
            "label": self.label,
            "total_requests": len(self.results),
            "successful": n,
            "errors": self.errors,
            "rps": round(n / total_time_s, 2) if total_time_s > 0 else 0,
            "mean_ms": round(statistics.mean(lats), 1),
            "min_ms": round(min(lats), 1),
            "max_ms": round(max(lats), 1),
            "p50_ms": round(lats_sorted[int(n * 0.50)], 1),
            "p90_ms": round(lats_sorted[int(n * 0.90)], 1),
            "p95_ms": round(lats_sorted[int(n * 0.95)], 1),
            "p99_ms": round(lats_sorted[min(int(n * 0.99), n - 1)], 1),
        }


async def _fire_one(client: httpx.AsyncClient, method: str, url: str) -> RequestResult:
    start = time.perf_counter()
    try:
        resp = await client.request(method, url)
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(status=resp.status_code, latency_ms=elapsed)
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RequestResult(status=0, latency_ms=elapsed, error=str(exc))


async def _load_test_endpoint(
    base_url: str,
    endpoint: dict,
    concurrency: int,
    total_requests: int,
) -> EndpointReport:
    report = EndpointReport(label=endpoint["label"])
    sem = asyncio.Semaphore(concurrency)
    url = f"{base_url}{endpoint['path']}"
    method = endpoint["method"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        async def _bounded():
            async with sem:
                return await _fire_one(client, method, url)

        tasks = [asyncio.create_task(_bounded()) for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)
        report.results = list(results)

    return report


async def run_load_tests(base_url: str, concurrency: int, total_requests: int) -> list[dict]:
    print(f"\n{'='*60}")
    print(f"  Load Test — {base_url}")
    print(f"  Concurrency: {concurrency}  |  Requests per endpoint: {total_requests}")
    print(f"{'='*60}\n")

    summaries = []
    for ep in ENDPOINTS:
        print(f"  ▶ {ep['label']} ...", end="", flush=True)
        report = await _load_test_endpoint(base_url, ep, concurrency, total_requests)
        s = report.summary()
        summaries.append(s)
        rps = s.get("rps", "N/A")
        p50 = s.get("p50_ms", "N/A")
        p95 = s.get("p95_ms", "N/A")
        errs = s.get("errors", 0)
        print(f"  RPS={rps}  p50={p50}ms  p95={p95}ms  errors={errs}")

    print(f"\n{'='*60}")
    print("  Full results (JSON):")
    print(json.dumps(summaries, indent=2))
    print(f"{'='*60}\n")
    return summaries


def main():
    parser = argparse.ArgumentParser(description="Load-test the Masar API")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of the API")
    parser.add_argument("--concurrency", "-c", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--requests", "-n", type=int, default=50, help="Total requests per endpoint")
    args = parser.parse_args()

    asyncio.run(run_load_tests(args.url, args.concurrency, args.requests))


if __name__ == "__main__":
    main()
