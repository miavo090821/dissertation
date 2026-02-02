import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.ad_detector import check_url_for_ads  # noqa: E402


class TestNetworkPatternMatching:
    def test_ad_break_detection(self):
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
        test_urls = [
            "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
            "https://www.youtube.com/pagead/viewthroughconversion/123",
        ]
        for url in test_urls:
            result = check_url_for_ads(url)
            assert result["pagead"], f"Failed to detect pagead in: {url}"
            assert result["is_ad_related"], f"Should be marked as ad-related: {url}"

    def test_doubleclick_detection(self):
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
        url = "https://rr1---sn-abc.googlevideo.com/videoplayback?adformat=15"
        result = check_url_for_ads(url)
        assert result["is_ad_related"] is True

    def test_non_ad_urls_not_detected(self):
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/channel/UC12345",
            "https://i.ytimg.com/vi/abc/maxresdefault.jpg",
            "https://rr1---sn-abc.googlevideo.com/videoplayback?mime=video/mp4",
            "https://www.google.com/search?q=test",
        ]
        for url in test_urls:
            result = check_url_for_ads(url)
            assert result["is_ad_related"] is False

    def test_case_insensitive_matching(self):
        urls = [
            "https://youtube.com/AD_BREAK",
            "https://youtube.com/Ad_Break",
            "https://DOUBLECLICK.NET/ad",
            "https://PageAd2.googlesyndication.com/test",
        ]
        for url in urls:
            result = check_url_for_ads(url)
            assert result["is_ad_related"] is True
