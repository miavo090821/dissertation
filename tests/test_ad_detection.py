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

    def test_empty_page_source(self):
        result = check_dom_for_ads("")
        assert result["has_adTimeOffset"] is False
        assert result["has_playerAds"] is False


class TestVerdictDetermination:
    def test_sponsored_label_true(self):
        dom = DOMDetectionResult(has_adTimeOffset=False, loads_with_ads=0, total_loads=1)
        network = NetworkDetectionResult(ad_requests_count=0, ad_break_detected=False)
        ui = UIAdDetectionResult(sponsored_label=True)

        verdict, method, confidence = determine_verdict(dom, network, ui)

        assert verdict is True
        assert method == DetectionMethod.UI
        assert confidence == "high"


class TestUIAdDetectionResultProperties:
    def test_has_ads_with_sponsored_label(self):
        result = UIAdDetectionResult(sponsored_label=True)
        assert result.has_ads is True

    def test_has_ads_with_no_markers(self):
        result = UIAdDetectionResult()
        assert result.has_ads is False


class TestDOMDetectionResultProperties:
    def test_has_ads_with_adTimeOffset(self):
        result = DOMDetectionResult(has_adTimeOffset=True, has_playerAds=False)
        assert result.has_ads is True

    def test_has_ads_with_neither(self):
        result = DOMDetectionResult(has_adTimeOffset=False, has_playerAds=False)
        assert result.has_ads is False

    def test_is_conclusive_with_5_loads(self):
        result = DOMDetectionResult(total_loads=5)
        assert result.is_conclusive is True

    def test_is_conclusive_with_fewer_loads(self):
        result = DOMDetectionResult(total_loads=4)
        assert result.is_conclusive is False


class TestNetworkDetectionResultProperties:
    def test_has_ads_with_ad_break(self):
        result = NetworkDetectionResult(ad_break_detected=True)
        assert result.has_ads is True

    def test_has_ads_without_ad_break(self):
        result = NetworkDetectionResult(ad_break_detected=False, ad_requests_count=10)
        assert result.has_ads is False
