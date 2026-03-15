# Ad Detection Engine
# Core detection classes and browser automation for stealth ad detection.
# Extracted from step1_ad_detector.py for modularity.

# This is main method for ad detection with highest successful 
# detection rate due to stealth browser and UI marker checks

import asyncio
import logging
import random
import sys
from dataclasses import dataclass, field
from typing import Optional

# Check for optional stealth library (improves bot evasion)
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

# Dataclass holding individual UI ad marker flags
@dataclass
class UIAdDetectionResult:
    """
    Results from player UI ad detection.

    Attributes:
        sponsored_label: True if "Sponsored" text found in player
        ad_label: True if "Ad" badge found
        skip_button: True if skip ad button visible
        ad_countdown: True if ad countdown timer visible
        ad_overlay: True if ad overlay container present
        ad_showing_class: True if player has 'ad-showing' CSS class
        raw_markers: List of detection context for debugging
    """


# Dataclass holding final detection verdict for a video
@dataclass
class AdDetectionResult:
    """
    Final ad detection result for a video.

    Attributes:
        video_id: YouTube video ID
        ui_result: Detailed UI detection findings
        verdict: True=has ads, False=no ads
        confidence: Detection confidence level
        error: Error message if detection failed
    """


# Main detector class using stealth Playwright browser
class AdDetector:
    """
    YouTube ad detector using stealth browser automation.

    Uses headed Chromium browser with stealth settings to avoid bot detection.
    Detects ads by checking for "Sponsored" label in the video player UI.

    Usage:
        detector = AdDetector()
        await detector.setup()
        result = await detector.detect("VIDEO_ID")
        await detector.cleanup()
    """

    # Detect ads for a list of videos with progress reporting
    async def detect_batch(self, video_ids: list, delay: float = 1.0,
                           progress_callback=None) -> list:
        results = []


    # Run full ad detection for a single video (navigate, poll, seek)
    async def detect(self, video_id: str) -> AdDetectionResult:
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("Detecting ads for: %s", video_id)

        ui_result = UIAdDetectionResult()
        error = None

        try:
            # Create fresh browser context with randomized fingerprint
            ua = self._random_user_agent()
            vp = self._random_viewport()
            self.logger.info("Using viewport %dx%d", vp['width'], vp['height'])
            context = await self.browser.new_context(viewport=vp, user_agent=ua)

            # Override navigator.webdriver to avoid detection
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = await context.new_page()

