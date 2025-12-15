"""
Performance Test for Parallel Processing Implementation
Tests the batch analysis endpoint and measures processing time.
"""

import time
import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"
BATCH_ENDPOINT = f"{BASE_URL}/api/analyze-batch"

# Test with different batch sizes
test_cases = [
    {
        "name": "Small Batch (5 tickers)",
        "tickers": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL"]
    },
    {
        "name": "Medium Batch (10 tickers)",
        "tickers": ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC"]
    },
    {
        "name": "Large Batch (24 tickers - Full Watchlist)",
        "tickers": [
            "TSLL", "NVDA", "SMCI", "BBAI", "OPEN", "SOFI", "PLTR", "GDXU",
            "TEM", "COIN", "QBTS", "RGTI", "QUBT", "INTC", "MARA", "AMD",
            "RIOT", "APLD", "MU", "FUTU", "HOOD", "MSTR", "TSLA", "AAPL"
        ]
    }
]

def test_batch_analysis(test_case):
    """Test batch analysis and measure performance."""
    print(f"\n{'='*70}")
    print(f"Testing: {test_case['name']}")
    print(f"Tickers: {len(test_case['tickers'])}")
    print(f"{'='*70}")
    
    # Prepare request
    payload = {"tickers": test_case["tickers"]}
    
    # Measure time
    start_time = time.time()
    
    try:
        response = requests.post(
            BATCH_ENDPOINT,
            json=payload,
            timeout=120  # 2 minute timeout
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Check response
        if response.status_code == 200:
            results = response.json()
            
            # Count successes and errors
            successes = sum(1 for r in results if "error" not in r)
            errors = sum(1 for r in results if "error" in r)
            
            print(f"\n✅ SUCCESS")
            print(f"   Total time: {elapsed:.2f} seconds")
            print(f"   Average per ticker: {elapsed / len(test_case['tickers']):.2f} seconds")
            print(f"   Successful: {successes}/{len(test_case['tickers'])}")
            print(f"   Errors: {errors}/{len(test_case['tickers'])}")
            
            # Show error details if any
            if errors > 0:
                print(f"\n   Error details:")
                for r in results:
                    if "error" in r:
                        print(f"   - {r['symbol']}: {r['error']}")
            
            # Performance rating
            expected_sequential = len(test_case['tickers']) * 2.5  # Assume 2.5s per ticker
            speedup = expected_sequential / elapsed
            print(f"\n   📊 Performance Analysis:")
            print(f"   Expected (sequential): ~{expected_sequential:.1f}s")
            print(f"   Actual (parallel): {elapsed:.2f}s")
            print(f"   Speedup: {speedup:.1f}x faster")
            
            return {
                "success": True,
                "elapsed": elapsed,
                "speedup": speedup,
                "successes": successes,
                "errors": errors
            }
        else:
            print(f"\n❌ FAILED")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return {"success": False}
            
    except requests.exceptions.Timeout:
        print(f"\n❌ TIMEOUT")
        print(f"   Request timed out after 120 seconds")
        return {"success": False}
    except Exception as e:
        print(f"\n❌ ERROR")
        print(f"   Exception: {str(e)}")
        return {"success": False}

def main():
    """Run all performance tests."""
    print("\n" + "="*70)
    print("PARALLEL PROCESSING PERFORMANCE TEST")
    print("="*70)
    print("\nThis test will measure the performance improvement from parallel processing.")
    print("Expected improvement: 5-7x faster than sequential processing")
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL, timeout=5)
        print(f"\n✅ Server is running at {BASE_URL}")
    except:
        print(f"\n❌ ERROR: Server is not running at {BASE_URL}")
        print("Please start the server with: python backend/main.py")
        return
    
    # Run all test cases
    results = []
    for test_case in test_cases:
        result = test_batch_analysis(test_case)
        results.append({
            "name": test_case["name"],
            "ticker_count": len(test_case["tickers"]),
            **result
        })
        
        # Wait between tests to avoid overwhelming the API
        if test_case != test_cases[-1]:
            print("\nWaiting 3 seconds before next test...")
            time.sleep(3)
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    successful_tests = [r for r in results if r.get("success")]
    
    if successful_tests:
        avg_speedup = sum(r["speedup"] for r in successful_tests) / len(successful_tests)
        print(f"\n✅ All tests completed!")
        print(f"   Average speedup: {avg_speedup:.1f}x faster")
        print(f"   Tests passed: {len(successful_tests)}/{len(results)}")
        
        print(f"\n📊 Detailed Results:")
        for r in results:
            if r.get("success"):
                print(f"   {r['name']}: {r['elapsed']:.2f}s ({r['speedup']:.1f}x speedup)")
    else:
        print(f"\n❌ Some tests failed. Please check the output above.")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()
