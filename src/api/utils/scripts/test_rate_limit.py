"""
Rate limit test script.

Hammers endpoints to verify rate limiting is working.
Usage: python test_rate_limit.py <base_url>
Example: python test_rate_limit.py http://localhost:8000
         python test_rate_limit.py https://your-staging-url.run.app
"""

import sys
import time
import requests

def test_rate_limit(base_url, endpoint, num_requests=110, delay=0):
    """
    Send num_requests to an endpoint and report status codes.

    Args:
        base_url: e.g. "http://localhost:8000"
        endpoint: e.g. "/health/"
        num_requests: how many requests to send
        delay: seconds between requests (0 = as fast as possible)
    """
    url = f"{base_url}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {url}")
    print(f"Sending {num_requests} requests...")
    print(f"{'='*60}")

    results = {}
    first_429 = None

    for i in range(1, num_requests + 1):
        try:
            resp = requests.get(url, timeout=10)
            code = resp.status_code
            results[code] = results.get(code, 0) + 1

            if code == 429 and first_429 is None:
                first_429 = i
                print(f"  [{i:3d}] {code} <-- RATE LIMITED (first hit)")
            elif i % 20 == 0 or code == 429:
                print(f"  [{i:3d}] {code}")

            if delay:
                time.sleep(delay)

        except requests.exceptions.RequestException as e:
            print(f"  [{i:3d}] ERROR: {e}")
            results["error"] = results.get("error", 0) + 1

    print(f"\n--- Results ---")
    for code, count in sorted(results.items(), key=lambda x: str(x[0])):
        print(f"  {code}: {count} responses")
    if first_429:
        print(f"  Rate limited after request #{first_429}")
    else:
        print(f"  No rate limiting detected!")
    print()


def test_rate_limit_reset(base_url, endpoint):
    """Test that rate limit resets after waiting."""
    url = f"{base_url}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing rate limit reset: {url}")
    print(f"{'='*60}")

    # Burn through the limit
    print("  Burning through rate limit...")
    for i in range(105):
        requests.get(url, timeout=10)

    resp = requests.get(url, timeout=10)
    print(f"  After 105 requests: {resp.status_code}")

    # Wait and try again
    print("  Waiting 61 seconds for rate limit to reset...")
    time.sleep(61)

    resp = requests.get(url, timeout=10)
    print(f"  After waiting: {resp.status_code}")
    if resp.status_code != 429:
        print("  Rate limit reset successfully!")
    else:
        print("  Rate limit did NOT reset!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_rate_limit.py <base_url>")
        print("Example: python test_rate_limit.py http://localhost:8000")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    print(f"Base URL: {base_url}")

    # Test 1: Health endpoint (should be EXEMPT from rate limiting)
    test_rate_limit(base_url, "/health/", num_requests=110)

    # Test 2: Root endpoint (should be rate limited at 100/min)
    test_rate_limit(base_url, "/", num_requests=110)

    # Test 3: Verify 429 response format
    print(f"\n{'='*60}")
    print("Testing 429 response body format")
    print(f"{'='*60}")
    # Burn through limit on a different-ish path
    for i in range(105):
        requests.get(f"{base_url}/", timeout=10)
    resp = requests.get(f"{base_url}/", timeout=10)
    if resp.status_code == 429:
        print(f"  Status: {resp.status_code}")
        print(f"  Body: {resp.json()}")
    else:
        print(f"  Got {resp.status_code} instead of 429 — limit may not have kicked in")

    print("\nDone! Run with --reset flag to also test rate limit reset (takes ~60s)")
    if "--reset" in sys.argv:
        test_rate_limit_reset(base_url, "/")
