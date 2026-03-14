"""
DOM-Based Ad Detection for YouTube Self-Censorship Research
============================================================

Detects ad infrastructure on YouTube videos by checking for DOM variables
(adTimeOffset, playerAds) in the page source HTML.

Methodology (Paper 1 - Dunna et al., 2022):
- Load each video page 5 times
- Each load: extract full page source and search for ad-related variables
- A video is classified as having ads if EITHER variable is found in ANY load
- This detects ad INFRASTRUCTURE embedded in the page, not rendered ad delivery

DOM indicators:
- adTimeOffset: Indicates ad time offsets are configured for the video
- playerAds: Indicates player ad configuration is present

Note: This is a complementary method to the UI-based detection in step1_ad_detector.py.
DOM variables indicate ad infrastructure availability, which may differ from actual
ad delivery (UI method). Both perspectives are valuable for triangulation.

Reference: Dunna et al. (2022) - YouTube Self-Censorship Research (RQ1)
"""
#  this file is restored to prove the effeciency 
# between 3 methods for the research report's purposes 

# Standard library imports
import argparse
import asyncio
import logging
import os
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Optional

# Third-party imports
import pandas as pd

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project configuration paths
try:
    from config import DATA_INPUT_DIR, DATA_OUTPUT_DIR
except ImportError:
    # Fallback defaults if config not available (e.g., standalone testing)
    DATA_INPUT_DIR = "data/input"
    DATA_OUTPUT_DIR = "data/output"

# Check for optional stealth library (improves bot evasion)
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


# --------------------------------------------------------------------------- #
# DOM indicator regex patterns from Paper 1 (Dunna et al., 2022)
# --------------------------------------------------------------------------- #
DOM_INDICATORS = {
    'adTimeOffset': re.compile(r'["\']?adTimeOffset["\']?\s*:', re.IGNORECASE),
    'playerAds': re.compile(r'["\']?playerAds["\']?\s*:', re.IGNORECASE),
}

# Default number of page loads per video (Paper 1 methodology)
DEFAULT_LOADS_PER_VIDEO = 5


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #

@dataclass
class DOMDetectionResult:
    """
    Results from DOM-based ad detection for a single video.

    Attributes:
        has_adTimeOffset: True if adTimeOffset variable found in any page load
        has_playerAds: True if playerAds variable found in any page load
        loads_with_ads: Number of loads where at least one indicator was found
        total_loads: Total number of page loads completed
        raw_findings: Per-load detail for debugging
    """
    has_adTimeOffset: bool = False
    has_playerAds: bool = False
    loads_with_ads: int = 0
    total_loads: int = 0
    raw_findings: list = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        """True if either DOM indicator was found in any load."""
        return self.has_adTimeOffset or self.has_playerAds

    @property
    def is_conclusive(self) -> bool:
        """True if the required number of loads (5) was completed."""
        return self.total_loads >= DEFAULT_LOADS_PER_VIDEO


# --------------------------------------------------------------------------- #
# Pure function: check page source for DOM indicators
# --------------------------------------------------------------------------- #

def check_dom_for_ads(page_source: str) -> dict:
    """
    Search page source HTML for ad-related DOM variables.

    Args:
        page_source: Full HTML content of the YouTube page.

    Returns:
        Dict mapping indicator name to bool (found/not found).
    """
    findings = {}
    for name, pattern in DOM_INDICATORS.items():
        findings[name] = bool(pattern.search(page_source))
    return findings


# --------------------------------------------------------------------------- #
# Extract video ID from URL (same as step1)
# --------------------------------------------------------------------------- #

