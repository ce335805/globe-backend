#!/usr/bin/env python3
"""
Rate limit test script for arXiv Globe Backend.

Tests that the /papers/by-category endpoint correctly enforces
the 20 requests/minute rate limit per IP address.
"""

import httpx
import time
from datetime import datetime


def test_rate_limit(base_url: str = "http://localhost:8000", num_requests: int = 25):
    """
    Test rate limiting by making rapid requests.

    Args:
        base_url: Backend URL
        num_requests: Number of requests to make (should exceed limit)
    """
    print(f"Testing rate limit at {base_url}")
    print(f"Making {num_requests} requests (limit is 20/minute)")
    print("-" * 60)

    success_count = 0
    rate_limited_count = 0

    client = httpx.Client(timeout=10.0)

    for i in range(1, num_requests + 1):
        try:
            start_time = time.time()
            response = client.get(
                f"{base_url}/papers/by-category",
                params={"category": "cs.AI", "index": 0}
            )
            elapsed = time.time() - start_time

            timestamp = datetime.now().strftime("%H:%M:%S")

            if response.status_code == 200:
                success_count += 1
                print(f"[{timestamp}] Request {i:2d}: ✓ 200 OK ({elapsed:.1f}s)")
            elif response.status_code == 429:
                rate_limited_count += 1
                print(f"[{timestamp}] Request {i:2d}: ✗ 429 RATE LIMITED")
            else:
                print(f"[{timestamp}] Request {i:2d}: ? {response.status_code}")

        except httpx.RequestError as e:
            print(f"Request {i:2d}: ERROR - {e}")
        except Exception as e:
            print(f"Request {i:2d}: UNEXPECTED ERROR - {e}")

    client.close()

    print("-" * 60)
    print(f"Results:")
    print(f"  Success (200):      {success_count}")
    print(f"  Rate Limited (429): {rate_limited_count}")
    print(f"  Expected:           20 success, {num_requests - 20} rate limited")
    print()

    if success_count <= 20 and rate_limited_count >= num_requests - 20:
        print("✓ Rate limiting working correctly!")
    else:
        print("✗ Rate limiting may not be working as expected")


def test_rate_limit_reset(base_url: str = "http://localhost:8000"):
    """
    Test that rate limit resets after 1 minute.
    """
    print("\nTesting rate limit reset...")
    print("Making 21 requests, waiting 60s, then trying again")
    print("-" * 60)

    client = httpx.Client(timeout=10.0)

    # First batch - should hit rate limit
    print("First batch (should hit limit at request 21):")
    for i in range(1, 22):
        try:
            response = client.get(
                f"{base_url}/papers/by-category",
                params={"category": "cs.AI", "index": 0}
            )
            status = "✓" if response.status_code == 200 else "✗"
            print(f"  Request {i:2d}: {status} {response.status_code}")
        except Exception as e:
            print(f"  Request {i:2d}: ERROR - {e}")

    # Wait for reset
    print("\nWaiting 60 seconds for rate limit to reset...")
    for remaining in range(60, 0, -10):
        print(f"  {remaining} seconds remaining...")
        time.sleep(10)

    # Second batch - should work again
    print("\nSecond batch (should work after reset):")
    for i in range(1, 6):
        try:
            response = client.get(
                f"{base_url}/papers/by-category",
                params={"category": "cs.AI", "index": 0}
            )
            status = "✓" if response.status_code == 200 else "✗"
            print(f"  Request {i}: {status} {response.status_code}")
        except Exception as e:
            print(f"  Request {i}: ERROR - {e}")

    client.close()
    print("\n✓ Rate limit reset test complete")


if __name__ == "__main__":
    import sys

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    print("arXiv Globe Backend - Rate Limit Test")
    print("=" * 60)

    # Quick test - just verify the limit works
    test_rate_limit(base_url, num_requests=25)

    # Uncomment to test reset behavior (takes 60+ seconds)
    test_rate_limit_reset(base_url)
