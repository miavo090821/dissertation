import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.ad_detector import check_url_for_ads, check_dom_for_ads  # noqa: E402


class TestNetworkPatternMatching:
    def test_ad_break_detection(self):
        url = "https://www.youtube.com/api/stats/playback?ad_break=1&docid=xyz"
        result = check_url_for_ads(url)
        assert result["ad_break"] is True
        assert result["is_ad_related"] is True

    def test_non_ad_urls_not_detected(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = check_url_for_ads(url)
        assert result["is_ad_related"] is False


class TestDOMDetection:
    def test_adTimeOffset_detection(self):
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
        page_sources = [
            '{"playerAds": [{"adPlacementConfig": {}}]}',
            '"playerAds":[{"adPlacementRenderer":{}}]',
            "'playerAds': []",
        ]
        for source in page_sources:
            result = check_dom_for_ads(source)
            assert result["has_playerAds"], f"Failed to detect playerAds in: {source[:50]}"

    def test_empty_page_source(self):
        result = check_dom_for_ads("")
        assert result["has_adTimeOffset"] is False
        assert result["has_playerAds"] is False

        result = check_dom_for_ads(None)
        assert result["has_adTimeOffset"] is False
        assert result["has_playerAds"] is False
