# # Unit Tests for Ad Detection Module

import pytest

from scripts.ad_detector import check_url_for_ads


class TestNetworkPatternMatching:
    def test_ad_break_smoke(self):
        # ad_break should be detected as ad-related.
        url = "https://www.youtube.com/api/stats/playback?ad_break=1&docid=xyz"
        result = check_url_for_ads(url)
        assert result["ad_break"] is True
        assert result["is_ad_related"] is True
