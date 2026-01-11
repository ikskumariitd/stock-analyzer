#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Stock Analyzer
Tests all API endpoints against both local and cloud environments.

Usage:
    python test_api_comprehensive.py              # Test local (default)
    python test_api_comprehensive.py --cloud      # Test cloud
    python test_api_comprehensive.py --both       # Test both environments
"""

import requests
import argparse
import time
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

# Configuration
LOCAL_URL = "http://localhost:8000"
CLOUD_URL = "https://stock-analyzer-641888119120.us-central1.run.app"

# Test ticker for most tests
TEST_TICKER = "AAPL"
TEST_TICKER_2 = "MSFT"


class TestStatus(Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    SKIP = "⏭️ SKIP"
    WARN = "⚠️ WARN"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration_ms: float
    message: str = ""
    response_preview: str = ""


class APITestSuite:
    def __init__(self, base_url: str, env_name: str = "local"):
        self.base_url = base_url.rstrip("/")
        self.env_name = env_name
        self.results: List[TestResult] = []
        self.timeout = 30  # seconds for normal endpoints
        self.timeout_heavy = 90  # seconds for heavy endpoints

    def _request(self, method: str, endpoint: str, **kwargs) -> tuple:
        """Make HTTP request and return (response, duration_ms)"""
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        
        start = time.time()
        try:
            response = requests.request(method, url, **kwargs)
            duration = (time.time() - start) * 1000
            return response, duration
        except requests.exceptions.RequestException as e:
            duration = (time.time() - start) * 1000
            return None, duration

    def _add_result(self, name: str, status: TestStatus, duration_ms: float, 
                    message: str = "", response_preview: str = ""):
        result = TestResult(name, status, duration_ms, message, response_preview)
        self.results.append(result)
        
        # Print immediately
        status_str = status.value
        time_str = f"({duration_ms:.0f}ms)"
        print(f"  {status_str} {name} {time_str}")
        if message:
            print(f"       └─ {message}")

    def test_health(self):
        """Test root endpoint health check"""
        resp, duration = self._request("GET", "/")
        if resp is None:
            self._add_result("Health Check", TestStatus.FAIL, duration, "Connection failed")
            return False
        if resp.status_code == 200:
            self._add_result("Health Check", TestStatus.PASS, duration)
            return True
        else:
            self._add_result("Health Check", TestStatus.FAIL, duration, f"Status: {resp.status_code}")
            return False

    # ========== Cache Endpoints ==========
    def test_cache_stats(self):
        """Test GET /api/cache/stats"""
        resp, duration = self._request("GET", "/api/cache/stats")
        if resp and resp.status_code == 200:
            data = resp.json()
            # API returns {"success": true, "stats": {...}, "backend": "GCS"}
            if data.get("success") and "stats" in data:
                stats = data.get("stats", {})
                self._add_result("Cache Stats", TestStatus.PASS, duration, 
                               f"Backend: {data.get('backend', 'unknown')}")
            elif "valid_entries" in data or "total_entries" in data:
                self._add_result("Cache Stats", TestStatus.PASS, duration)
            else:
                self._add_result("Cache Stats", TestStatus.WARN, duration, "Unexpected response format")
        else:
            self._add_result("Cache Stats", TestStatus.FAIL, duration, 
                           f"Status: {resp.status_code if resp else 'No response'}")

    def test_cache_clear(self):
        """Test POST /api/cache/clear (skip in cloud to avoid disruption)"""
        if self.env_name == "cloud":
            self._add_result("Cache Clear", TestStatus.SKIP, 0, "Skipped in cloud environment")
            return
        
        resp, duration = self._request("POST", "/api/cache/clear")
        if resp and resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                self._add_result("Cache Clear", TestStatus.PASS, duration)
            else:
                self._add_result("Cache Clear", TestStatus.WARN, duration, "Unexpected response")
        else:
            self._add_result("Cache Clear", TestStatus.FAIL, duration)

    # ========== Watchlist Endpoints ==========
    def test_watchlist_crud(self):
        """Test watchlist CRUD operations"""
        # GET watchlist
        resp, duration = self._request("GET", "/api/watchlist")
        if resp and resp.status_code == 200:
            self._add_result("Watchlist GET", TestStatus.PASS, duration)
        else:
            self._add_result("Watchlist GET", TestStatus.FAIL, duration)
            return

        # POST add symbol (400 = already exists, which is acceptable)
        resp, duration = self._request("POST", f"/api/watchlist/{TEST_TICKER}")
        if resp and resp.status_code in [200, 400]:
            msg = "Added" if resp.status_code == 200 else "Already exists"
            self._add_result("Watchlist POST (add)", TestStatus.PASS, duration, msg)
        else:
            self._add_result("Watchlist POST (add)", TestStatus.FAIL, duration,
                           f"Status: {resp.status_code if resp else 'No response'}")

        # DELETE single symbol
        resp, duration = self._request("DELETE", f"/api/watchlist/{TEST_TICKER}")
        if resp and resp.status_code == 200:
            self._add_result("Watchlist DELETE (single)", TestStatus.PASS, duration)
        else:
            self._add_result("Watchlist DELETE (single)", TestStatus.FAIL, duration)

    def test_watchlist_clear(self):
        """Test DELETE /api/watchlist (clear all)"""
        if self.env_name == "cloud":
            self._add_result("Watchlist Clear All", TestStatus.SKIP, 0, "Skipped in cloud")
            return
        
        resp, duration = self._request("DELETE", "/api/watchlist")
        if resp and resp.status_code == 200:
            self._add_result("Watchlist Clear All", TestStatus.PASS, duration)
        else:
            self._add_result("Watchlist Clear All", TestStatus.FAIL, duration)

    # ========== Favorites Endpoints ==========
    def test_favorites_crud(self):
        """Test favorites CRUD operations"""
        # GET favorites
        resp, duration = self._request("GET", "/api/favorites")
        if resp and resp.status_code == 200:
            self._add_result("Favorites GET", TestStatus.PASS, duration)
        else:
            self._add_result("Favorites GET", TestStatus.FAIL, duration)
            return

        # POST add symbol (400 = already exists, which is acceptable)
        resp, duration = self._request("POST", f"/api/favorites/{TEST_TICKER}")
        if resp and resp.status_code in [200, 400]:
            msg = "Added" if resp.status_code == 200 else "Already exists"
            self._add_result("Favorites POST (add)", TestStatus.PASS, duration, msg)
        else:
            self._add_result("Favorites POST (add)", TestStatus.FAIL, duration,
                           f"Status: {resp.status_code if resp else 'No response'}")

        # DELETE single symbol
        resp, duration = self._request("DELETE", f"/api/favorites/{TEST_TICKER}")
        if resp and resp.status_code == 200:
            self._add_result("Favorites DELETE (single)", TestStatus.PASS, duration)
        else:
            self._add_result("Favorites DELETE (single)", TestStatus.FAIL, duration)

    # ========== Analysis Endpoints ==========
    def test_analyze_single(self):
        """Test GET /api/analyze/{ticker}"""
        resp, duration = self._request("GET", f"/api/analyze/{TEST_TICKER}")
        if resp and resp.status_code == 200:
            data = resp.json()
            required_fields = ["symbol", "price"]
            missing = [f for f in required_fields if f not in data]
            if not missing:
                self._add_result("Analyze Single", TestStatus.PASS, duration, 
                               f"Price: ${data.get('price', 'N/A')}")
            else:
                self._add_result("Analyze Single", TestStatus.WARN, duration, 
                               f"Missing: {missing}")
        else:
            self._add_result("Analyze Single", TestStatus.FAIL, duration)

    def test_analyze_batch(self):
        """Test POST /api/analyze-batch"""
        payload = {"tickers": [TEST_TICKER, TEST_TICKER_2]}
        resp, duration = self._request("POST", "/api/analyze-batch", json=payload)
        if resp and resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) >= 2:
                self._add_result("Analyze Batch", TestStatus.PASS, duration, 
                               f"Returned {len(data)} stocks")
            else:
                self._add_result("Analyze Batch", TestStatus.WARN, duration, 
                               f"Unexpected format")
        else:
            self._add_result("Analyze Batch", TestStatus.FAIL, duration)

    # ========== History Endpoints ==========
    def test_history_single(self):
        """Test GET /api/history/{ticker}"""
        resp, duration = self._request("GET", f"/api/history/{TEST_TICKER}")
        if resp and resp.status_code == 200:
            data = resp.json()
            # API may return {"data": [...]} or just [...] or {ticker: [...]}
            if isinstance(data, dict):
                if "data" in data:
                    points = len(data.get("data", []))
                elif TEST_TICKER in data:
                    points = len(data.get(TEST_TICKER, []))
                else:
                    points = sum(len(v) if isinstance(v, list) else 0 for v in data.values())
            elif isinstance(data, list):
                points = len(data)
            else:
                points = 0
            self._add_result("History Single", TestStatus.PASS, duration, 
                           f"{points} data points")
        else:
            self._add_result("History Single", TestStatus.FAIL, duration)

    def test_history_batch(self):
        """Test POST /api/history-batch"""
        payload = {"tickers": [TEST_TICKER, TEST_TICKER_2], "period": "1y"}
        resp, duration = self._request("POST", "/api/history-batch", json=payload)
        if resp and resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and len(data) >= 2:
                self._add_result("History Batch", TestStatus.PASS, duration, 
                               f"{len(data)} tickers returned")
            else:
                self._add_result("History Batch", TestStatus.WARN, duration)
        else:
            self._add_result("History Batch", TestStatus.FAIL, duration)

    # ========== Volatility & CSP Metrics ==========
    def test_volatility(self):
        """Test GET /api/volatility/{ticker}"""
        resp, duration = self._request("GET", f"/api/volatility/{TEST_TICKER}")
        if resp and resp.status_code == 200:
            data = resp.json()
            if "hv_current" in data or "iv_rank" in data:
                self._add_result("Volatility", TestStatus.PASS, duration)
            else:
                self._add_result("Volatility", TestStatus.WARN, duration, "Missing expected fields")
        else:
            self._add_result("Volatility", TestStatus.FAIL, duration)

    def test_csp_metrics(self):
        """Test GET /api/csp-metrics/{ticker}"""
        resp, duration = self._request("GET", f"/api/csp-metrics/{TEST_TICKER}")
        if resp and resp.status_code == 200:
            self._add_result("CSP Metrics", TestStatus.PASS, duration)
        else:
            self._add_result("CSP Metrics", TestStatus.FAIL, duration)

    # ========== Search ==========
    def test_search_stocks(self):
        """Test GET /api/search-stocks/{query}"""
        resp, duration = self._request("GET", "/api/search-stocks/APP")
        if resp and resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if len(results) > 0:
                self._add_result("Search Stocks", TestStatus.PASS, duration, 
                               f"{len(results)} results")
            else:
                self._add_result("Search Stocks", TestStatus.WARN, duration, "No results")
        else:
            self._add_result("Search Stocks", TestStatus.FAIL, duration)

    # ========== Technical Indicators ==========
    def test_mystic_pulse(self):
        """Test GET /api/mystic-pulse/{ticker} with various periods"""
        periods = ["1mo", "3mo", "6mo", "1y", "3y"]
        
        for period in periods:
            resp, duration = self._request("GET", f"/api/mystic-pulse/{TEST_TICKER}?period={period}")
            if resp and resp.status_code == 200:
                data = resp.json()
                points = len(data.get("data", []))
                if points > 0:
                    self._add_result(f"Mystic Pulse ({period})", TestStatus.PASS, duration, 
                                   f"{points} points")
                else:
                    self._add_result(f"Mystic Pulse ({period})", TestStatus.WARN, duration, 
                                   "No data points")
            else:
                self._add_result(f"Mystic Pulse ({period})", TestStatus.FAIL, duration)



    # ========== Market Data ==========
    def test_market_news(self):
        """Test GET /api/market-news"""
        resp, duration = self._request("GET", "/api/market-news")
        if resp and resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                self._add_result("Market News", TestStatus.PASS, duration)
            else:
                self._add_result("Market News", TestStatus.WARN, duration)
        else:
            self._add_result("Market News", TestStatus.FAIL, duration)

    def test_sp100(self):
        """Test GET /api/sp100 (heavy endpoint, use longer timeout)"""
        resp, duration = self._request("GET", "/api/sp100", timeout=self.timeout_heavy)
        if resp and resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) >= 50:
                self._add_result("S&P 100 List", TestStatus.PASS, duration, 
                               f"{len(data)} stocks")
            elif isinstance(data, list):
                self._add_result("S&P 100 List", TestStatus.WARN, duration, 
                               f"Only {len(data)} stocks")
            else:
                self._add_result("S&P 100 List", TestStatus.WARN, duration, "Unexpected format")
        else:
            self._add_result("S&P 100 List", TestStatus.FAIL, duration,
                           f"Status: {resp.status_code if resp else 'Timeout/No response'}")

    # ========== YouTube Integration ==========
    def test_youtube_stocks(self):
        """Test GET /api/youtube-stocks (Gemini-dependent, optional)"""
        resp, duration = self._request("GET", "/api/youtube-stocks", timeout=self.timeout_heavy)
        if resp and resp.status_code == 200:
            self._add_result("YouTube Stocks", TestStatus.PASS, duration)
        elif resp and resp.status_code == 500:
            self._add_result("YouTube Stocks", TestStatus.WARN, duration, 
                           "API may not be configured")
        else:
            # Timeout is acceptable for Gemini-dependent endpoints
            self._add_result("YouTube Stocks", TestStatus.WARN, duration,
                           "Timeout (Gemini API dependent)")

    def test_youtube_video_list(self):
        """Test GET /api/youtube-video-list (Gemini-dependent, optional)"""
        resp, duration = self._request("GET", "/api/youtube-video-list", timeout=self.timeout_heavy)
        if resp and resp.status_code == 200:
            self._add_result("YouTube Video List", TestStatus.PASS, duration)
        elif resp and resp.status_code == 500:
            self._add_result("YouTube Video List", TestStatus.WARN, duration, 
                           "API may not be configured")
        else:
            self._add_result("YouTube Video List", TestStatus.WARN, duration,
                           "Timeout (Gemini API dependent)")

    # ========== Debug Endpoints ==========
    def test_debug_models(self):
        """Test GET /api/debug-models (Gemini-dependent, optional)"""
        resp, duration = self._request("GET", "/api/debug-models", timeout=self.timeout_heavy)
        if resp and resp.status_code == 200:
            self._add_result("Debug Models", TestStatus.PASS, duration)
        else:
            # This endpoint calls Gemini API, timeout is acceptable
            self._add_result("Debug Models", TestStatus.WARN, duration,
                           "Timeout (Gemini API dependent)")

    # ========== Data Quality Checks ==========
    def test_mystic_pulse_data_quality(self):
        """Verify Mystic Pulse data quality (sorted, no duplicates)"""
        resp, duration = self._request("GET", f"/api/mystic-pulse/{TEST_TICKER}?period=1y", 
                                        timeout=self.timeout_heavy)
        if not resp or resp.status_code != 200:
            self._add_result("Data Quality: Mystic Pulse", TestStatus.FAIL, duration,
                           f"Status: {resp.status_code if resp else 'Timeout'}")
            return

        data = resp.json().get("data", [])
        if not data:
            self._add_result("Data Quality: Mystic Pulse", TestStatus.WARN, duration, "No data")
            return
        
        # Check sorting
        dates = [item["date"] for item in data if "date" in item]
        is_sorted = dates == sorted(dates)
        
        # Check duplicates
        unique_dates = set(dates)
        has_duplicates = len(unique_dates) != len(dates)
        
        if is_sorted and not has_duplicates:
            self._add_result("Data Quality: Mystic Pulse", TestStatus.PASS, duration, 
                           f"Sorted: ✓, No dups: ✓ ({len(data)} pts)")
        else:
            issues = []
            if not is_sorted:
                issues.append("Not sorted")
            if has_duplicates:
                issues.append(f"{len(dates) - len(unique_dates)} duplicates")
            self._add_result("Data Quality: Mystic Pulse", TestStatus.FAIL, duration, 
                           ", ".join(issues))

    # ========== Run All Tests ==========
    def run_all(self):
        """Run all tests"""
        print(f"\n{'='*60}")
        print(f"🧪 API Test Suite - {self.env_name.upper()}")
        print(f"   Base URL: {self.base_url}")
        print(f"{'='*60}\n")

        # Health check first
        if not self.test_health():
            print("\n❌ Health check failed. Aborting remaining tests.")
            return self.results

        print("\n📦 Cache Tests:")
        self.test_cache_stats()
        self.test_cache_clear()

        print("\n📋 Watchlist Tests:")
        self.test_watchlist_crud()
        self.test_watchlist_clear()

        print("\n⭐ Favorites Tests:")
        self.test_favorites_crud()

        print("\n📊 Analysis Tests:")
        self.test_analyze_single()
        self.test_analyze_batch()

        print("\n📈 History Tests:")
        self.test_history_single()
        self.test_history_batch()

        print("\n📉 Volatility & CSP Tests:")
        self.test_volatility()
        self.test_csp_metrics()

        print("\n🔍 Search Tests:")
        self.test_search_stocks()

        print("\n🔮 Technical Indicator Tests:")
        self.test_mystic_pulse()


        print("\n📰 Market Data Tests:")
        self.test_market_news()
        self.test_sp100()

        print("\n📺 YouTube Integration Tests:")
        self.test_youtube_stocks()
        self.test_youtube_video_list()

        print("\n🛠️ Debug Tests:")
        self.test_debug_models()

        print("\n🔬 Data Quality Tests:")
        self.test_mystic_pulse_data_quality()

        # Summary
        self._print_summary()
        
        return self.results

    def _print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == TestStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)
        total = len(self.results)
        
        avg_time = sum(r.duration_ms for r in self.results) / total if total > 0 else 0

        print(f"\n{'='*60}")
        print(f"📊 SUMMARY - {self.env_name.upper()}")
        print(f"{'='*60}")
        print(f"   ✅ Passed:  {passed}/{total}")
        print(f"   ❌ Failed:  {failed}/{total}")
        print(f"   ⚠️ Warned:  {warned}/{total}")
        print(f"   ⏭️ Skipped: {skipped}/{total}")
        print(f"   ⏱️ Avg Time: {avg_time:.0f}ms")
        print(f"{'='*60}\n")

        if failed > 0:
            print("❌ FAILED TESTS:")
            for r in self.results:
                if r.status == TestStatus.FAIL:
                    print(f"   • {r.name}: {r.message}")
            print()


def main():
    parser = argparse.ArgumentParser(description="Comprehensive API Test Suite")
    parser.add_argument("--local", action="store_true", help="Test local environment")
    parser.add_argument("--cloud", action="store_true", help="Test cloud environment")
    parser.add_argument("--both", action="store_true", help="Test both environments")
    parser.add_argument("--url", type=str, help="Custom base URL to test")
    
    args = parser.parse_args()
    
    # Default to local if no flag specified
    if not any([args.local, args.cloud, args.both, args.url]):
        args.local = True

    all_results = {}

    if args.url:
        suite = APITestSuite(args.url, "custom")
        all_results["custom"] = suite.run_all()
    
    if args.local or args.both:
        suite = APITestSuite(LOCAL_URL, "local")
        all_results["local"] = suite.run_all()
    
    if args.cloud or args.both:
        suite = APITestSuite(CLOUD_URL, "cloud")
        all_results["cloud"] = suite.run_all()

    # Final cross-environment summary if testing both
    if args.both:
        print("\n" + "="*60)
        print("🌍 CROSS-ENVIRONMENT COMPARISON")
        print("="*60)
        
        for env, results in all_results.items():
            passed = sum(1 for r in results if r.status == TestStatus.PASS)
            total = len(results)
            print(f"   {env.upper()}: {passed}/{total} passed")
        print()


if __name__ == "__main__":
    main()