def extract_video_id(url: str) -> str:
    """Extract the 11-character video ID from a YouTube URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url


# --------------------------------------------------------------------------- #
# DOMDetector class (mirrors AdDetector stealth setup)
# --------------------------------------------------------------------------- #

class DOMDetector:
    """
    YouTube DOM-based ad detector using stealth browser automation.

    Uses headed Chromium with the same stealth settings as step1_ad_detector.py.
    Detects ad infrastructure by scanning page source for adTimeOffset / playerAds.

    Usage:
        detector = DOMDetector()
        await detector.setup()
        result = await detector.detect("VIDEO_ID")
        await detector.cleanup()
    """

    def __init__(self, headless: bool = False, loads_per_video: int = DEFAULT_LOADS_PER_VIDEO,
                 log_level: int = logging.INFO):
        self.headless = headless
        self.loads_per_video = loads_per_video
        self.browser = None
        self.playwright = None
        self.logger = self._setup_logger(log_level)

        # macOS Chrome user agents for rotation (same as step1)
        self._user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        ]

        if headless:
            self.logger.warning("Headless mode may trigger bot detection on YouTube!")

    # Configure stdout logger with timestamp format
    def _setup_logger(self, log_level: int) -> logging.Logger:
        logger = logging.getLogger("dom_detector")
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
        """Launch stealth browser (same config as step1_ad_detector.py)."""
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
        """Shut down browser and Playwright."""
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    # Dismiss Google/YouTube cookie consent banner if present
    async def _dismiss_consent(self, page):
        """Click consent / cookie banners that might block the page."""
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

    # ------------------------------------------------------------------ #
    # Core detection: multiple loads per video
    # ------------------------------------------------------------------ #

    async def detect(self, video_id: str) -> DOMDetectionResult:
        """
        Run DOM-based ad detection for a single video.

        Loads the video page multiple times (default 5) and checks for
        adTimeOffset / playerAds in the page source on each load.

        Args:
            video_id: YouTube video ID.

        Returns:
            DOMDetectionResult with aggregated findings.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("DOM detection for %s (%d loads)", video_id, self.loads_per_video)

        result = DOMDetectionResult()

        for load_num in range(1, self.loads_per_video + 1):
            load_label = f"load {load_num}/{self.loads_per_video}"
            self.logger.info("[%s] %s - starting", video_id, load_label)

            try:
                # Create fresh browser context with randomised fingerprint
                ua = self._random_user_agent()
                vp = self._random_viewport()
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

                # Navigate to video
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # Dismiss cookie consent
                await self._dismiss_consent(page)

                # Wait for page scripts to execute and populate variables
                await asyncio.sleep(3)

                # Extract full page source and run regex detection
                page_source = await page.content()
                findings = check_dom_for_ads(page_source)

                # Update aggregated result
                load_has_ads = any(findings.values())
                if load_has_ads:
                    result.loads_with_ads += 1
                if findings.get('adTimeOffset'):
                    result.has_adTimeOffset = True
                if findings.get('playerAds'):
                    result.has_playerAds = True

                result.total_loads += 1
                result.raw_findings.append({
                    'load': load_num,
                    'adTimeOffset': findings.get('adTimeOffset', False),
                    'playerAds': findings.get('playerAds', False),
                    'error': None,
                })

                self.logger.info(
                    "[%s] %s - adTimeOffset=%s, playerAds=%s",
                    video_id, load_label,
                    findings.get('adTimeOffset'), findings.get('playerAds'),
                )

                await context.close()

            except Exception as e:
                self.logger.warning("[%s] %s - error: %s", video_id, load_label, e)
                result.total_loads += 1
                result.raw_findings.append({
                    'load': load_num,
                    'adTimeOffset': False,
                    'playerAds': False,
                    'error': str(e),
                })

            # Brief delay between loads (not after last)
            if load_num < self.loads_per_video:
                delay = random.uniform(2.0, 4.0)
                await asyncio.sleep(delay)

        self.logger.info(
            "[%s] DOM verdict: has_ads=%s (adTimeOffset=%s, playerAds=%s, "
            "loads_with_ads=%d/%d)",
            video_id, result.has_ads, result.has_adTimeOffset, result.has_playerAds,
            result.loads_with_ads, result.total_loads,
        )

        return result

    # Detect ads for a list of videos with progress reporting
    async def detect_batch(self, video_ids: list, progress_callback=None) -> dict:
        """
        Run DOM detection on a batch of videos.

        Args:
            video_ids: List of YouTube video IDs.
            progress_callback: Optional callable(current, total, video_id, result).

        Returns:
            Dict mapping video_id -> DOMDetectionResult.
        """
        results = {}

        for i, video_id in enumerate(video_ids):
            result = self.detect(video_id)
            # Support both sync and async detect
            if asyncio.iscoroutine(result):
                result = await result
            results[video_id] = result

            if progress_callback:
                progress_callback(i + 1, len(video_ids), video_id, result)

            # Restart browser every 5 videos to get a fresh fingerprint
            if (i + 1) % 5 == 0 and i < len(video_ids) - 1:
                self.logger.info("Restarting browser to refresh fingerprint...")
                await self.cleanup()
                await self.setup()

            # Random delay between videos (not after last)
            if i < len(video_ids) - 1:
                wait_time = random.uniform(5.0, 12.0)
                self.logger.info("Waiting %.1f seconds before next video...", wait_time)
                await asyncio.sleep(wait_time)

        return results


