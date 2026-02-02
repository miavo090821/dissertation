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


@pytest.fixture
def test_videos():
    fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures", "test_videos.json")
    with open(fixtures_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["test_videos"]


@pytest.fixture
def videos_with_ads(test_videos):
    return [v for v in test_videos if v["expected_ads"]]


@pytest.fixture
def videos_without_ads(test_videos):
    return [v for v in test_videos if not v["expected_ads"]]


@pytest.fixture
def playwright_available():
    # Useful for quick diagnosis, even though integration tests are env-gated.
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


class TestNetworkPatternMatching:
    def test_ad_break_detection(self):
        url = "https://www.youtube.com/api/stats/playback?ad_break=1&docid=xyz"
        result = check_url_for_ads(url)
        assert result["ad_break"] is True
        assert result["is_ad_related"] is True


class TestDOMDetection:
    def test_adTimeOffset_detection(self):
        source = '{"adTimeOffset": {"start": 0, "end": 30}}'
        result = check_dom_for_ads(source)
        assert result["has_adTimeOffset"] is True


class TestVerdictDetermination:
    def test_sponsored_label_true(self):
        dom = DOMDetectionResult(has_adTimeOffset=False, loads_with_ads=0, total_loads=1)
        network = NetworkDetectionResult(ad_requests_count=0, ad_break_detected=False)
        ui = UIAdDetectionResult(sponsored_label=True)

        verdict, method, confidence = determine_verdict(dom, network, ui)

        assert verdict is True
        assert method == DetectionMethod.UI
        assert confidence == "high"


class TestIntegrationWithPlaywright:
    @pytest.mark.skipif(
        not os.environ.get("RUN_BROWSER_TESTS"),
        reason="Browser tests disabled. Set RUN_BROWSER_TESTS=1 to enable.",
    )
    @pytest.mark.asyncio
    async def test_detect_ads_on_known_monetised_video(self, videos_with_ads):
        # This test requires the real browser automation layer.
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
