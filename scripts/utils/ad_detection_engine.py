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
    sponsored_label: bool = False
    ad_label: bool = False
    skip_button: bool = False
    ad_countdown: bool = False
    ad_overlay: bool = False
    ad_showing_class: bool = False
    raw_markers: list = field(default_factory=list)

    # Check if any ad marker was detected (sponsored label is primary)
    @property
    def has_ads(self) -> bool:
        """Returns True if any ad marker was detected."""
        return self.sponsored_label


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
    video_id: str
    ui_result: UIAdDetectionResult
    verdict: bool = False
    confidence: str = "high"
    error: Optional[str] = None

    # Convert result fields to a flat dictionary for CSV export
    def to_dict(self) -> dict:
        return {
            'video_id': self.video_id,
            'auto_verdict': 'Yes' if self.verdict else 'No',
            'auto_confidence': self.confidence,
            'auto_sponsored_label': 'Yes' if self.ui_result.sponsored_label else 'No',
            'auto_ad_label': 'Yes' if self.ui_result.ad_label else 'No',
            'auto_skip_button': 'Yes' if self.ui_result.skip_button else 'No',
            'auto_ad_countdown': 'Yes' if self.ui_result.ad_countdown else 'No',
            'auto_ad_overlay': 'Yes' if self.ui_result.ad_overlay else 'No',
            'auto_ad_showing_class': 'Yes' if self.ui_result.ad_showing_class else 'No',
            'auto_error': self.error or '',
        }


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

    # Initialise detector with browser mode and logging config
    def __init__(self, headless: bool = False, log_level: int = logging.INFO):
        self.headless = headless
        self.browser = None
        self.playwright = None
        self.logger = self._setup_logger(log_level)

        # macOS Chrome user agents for rotation
        self._user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        ]

        if headless:
            self.logger.warning("Headless mode may not detect ads due to bot detection!")

    # Configure stdout logger with timestamp format
    def _setup_logger(self, log_level: int) -> logging.Logger:
        logger = logging.getLogger("ad_detector")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    # Pick a random user agent from the rotation list
    def _random_user_agent(self) -> str:
        return random.choice(self._user_agents)

    # Generate a randomised viewport to vary browser fingerprint
    def _random_viewport(self) -> dict:
        width = random.randint(1250, 1400)
        height = random.randint(700, 800)
        return {'width': width, 'height': height}

    # Launch Chromium with anti-detection arguments and stealth patches
    async def setup(self):
        try:
            from playwright.async_api import async_playwright

            self.logger.info("Starting browser (headless=%s)", self.headless)
            self.playwright = await async_playwright().start()

            # Stealth arguments to avoid bot detection
            stealth_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--incognito",
            ]

            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=stealth_args,
                channel="chrome"  # Use installed Chrome for better stealth
            )
            self.logger.info("Browser launched with stealth settings")

        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    # Close browser and release Playwright resources
    async def cleanup(self):
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # Dismiss Google/YouTube cookie consent banner if present
    async def _dismiss_consent(self, page):
        try:
            await asyncio.sleep(1)

            consent_selectors = [
                'button:has-text("Accept all")',
                '[aria-label="Accept the use of cookies and other data for the purposes described"]',
            ]

            for selector in consent_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        self.logger.info("Dismissing consent banner")
                        await button.click()
                        await asyncio.sleep(1)
                        return
                except Exception:
                    continue

        except Exception as e:
            self.logger.debug("Consent handling: %s", e)

    # Check player UI for ad markers (sponsored label, skip button, etc.)
    async def _check_ui_markers(self, page, ui_result: UIAdDetectionResult, context: str = ""):
        try:
            markers = await page.evaluate('''() => {
                const player = document.querySelector('.html5-video-player');
                const adShowing = !!(player && player.classList.contains('ad-showing'));

                // Check badge texts
                const badgeTexts = Array.from(document.querySelectorAll('.ytp-ad-badge__text'))
                    .map(el => (el.textContent || '').trim().toLowerCase());
                const hasAdLabel = badgeTexts.some(t => t === 'ad');
                const hasSponsoredBadge = badgeTexts.some(t => t.includes('sponsored'));

                // Check for "Sponsored" anywhere in player
                const sponsoredInPlayer = (() => {
                    if (!player) return false;
                    const nodes = player.querySelectorAll('*');
                    for (const node of nodes) {
                        const text = (node.textContent || '').trim().toLowerCase();
                        if (text === 'sponsored' || text.includes('sponsored')) {
                            return true;
                        }
                    }
                    return false;
                })();

                // Check for skip button and countdown
                const skipButton = !!document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern');
                const adCountdown = !!document.querySelector(
                    '.ytp-ad-preview-container, .ytp-ad-timed-pie-countdown-container, .ytp-ad-duration-remaining'
                );
                const adOverlay = !!document.querySelector('.ytp-ad-overlay-container, .ytp-ad-overlay-slot');

                return {
                    adShowing,
                    hasAdLabel,
                    hasSponsored: (hasSponsoredBadge || sponsoredInPlayer),
                    skipButton,
                    adCountdown,
                    adOverlay,
                    badgeTexts,
                };
            }''')

            # Update result with newly detected markers
            newly_detected = []

            if markers.get('hasSponsored') and not ui_result.sponsored_label:
                ui_result.sponsored_label = True
                newly_detected.append("sponsored_label")
            if markers.get('hasAdLabel') and not ui_result.ad_label:
                ui_result.ad_label = True
                newly_detected.append("ad_label")
            if markers.get('skipButton') and not ui_result.skip_button:
                ui_result.skip_button = True
                newly_detected.append("skip_button")
            if markers.get('adCountdown') and not ui_result.ad_countdown:
                ui_result.ad_countdown = True
                newly_detected.append("ad_countdown")
            if markers.get('adOverlay') and not ui_result.ad_overlay:
                ui_result.ad_overlay = True
                newly_detected.append("ad_overlay")
            if markers.get('adShowing') and not ui_result.ad_showing_class:
                ui_result.ad_showing_class = True
                newly_detected.append("ad_showing_class")

            if newly_detected:
                ui_result.raw_markers.append({"context": context, "detected": newly_detected})
                self.logger.info("Ad markers detected (%s): %s", context, ", ".join(newly_detected))

            return markers

        except Exception as e:
            self.logger.warning("UI marker check failed: %s", str(e))
            return None

    # Play video and seek to 25/50/75% to trigger mid-roll ads
    async def _play_and_seek(self, page, ui_result: UIAdDetectionResult):
        try:
            self.logger.info("Starting playback and seek sequence")

            # Start video playback
            await page.evaluate('''() => {
                const player = document.querySelector('video');
                if (player) {
                    player.muted = true;
                    player.play().catch(() => {});
                }
            }''')

            # Wait for pre-roll ads
            await asyncio.sleep(3)
            markers = await self._check_ui_markers(page, ui_result, context="after play")

            # If ad is playing, wait for it to finish before seeking
            if markers and markers.get('adShowing'):
                self.logger.info("Ad playing, waiting...")
                for _ in range(10):  # Wait up to 20 seconds
                    await asyncio.sleep(2)
                    markers = await self._check_ui_markers(page, ui_result, context="ad wait")
                    if not markers or not markers.get('adShowing'):
                        break

            # Seek to different positions to trigger mid-roll ads
            for position in [0.25, 0.5, 0.75]:
                self.logger.info("Seeking to %.0f%%", position * 100)
                await page.evaluate(f'''() => {{
                    const video = document.querySelector('video');
                    if (video && video.duration) {{
                        video.currentTime = video.duration * {position};
                    }}
                }}''')
                await asyncio.sleep(2)
                await self._check_ui_markers(page, ui_result, context=f"seek {int(position * 100)}%")

            # Final check
            await asyncio.sleep(2)
            await self._check_ui_markers(page, ui_result, context="final")

        except Exception as e:
            self.logger.warning("Playback/seek failed: %s", str(e))

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

            # Apply stealth patches if available
            if STEALTH_AVAILABLE:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
                self.logger.info("Applied stealth patches")

            # Navigate to video
            self.logger.info("Loading video page...")
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Dismiss cookie consent
            await self._dismiss_consent(page)

            # Wait for player to initialize
            await asyncio.sleep(2)

            # Poll for pre-roll ads (they appear shortly after page load)
            self.logger.info("Checking for pre-roll ads...")
            for poll in range(4):
                await self._check_ui_markers(page, ui_result, context=f"pre-roll {poll+1}")
                if ui_result.sponsored_label:
                    self.logger.info("Pre-roll ad detected!")
                    break
                await asyncio.sleep(2)

            # Play video and seek to trigger mid-roll ads
            await self._play_and_seek(page, ui_result)

            # Log final UI state
            self.logger.info(
                "UI summary: sponsored=%s, ad_label=%s, skip=%s, countdown=%s",
                ui_result.sponsored_label,
                ui_result.ad_label,
                ui_result.skip_button,
                ui_result.ad_countdown
            )

            await context.close()

        except Exception as e:
            error = str(e)
            self.logger.error("Detection failed: %s", error)

        # Determine verdict based on sponsored label
        verdict = ui_result.sponsored_label

        self.logger.info("Verdict: %s", "Has Ads" if verdict else "No Ads")

        return AdDetectionResult(
            video_id=video_id,
            ui_result=ui_result,
            verdict=verdict,
            confidence="high",
            error=error,
        )

    # Detect ads for a list of videos with progress reporting
    async def detect_batch(self, video_ids: list, delay: float = 1.0,
                           progress_callback=None) -> list:
        results = []

        for i, video_id in enumerate(video_ids):
            result = await self.detect(video_id)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(video_ids), result)

            # Restart browser every 5 videos to get a fresh fingerprint
            if (i + 1) % 5 == 0 and i < len(video_ids) - 1:
                self.logger.info("Restarting browser to avoid detection...")
                await self.cleanup()
                await self.setup()

            if i < len(video_ids) - 1:
                wait_time = random.uniform(5.0, 12.0)
                self.logger.info("Waiting %.1f seconds before next video...", wait_time)
                await asyncio.sleep(wait_time)

        return results


# Synchronous wrapper for single-video ad detection
def detect_ads_sync(video_id: str, headless: bool = False) -> AdDetectionResult:
    async def _detect():
        detector = AdDetector(headless=headless)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()

    return asyncio.run(_detect())
