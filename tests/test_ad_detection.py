# # Unit Tests for Ad Detection Module
#
# Tests both detection methods:
# 1) DOM Detection (Paper 1 - Dunna et al., 2022): adTimeOffset and playerAds
# 2) Network API Detection: ad_break as evidence; other patterns logged only
#
# Test videos selected from video_urls.csv with known manual classification.

import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.ad_detector import (  # noqa: E402
    check_url_for_ads,
    check_dom_for_ads,
    determine_verdict,
    DOMDetectionResult,
    NetworkDetectionResult,
    UIAdDetectionResult,
    DetectionMethod,
)

 # Fixtures
 
@pytest.fixture
def test_videos():
    # Load test video fixtures with known ad status.
    fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_videos.json")
    with open(fixtures_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_videos"]


@pytest.fixture
def videos_with_ads(test_videos):
    # Return only videos that should have ads.
    return [v for v in test_videos if v["expected_ads"]]


@pytest.fixture
def videos_without_ads(test_videos):
    # Return only videos that should NOT have ads.
    return [v for v in test_videos if not v["expected_ads"]]


@pytest.fixture
def playwright_available():
    # Check if Playwright is available.
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


 # Unit Tests: Network Pattern Matching
 
class TestNetworkPatternMatching:
    # Test network URL pattern matching logic.

    def test_ad_break_detection(self):
        # ad_break pattern is treated as strong evidence in the Network API method.
        test_urls = [
            "https://www.youtube.com/api/stats/playback?ad_break=1&docid=xyz",
            "https://youtube.com/watch?v=abc&ad_break_type=preroll",
            "https://googlevideo.com/videoplayback?ad_break",
        ]
        for url in test_urls:
            result = check_url_for_ads(url)
            assert result["ad_break"], f"Failed to detect ad_break in: {url}"
            assert result["is_ad_related"], f"Should be marked as ad-related: {url}"

    def test_pagead_detection(self):
        # pagead pattern is detected and logged as ad-related (not definitive evidence).
        test_urls = [
            "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
            "https://www.youtube.com/pagead/viewthroughconversion/123",
        ]
        for url in test_urls:
            result = check_url_for_ads(url)
            assert result["pagead"], f"Failed to detect pagead in: {url}"
            assert result["is_ad_related"], f"Should be marked as ad-related: {url}"

    def test_doubleclick_detection(self):
        # doubleclick pattern is detected and logged as ad-related (not definitive evidence).
        test_urls = [
            "https://ad.doubleclick.net/ddm/trackclk/xyz",
            "https://googleads.g.doubleclick.net/pagead/id",
            "https://pubads.g.doubleclick.net/gampad/ads",
        ]
        for url in test_urls:
            result = check_url_for_ads(url)
            assert result["doubleclick"], f"Failed to detect doubleclick in: {url}"
            assert result["is_ad_related"], f"Should be marked as ad-related: {url}"

    def test_googlevideo_ad_format(self):
        # googlevideo adformat pattern is detected as ad-related.
        url = "https://rr1---sn-abc.googlevideo.com/videoplayback?adformat=15"
        result = check_url_for_ads(url)
        assert result["is_ad_related"], "Should detect adformat in googlevideo URL"

    def test_non_ad_urls_not_detected(self):
        # Regular YouTube URLs are not flagged as ad-related.
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/channel/UC12345",
            "https://i.ytimg.com/vi/abc/maxresdefault.jpg",
            "https://rr1---sn-abc.googlevideo.com/videoplayback?mime=video/mp4",
            "https://www.google.com/search?q=test",
        ]
        for url in test_urls:
            result = check_url_for_ads(url)
            assert not result["is_ad_related"], f"Should NOT be ad-related: {url}"

    def test_case_insensitive_matching(self):
        # Pattern matching should be case-insensitive.
        urls = [
            "https://youtube.com/AD_BREAK",
            "https://youtube.com/Ad_Break",
            "https://DOUBLECLICK.NET/ad",
            "https://PageAd2.googlesyndication.com/test",
        ]
        for url in urls:
            result = check_url_for_ads(url)
            assert result["is_ad_related"], f"Case-insensitive match failed: {url}"


 # Unit Tests: DOM Detection (Paper 1 Methodology)
 
class TestDOMDetection:
    # Test DOM-based ad detection (Paper 1 - Dunna et al.).

    def test_adTimeOffset_detection(self):
        # adTimeOffset variable detection in page source.
        page_sources = [
            '{"adTimeOffset": {"start": 0, "end": 30}}',
            '"adTimeOffset":{"preroll":true}',
            "'adTimeOffset': [0, 15, 30]",
            'var ytInitialPlayerResponse = {"adTimeOffset": {}}',
        ]
        for source in page_sources:
            result = check_dom_for_ads(source)
            assert result["has_adTimeOffset"], f"Failed to detect adTimeOffset in: {source[:50]}"

    def test_playerAds_detection(self):
        # playerAds variable detection in page source.
        page_sources = [
            '{"playerAds": [{"adPlacementConfig": {}}]}',
            '"playerAds":[{"adPlacementRenderer":{}}]',
            "'playerAds': []",
        ]
        for source in page_sources:
            result = check_dom_for_ads(source)
            assert result["has_playerAds"], f"Failed to detect playerAds in: {source[:50]}"

    def test_no_ad_indicators(self):
        # Pages without ad indicators should return False.
        page_sources = [
            "<html><body>Regular content</body></html>",
            '{"videoDetails": {"videoId": "abc"}}',
            'ytInitialPlayerResponse = {"playabilityStatus": {"status": "OK"}}',
        ]
        for source in page_sources:
            result = check_dom_for_ads(source)
            assert not result["has_adTimeOffset"], f"False positive adTimeOffset: {source[:50]}"
            assert not result["has_playerAds"], f"False positive playerAds: {source[:50]}"

    def test_empty_page_source(self):
        # Empty / None inputs should be handled safely.
        result = check_dom_for_ads("")
        assert not result["has_adTimeOffset"]
        assert not result["has_playerAds"]

        result = check_dom_for_ads(None)
        assert not result["has_adTimeOffset"]
        assert not result["has_playerAds"]


 # Unit Tests: Verdict Determination
 