# --------------------------------------------------------------------------- #
# Synchronous wrapper for single-video detection
# --------------------------------------------------------------------------- #

def detect_dom_sync(video_id: str, headless: bool = False,
                    loads_per_video: int = DEFAULT_LOADS_PER_VIDEO) -> DOMDetectionResult:
    """Synchronous convenience wrapper for single-video DOM detection."""
    async def _detect():
        detector = DOMDetector(headless=headless, loads_per_video=loads_per_video)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()

    return asyncio.run(_detect())


# --------------------------------------------------------------------------- #
# CLI / main
# --------------------------------------------------------------------------- #

def main():
    """Batch DOM detection on video_urls.csv with optional --recheck-no mode."""

    # Resolve paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_csv = os.path.join(output_dir, "dom_detection_results.csv")

    # Check input exists
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} not found")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Parse CLI arguments
    parser = argparse.ArgumentParser(
        description='DOM-based ad detection for YouTube videos (Paper 1 methodology)'
    )
    parser.add_argument(
        '--recheck-no', action='store_true',
        help='Re-check only videos where ad_status is "No"'
    )
    parser.add_argument(
        '--recheck-rounds', type=int, default=DEFAULT_LOADS_PER_VIDEO,
        help=f'Number of page loads per video (default: {DEFAULT_LOADS_PER_VIDEO})'
    )
    args = parser.parse_args()

    # Read video URLs
    print("Reading video_urls.csv...")
    df = pd.read_csv(input_csv)

    if 'url' not in df.columns:
        print("ERROR: 'url' column not found in CSV")
        sys.exit(1)

    # Determine which videos need processing
    ads_column = df.get('ad_status', pd.Series([''] * len(df)))
    videos_to_process = []
    video_indices = []

    if args.recheck_no:
        # Re-check mode: only process videos currently marked as "No"
        for i, (url, existing_ad) in enumerate(zip(df['url'], ads_column)):
            if str(existing_ad).strip().lower() == 'no':
                videos_to_process.append(extract_video_id(url))
                video_indices.append(i)
    else:
        # Default mode: process videos with no ad_status yet
        for i, (url, existing_ad) in enumerate(zip(df['url'], ads_column)):
            existing_str = str(existing_ad).strip().lower()
            if existing_str not in ['yes', 'no']:
                videos_to_process.append(extract_video_id(url))
                video_indices.append(i)

    skipped = len(df) - len(videos_to_process)
    print(f"Found {len(df)} total videos")
    if args.recheck_no:
        print("Re-check mode: processing videos with ad_status = No")
    if skipped > 0:
        print(f"Skipping {skipped} videos (already have ad_status)")
    print(f"Processing {len(videos_to_process)} videos ({args.recheck_rounds} loads each)")

    if not videos_to_process:
        print("All videos already processed. Nothing to do.")
        return

    # Run detection
    print("\nStarting DOM-based ad detection...")
    print("NOTE: This requires a visible browser window.")
    print(f"Method: Check page source for adTimeOffset/playerAds ({args.recheck_rounds} loads per video)")
    print()

    async def run_detection():
        detector = DOMDetector(headless=False, loads_per_video=args.recheck_rounds)
        await detector.setup()

        try:
            def progress_callback(current, total, video_id, result):
                verdict = "Yes" if result.has_ads else "No"
                detail = f"offset={result.has_adTimeOffset}, playerAds={result.has_playerAds}"
                print(f"[{current}/{total}] {video_id}: DOM={verdict} ({detail}, "
                      f"loads_with_ads={result.loads_with_ads}/{result.total_loads})")

            results = await detector.detect_batch(
                videos_to_process,
                progress_callback=progress_callback,
            )
            return results
        finally:
            await detector.cleanup()

    results = asyncio.run(run_detection())

    # Update ad_status in video_urls.csv
    if 'ad_status' not in df.columns:
        df['ad_status'] = ''

    for idx, video_id in zip(video_indices, videos_to_process):
        if video_id in results:
            r = results[video_id]
            df.at[idx, 'ad_status'] = 'Yes' if r.has_ads else 'No'

    df.to_csv(input_csv, index=False)
    print(f"\nUpdated {input_csv} with ad_status from DOM detection")

    # Save detailed results CSV
    rows = []
    for video_id, r in results.items():
        # Collect errors from individual loads
        load_errors = [f.get('error') for f in r.raw_findings if f.get('error')]
        error_str = '; '.join(load_errors) if load_errors else ''

        rows.append({
            'video_id': video_id,
            'dom_verdict': 'Yes' if r.has_ads else 'No',
            'dom_adTimeOffset': 'Yes' if r.has_adTimeOffset else 'No',
            'dom_playerAds': 'Yes' if r.has_playerAds else 'No',
            'dom_loads_with_ads': r.loads_with_ads,
            'dom_total_loads': r.total_loads,
            'dom_error': error_str,
        })

    results_df = pd.DataFrame(rows)
    results_df.to_csv(output_csv, index=False)
    print(f"Saved detailed DOM results to {output_csv}")

    # Print summary
    yes_count = sum(1 for r in results.values() if r.has_ads)
    no_count = len(results) - yes_count
    error_count = sum(1 for r in results.values()
                      if any(f.get('error') for f in r.raw_findings))

    print(f"\n{'='*50}")
    print("DOM DETECTION SUMMARY")
    print(f"{'='*50}")
    print(f"Videos processed:      {len(results)}")
    print(f"With ad infrastructure: {yes_count}")
    print(f"Without:               {no_count}")
    print(f"Loads per video:       {args.recheck_rounds}")
    if error_count:
        print(f"Videos with errors:    {error_count}")


if __name__ == "__main__":
    # Single video mode: pass a video ID as argument (not a flag)
    if len(sys.argv) == 2 and not sys.argv[1].startswith('--'):
        video_id = sys.argv[1]
        print(f"DOM detection for video: {video_id}")
        print("(This requires a visible browser window)")
        print()

        result = detect_dom_sync(video_id, headless=False)

        print("\n=== DOM Detection Results ===")
        print(f"Video ID:       {video_id}")
        print(f"adTimeOffset:   {result.has_adTimeOffset}")
        print(f"playerAds:      {result.has_playerAds}")
        print(f"Has ads (DOM):  {result.has_ads}")
        print(f"Loads with ads: {result.loads_with_ads}/{result.total_loads}")
        print(f"Conclusive:     {result.is_conclusive}")

        if result.raw_findings:
            print("\nPer-load details:")
            for f in result.raw_findings:
                status = "AD FOUND" if (f['adTimeOffset'] or f['playerAds']) else "clean"
                err = f" [ERROR: {f['error']}]" if f.get('error') else ""
                print(f"  Load {f['load']}: {status}{err}")
    else:
        # Batch processing on video_urls.csv
        main()
