import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.ad_detector import check_url_for_ads, check_dom_for_ads


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


class TestNetworkPatternMatching:
    def test_ad_break_detection(self):
        url = "https://www.youtube.com/api/stats/playback?ad_break=1&docid=xyz"
        result = check_url_for_ads(url)
        assert result["ad_break"] is True
        assert result["is_ad_related"] is True

    def test_case_insensitive_matching(self):
        url = "https://youtube.com/AD_BREAK"
        result = check_url_for_ads(url)
        assert result["is_ad_related"] is True


class TestDOMDetection:
    def test_adTimeOffset_detection(self):
        source = '{"adTimeOffset": {"start": 0, "end": 30}}'
        result = check_dom_for_ads(source)
        assert result["has_adTimeOffset"] is True

    def test_playerAds_detection(self):
        source = '{"playerAds": [{"adPlacementConfig": {}}]}'
        result = check_dom_for_ads(source)
        assert result["has_playerAds"] is True