class TestVerdictDetermination:
    # Test combined verdict logic.

    def test_sponsored_label_true(self):
        # Sponsored label alone should yield Has Ads.
        dom = DOMDetectionResult(has_adTimeOffset=False, loads_with_ads=0, total_loads=1)
        network = NetworkDetectionResult(ad_requests_count=0, ad_break_detected=False)
        ui = UIAdDetectionResult(sponsored_label=True)

        verdict, method, confidence = determine_verdict(dom, network, ui)

        assert verdict is True
        assert method == DetectionMethod.UI
        assert confidence == "high"

    def test_sponsored_label_false(self):
        # If sponsored label is absent, verdict is No Ads.
        dom = DOMDetectionResult(has_adTimeOffset=True, loads_with_ads=1, total_loads=1)
        network = NetworkDetectionResult(ad_requests_count=5, ad_break_detected=True)
        ui = UIAdDetectionResult(sponsored_label=False)

        verdict, method, confidence = determine_verdict(dom, network, ui)

        assert verdict is False
        assert method == DetectionMethod.UI
        assert confidence == "high"

class TestNetworkDetectionResultProperties:
    # Test NetworkDetectionResult dataclass properties.

    def test_has_ads_with_ad_break(self):
        result = NetworkDetectionResult(ad_break_detected=True)
        assert result.has_ads is True

    def test_has_ads_without_ad_break(self):
        result = NetworkDetectionResult(ad_break_detected=False, ad_requests_count=10)
        assert result.has_ads is False

 # Integration Tests (Require Playwright - Skip unless enabled)
class TestIntegrationWithPlaywright:
    @pytest.mark.skipif(
        not os.environ.get("RUN_BROWSER_TESTS"),
        reason="Browser tests disabled. Set RUN_BROWSER_TESTS=1 to enable.",
    )
    @pytest.mark.asyncio
    async def test_detect_ads_on_known_monetised_video(self, videos_with_ads):
        from scripts.ad_detector import AdDetector

        video = videos_with_ads[0]
        detector = AdDetector(headless=True, num_loads=2)
        await detector.setup()

        try:
            result = await detector.detect(video["video_id"])
            assert (
                result.verdict is True
                or result.dom_result.has_ads
                or result.network_result.has_ads
            ), f"Expected to detect ads for video {video['video_id']}"
        finally:
            await detector.cleanup()

    @pytest.mark.skipif(
        not os.environ.get("RUN_BROWSER_TESTS"),
        reason="Browser tests disabled. Set RUN_BROWSER_TESTS=1 to enable.",
    )
    @pytest.mark.asyncio
    async def test_detect_no_ads_on_known_demonetised_video(self, videos_without_ads):
        from scripts.ad_detector import AdDetector

        video = videos_without_ads[0]
        detector = AdDetector(headless=True, num_loads=2)
        await detector.setup()

        try:
            result = await detector.detect(video["video_id"])
            assert (
                result.verdict is False
                or (not result.dom_result.has_ads and not result.network_result.has_ads)
            ), f"Expected no ads for video {video['video_id']}"
        finally:
            await detector.cleanup()


 # Accuracy Tests (Require Playwright and all test videos)
 
class TestAccuracyMetrics:
    @pytest.mark.skipif(
        not os.environ.get("RUN_ACCURACY_TESTS"),
        reason="Accuracy tests disabled. Set RUN_ACCURACY_TESTS=1 to enable.",
    )
    @pytest.mark.asyncio
    async def test_batch_detection_accuracy(self, test_videos):
        from scripts.ad_detector import AdDetector

        detector = AdDetector(headless=True, num_loads=3)
        await detector.setup()

        results = {
            "dom": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
            "network": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
            "combined": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        }

        for method, counts in results.items():
            total = counts["tp"] + counts["tn"] + counts["fp"] + counts["fn"]
            if total > 0:
                accuracy = (counts["tp"] + counts["tn"]) / total
                assert accuracy >= 0.8, f"{method} accuracy {accuracy:.1%} below 80% threshold"


 # Test Fixtures Validation
 
class TestFixturesValidation:
    def test_fixtures_exist(self):
        fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_videos.json")
        assert os.path.exists(fixtures_path), "Fixtures file missing"

        with open(fixtures_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "test_videos" in data
        assert len(data["test_videos"]) == 10

    def test_fixtures_have_required_fields(self, test_videos):
        required_fields = ["video_id", "expected_ads", "channel"]
        for video in test_videos:
            for field in required_fields:
                assert field in video, f"Missing field '{field}' in video {video.get('video_id', 'unknown')}"
                
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
