"""
concurrent_rpm_test.py

Measure how many requests-per-minute an endpoint can handle.
Usage (defaults to 60 s, 20 workers):

    python concurrent_rpm_test.py \
        --url https://api-staging.dishpal.ai/api/geodiscounts/v1/discounts/categories/ \
        --concurrency 50 \
        --duration 120
"""
import argparse, asyncio, time, statistics, aiohttp, ssl, certifi
from collections import Counter

async def worker(session, url, deadline, stats):
    """Continuously hit `url` until `deadline` is reached."""
    while time.perf_counter() < deadline:
        start = time.perf_counter()
        try:
            async with session.get(url, timeout=10) as resp:
                await resp.read()                     # drain body
                elapsed = time.perf_counter() - start
                code = resp.status
        except Exception:
            code = "ERR"
            elapsed = time.perf_counter() - start
        # update shared counters
        stats["latencies"].append(elapsed)
        stats["codes"][code] += 1

async def run(url: str, concurrency: int, duration: int):
    deadline = time.perf_counter() + duration
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())  # avoid SSL errors
    stats = {"codes": Counter(), "latencies": []}

    conn = aiohttp.TCPConnector(limit=0, ssl=ssl_ctx)            # no per-host limit
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [asyncio.create_task(worker(session, url, deadline, stats))
                 for _ in range(concurrency)]
        await asyncio.gather(*tasks)

    total = sum(stats["codes"].values())
    ok = sum(v for k, v in stats["codes"].items() if isinstance(k, int) and 200 <= k < 300)
    rpm = total / (duration / 60)
    if stats["latencies"]:
        avg_lat = statistics.mean(stats["latencies"])
        p95_lat = statistics.quantiles(stats["latencies"], n=20)[18]   # 95th percentile
        worst = max(stats["latencies"])
    else:
        avg_lat = p95_lat = worst = 0

    print(f"\nFinished {duration}s test with {concurrency} workers")
    print(f"Total requests:      {total:,}")
    print(f"Successful (2xx):    {ok:,}")
    print(f"Requests per minute: {rpm:,.0f}")
    print(f"Avg latency:         {avg_lat*1e3:.1f} ms")
    print(f"95th percentile:     {p95_lat*1e3:.1f} ms")
    print(f"Worst:               {worst*1e3:.1f} ms")
    print("\nStatus-code breakdown:", dict(stats["codes"]))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://api-staging.dishpal.ai/api/geodiscounts/v1/discounts/categories/")
    parser.add_argument("--concurrency", "-c", type=int, default=20,
                        help="Number of simultaneous workers")
    parser.add_argument("--duration", "-d", type=int, default=60,
                        help="Length of test in seconds (default 60)")
    args = parser.parse_args()
    asyncio.run(run(args.url, args.concurrency, args.duration))

if __name__ == "__main__":
    main()

