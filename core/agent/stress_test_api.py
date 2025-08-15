import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple

import urllib.request
import urllib.error


def send_request(
    request_id: int, url: str, message: str, timeout_s: float
) -> Tuple[int, int, float, str, Optional[str], Optional[str]]:
    """Send one POST request and return (id, status, latency_s, body, timings_header, error)."""
    payload = {"messages": [{"role": "user", "content": message}]}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            latency = time.perf_counter() - start
            status = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
            timings = resp.headers.get("X-Luna-Timings")
            return request_id, status, latency, body, timings, None
    except urllib.error.HTTPError as e:
        latency = time.perf_counter() - start
        body = e.read().decode("utf-8", errors="replace")
        timings = e.headers.get("X-Luna-Timings") if e.headers else None
        return request_id, e.code, latency, body, timings, f"HTTPError: {e}"
    except Exception as e:  # URLError / timeout / other
        latency = time.perf_counter() - start
        return request_id, 0, latency, "", None, f"ERROR: {e}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Stress test the Luna OpenAI-compatible API")
    parser.add_argument("--host", default=os.environ.get("API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("API_PORT", "8010")))
    parser.add_argument("--num", type=int, default=20, help="Total requests to send")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent worker threads")
    parser.add_argument("--message", default="say hello", help="User message to send")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout seconds")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/v1/chat/completions"
    print(f"Target: {url}")
    print(f"Requests: {args.num}, Concurrency: {args.concurrency}, Message: {args.message!r}")

    wall_start = time.perf_counter()
    latencies: list[float] = []
    successes = 0
    failures = 0

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(send_request, i + 1, url, args.message, args.timeout)
            for i in range(args.num)
        ]
        for fut in as_completed(futures):
            req_id, status, latency, body, timings, error = fut.result()
            latencies.append(latency)
            if error or status != 200:
                failures += 1
                print(
                    f"[done] #{req_id} {latency:.3f}s status={status} ERROR={error or body[:200]}"
                )
            else:
                successes += 1
                preview = body.strip().replace("\n", " ")
                if len(preview) > 120:
                    preview = preview[:117] + "..."
                print(f"[done] #{req_id} {latency:.3f}s status=200 body={preview}")

    wall_total = time.perf_counter() - wall_start
    avg = (sum(latencies) / len(latencies)) if latencies else 0.0
    print()
    print(f"successes={successes} failures={failures}")
    print(f"avg_latency_s={avg:.3f} total_wall_s={wall_total:.3f}")


if __name__ == "__main__":
    main()


