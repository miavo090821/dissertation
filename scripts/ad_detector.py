"""
Ad Detection Module for YouTube Self-Censorship Research
=========================================================

Detects advertisements on YouTube videos using stealth browser automation
and UI-based detection (checking for "Sponsored" label in video player).

Methodology:
- Uses headed browser with stealth settings to avoid bot detection
- Checks for "Sponsored" label which only appears when an ad is actually rendered
- This approach detects ad DELIVERY, not just ad INFRASTRUCTURE

Note: DOM variables (adTimeOffset, playerAds) and Network signals (ad_break, pagead)
were evaluated but removed as they indicate infrastructure availability, not actual
ad delivery, producing false positives on non-monetised content.

Reference: YouTube Self-Censorship Research Project (RQ1 Methodology)
"""

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from typing import Optional

# Check for stealth library
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


@dataclass
class UIAdDetectionResult:
    
    # Results from player UI ad detection.

    # Attributes:
    #     sponsored_label: True if "Sponsored" text found in player
    #     ad_label: True if "Ad" badge found
    #     skip_button: True if skip ad button visible
    #     ad_countdown: True if ad countdown timer visible
    #     ad_overlay: True if ad overlay container present
    #     ad_showing_class: True if player has 'ad-showing' CSS class
    #     raw_markers: List of detection context for debugging
    
    sponsored_label: bool = False
    ad_label: bool = False
    skip_button: bool = False
    ad_countdown: bool = False
    ad_overlay: bool = False
    ad_showing_class: bool = False
    raw_markers: list = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        """Returns True if any ad marker was detected."""
        return self.sponsored_label  # Sponsored label is the primary indicator


@dataclass
class AdDetectionResult:
    
    # Final ad detection result for a video.

    # Attributes:
    #     video_id: YouTube video ID
    #     ui_result: Detailed UI detection findings
    #     verdict: True=has ads, False=no ads
    #     confidence: Detection confidence level
    #     error: Error message if detection failed
    
    video_id: str
    ui_result: UIAdDetectionResult
    verdict: bool = False
    confidence: str = "high"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert result to dictionary for CSV export."""
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


class AdDetector:
   
    # YouTube ad detector using stealth browser automation.

    # Uses headed Chromium browser with stealth settings to avoid bot detection.
    # Detects ads by checking for "Sponsored" label in the video player UI.

    # Usage:
    #     detector = AdDetector()
    #     await detector.setup()
    #     result = await detector.detect("VIDEO_ID")
    #     await detector.cleanup()


    def __init__(self, headless: bool = False, log_level: int = logging.INFO):
        
        # Initialise ad detector.

        # Args:
        #     headless: Run browser in headless mode (NOT RECOMMENDED - ads not served)
        #     log_level: Logging level (default INFO)
    
        self.headless = headless
        self.browser = None
        self.playwright = None
        self.logger = self._setup_logger(log_level)

        if headless:
            self.logger.warning("Headless mode may not detect ads due to bot detection!")

    def _setup_logger(self, log_level: int) -> logging.Logger:
        """Configure logger for this detector instance."""
        logger = logging.getLogger("ad_detector")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    async def setup(self):
        
        # Initialize Playwright browser with stealth settings.

        # Launches Chromium with arguments to avoid bot detection:
        # - Disables AutomationControlled blink feature
        # - Opens in incognito mode
        # - Applies playwright-stealth patches if available
    
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

    async def cleanup(self):
        """Close browser and release resources."""
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _dismiss_consent(self, page):
        """Click 'Accept all' on Google/YouTube cookie consent banner if present."""
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

    async def _check_ui_markers(self, page, ui_result: UIAdDetectionResult, context: str = ""):
        """
        Check player UI for ad markers and update result.

        Looks for:
        - "Sponsored" text in player (primary indicator)
        - Ad badge text
        - Skip button
        - Ad countdown timer
        - Ad overlay container
        - ad-showing CSS class on player

        Args:
            page: Playwright page object
            ui_result: Result object to update
            context: Description of when this check is happening
        """
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

    async def _play_and_seek(self, page, ui_result: UIAdDetectionResult):
        
        # Play video and seek to different positions to trigger mid-roll ads.

        # Strategy:
        # 1. Start video playback (triggers pre-roll ads)
        # 2. Wait and check for ad markers
        # 3. Seek to 25%, 50%, 75% positions (triggers mid-roll ads)
        # 4. Check for markers after each seek

        # Args:
        #     page: Playwright page object
        #     ui_result: Result object to update with findings
        
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

    async def detect(self, video_id: str) -> AdDetectionResult:
        
        # Detect ads for a YouTube video.

        # Args:
        #     video_id: YouTube video ID (e.g., "dQw4w9WgXcQ")

        # Returns:
        #     AdDetectionResult with verdict and detection details
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("Detecting ads for: %s", video_id)

        ui_result = UIAdDetectionResult()
        error = None

        try:
            # Create fresh browser context (like incognito)
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

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

    async def detect_batch(self, video_ids: list, delay: float = 1.0,
                           progress_callback=None) -> list:
        
        # Detect ads for multiple videos.

        # Args:
        #     video_ids: List of YouTube video IDs
        #     delay: Delay between videos in seconds (default 1.0)
        #     progress_callback: Optional callback(current, total, result)

        # Returns:
        #     List of AdDetectionResult objects
        
        results = []

        for i, video_id in enumerate(video_ids):
            result = await self.detect(video_id)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(video_ids), result)

            if i < len(video_ids) - 1:
                await asyncio.sleep(delay)

        return results


def detect_ads_sync(video_id: str, headless: bool = False) -> AdDetectionResult:
    
    # Synchronous wrapper for ad detection.

    # Convenience function for non-async code.

    # Args:
    #     video_id: YouTube video ID
    #     headless: Run browser in headless mode (not recommended)

    # Returns:
    #     AdDetectionResult with verdict and details
    
    async def _detect():
        detector = AdDetector(headless=headless)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()

    return asyncio.run(_detect())


if __name__ == "__main__":
    # Command-line usage
    if len(sys.argv) < 2:
        print("Usage: python ad_detector.py <video_id>")
        print("Example: python ad_detector.py dQw4w9WgXcQ")
        sys.exit(1)

    video_id = sys.argv[1]
    print(f"Detecting ads for video: {video_id}")
    print("(This requires a visible browser window)")
    print()

    result = detect_ads_sync(video_id, headless=False)

    print("\n=== Detection Results ===")
    print(f"Video ID: {result.video_id}")
    print(f"\nUI Detection:")
    print(f"  Sponsored label: {result.ui_result.sponsored_label}")
    print(f"  Ad label: {result.ui_result.ad_label}")
    print(f"  Skip button: {result.ui_result.skip_button}")
    print(f"  Ad countdown: {result.ui_result.ad_countdown}")
    print(f"  Ad overlay: {result.ui_result.ad_overlay}")
    print(f"  Ad-showing class: {result.ui_result.ad_showing_class}")
    print(f"\nVerdict: {'Has Ads' if result.verdict else 'No Ads'}")
    print(f"Confidence: {result.confidence}")
    if result.error:
        print(f"Error: {result.error}")
