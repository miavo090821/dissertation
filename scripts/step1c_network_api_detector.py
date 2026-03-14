"""
Network API-Based Ad Detection for YouTube Self-Censorship Research
====================================================================

Detects advertisements on YouTube videos by monitoring network requests
for ad-related URL patterns (ad_break, pagead, doubleclick, etc.).

Methodology:
- Uses headed browser with stealth settings to avoid bot detection
- Intercepts all network requests via page.on('request', ...)
- Plays video and seeks to 25%, 50%, 75% to trigger mid-roll ad requests
- Primary signal: ad_break pattern is the only conclusive verdict indicator

Note: This is a complementary detection method to the UI-based detector
(step1_ad_detector.py). Network signals indicate ad infrastructure requests,
which may differ from actual ad delivery observed in the UI.

Reference: YouTube Self-Censorship Research Project (RQ1 Methodology)
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


# Network request URL patterns that indicate ad-related activity
NETWORK_AD_PATTERNS = [
    re.compile(r'googlevideo\.com.*adformat', re.IGNORECASE),
    re.compile(r'ad_break', re.IGNORECASE),
    re.compile(r'pagead2\.googlesyndication', re.IGNORECASE),
    re.compile(r'doubleclick\.net', re.IGNORECASE),
    re.compile(r'youtube\.com/api/stats/ads', re.IGNORECASE),
    re.compile(r'youtube\.com/pagead/', re.IGNORECASE),
    re.compile(r'/ptracking\?', re.IGNORECASE),
    re.compile(r'adsapi\.youtube\.com', re.IGNORECASE),
    re.compile(r'el=adunit', re.IGNORECASE),
    re.compile(r'/activeview\?', re.IGNORECASE),
]

# Individual signal patterns for granular tracking
AD_BREAK_PATTERN = re.compile(r'ad_break', re.IGNORECASE)
PAGEAD_PATTERN = re.compile(r'pagead', re.IGNORECASE)
DOUBLECLICK_PATTERN = re.compile(r'doubleclick\.net', re.IGNORECASE)
ADUNIT_PATTERN = re.compile(r'el=adunit', re.IGNORECASE)
ACTIVEVIEW_PATTERN = re.compile(r'/activeview\?', re.IGNORECASE)


@dataclass
class NetworkDetectionResult:
    """
    Results from network API ad detection.

    Attributes:
        ad_requests_count: Total number of ad-related network requests observed
        ad_break_detected: True if ad_break pattern found (primary signal)
        pagead_detected: True if pagead pattern found
        doubleclick_detected: True if doubleclick.net pattern found
        adunit_detected: True if el=adunit pattern found
        activeview_detected: True if /activeview? pattern found
        matched_urls: List of matched ad-related URLs for debugging
        error: Error message if detection failed
    """
    ad_requests_count: int = 0
    ad_break_detected: bool = False
    pagead_detected: bool = False
    doubleclick_detected: bool = False
    adunit_detected: bool = False
    activeview_detected: bool = False
    matched_urls: list = field(default_factory=list)
    error: str = None

    @property
    def has_ads(self) -> bool:
        """Returns True only if ad_break was detected (conclusive signal)."""
        return self.ad_break_detected


def check_url_for_ads(url: str) -> bool:
    """Check if a URL matches any known ad-related pattern."""
    for pattern in NETWORK_AD_PATTERNS:
        if pattern.search(url):
            return True
    return False


class NetworkAPIDetector:
    """
    YouTube ad detector using network request interception.

    Uses headed Chromium browser with stealth settings to avoid bot detection.
    Monitors all network requests for ad-related URL patterns during video
    playback and seeking.

    Usage:
        detector = NetworkAPIDetector()
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
            self.logger.warning("Headless mode may trigger bot detection on YouTube!")

    # Configure stdout logger with timestamp format
    def _setup_logger(self, log_level: int) -> logging.Logger:
        logger = logging.getLogger("network_api_detector")
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

    # Play video and seek to 25/50/75% to trigger mid-roll ad requests
    async def _play_and_seek(self, page):
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

            # Wait for pre-roll ad requests
            await asyncio.sleep(3)

            # Seek to different positions to trigger mid-roll ad requests
            for position in [0.25, 0.5, 0.75]:
                self.logger.info("Seeking to %.0f%%", position * 100)
                await page.evaluate(f'''() => {{
                    const video = document.querySelector('video');
                    if (video && video.duration) {{
                        video.currentTime = video.duration * {position};
                    }}
                }}''')
                await asyncio.sleep(2)

            # Final wait for any trailing ad requests
            await asyncio.sleep(2)

        except Exception as e:
            self.logger.warning("Playback/seek failed: %s", str(e))

    # Run full network ad detection for a single video
    async def detect(self, video_id: str) -> NetworkDetectionResult:
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("Detecting ads (network) for: %s", video_id)

        result = NetworkDetectionResult()
        captured_ad_urls = []

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

            # Set up network request listener before navigation
            def handle_request(request):
                req_url = request.url
                if check_url_for_ads(req_url):
                    captured_ad_urls.append(req_url)

                    # Track individual signal patterns
                    if AD_BREAK_PATTERN.search(req_url):
                        result.ad_break_detected = True
                    if PAGEAD_PATTERN.search(req_url):
                        result.pagead_detected = True
                    if DOUBLECLICK_PATTERN.search(req_url):
                        result.doubleclick_detected = True
                    if ADUNIT_PATTERN.search(req_url):
                        result.adunit_detected = True
                    if ACTIVEVIEW_PATTERN.search(req_url):
                        result.activeview_detected = True

            page.on('request', handle_request)

            # Navigate to video
            self.logger.info("Loading video page...")
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Dismiss cookie consent
            await self._dismiss_consent(page)

            # Wait for player to initialize
            await asyncio.sleep(2)

            # Play video and seek to trigger mid-roll ad requests
            await self._play_and_seek(page)

            # Finalise results from captured URLs
            result.ad_requests_count = len(captured_ad_urls)
            result.matched_urls = captured_ad_urls

            # Log network detection summary
            self.logger.info(
                "Network summary: ad_requests=%d, ad_break=%s, pagead=%s, "
                "doubleclick=%s, adunit=%s, activeview=%s",
                result.ad_requests_count,
                result.ad_break_detected,
                result.pagead_detected,
                result.doubleclick_detected,
                result.adunit_detected,
                result.activeview_detected,
            )

            await context.close()

        except Exception as e:
            result.error = str(e)
            self.logger.error("Detection failed: %s", result.error)

        verdict_str = "Has Ads" if result.has_ads else "No Ads"
        self.logger.info("Verdict: %s (based on ad_break signal)", verdict_str)

        return result

    # Detect ads for a list of videos with progress reporting
    async def detect_batch(self, video_ids: list, progress_callback=None) -> list:
        results = []

        for i, video_id in enumerate(video_ids):
            detection = await self.detect(video_id)
            results.append(detection)

            if progress_callback:
                progress_callback(i + 1, len(video_ids), detection)

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


# Extract the 11-character video ID from a YouTube URL
def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url


# Convert a NetworkDetectionResult to a flat dictionary for CSV export
def result_to_dict(video_id: str, result: NetworkDetectionResult) -> dict:
    return {
        'video_id': video_id,
        'network_verdict': 'Yes' if result.has_ads else 'No',
        'network_ad_requests': result.ad_requests_count,
        'network_ad_break': 'Yes' if result.ad_break_detected else 'No',
        'network_pagead': 'Yes' if result.pagead_detected else 'No',
        'network_doubleclick': 'Yes' if result.doubleclick_detected else 'No',
        'network_adunit': 'Yes' if result.adunit_detected else 'No',
        'network_activeview': 'Yes' if result.activeview_detected else 'No',
        'network_error': result.error or '',
    }


# Batch network ad detection on video_urls.csv
def main():
    # Get base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Resolve paths
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_csv = os.path.join(output_dir, "network_api_detection_results.csv")

    # Check input exists
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} not found")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Read video URLs
    print("Reading video_urls.csv...")
    df = pd.read_csv(input_csv)

    if 'url' not in df.columns:
        print("ERROR: 'url' column not found in CSV")
        sys.exit(1)

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Detect ads on YouTube videos via network API monitoring')
    parser.add_argument('--recheck-no', action='store_true',
                        help='Re-check only videos where ad_status is No')
    parser.add_argument('--recheck-rounds', type=int, default=1,
                        help='Number of recheck rounds to run (default: 1)')
    args = parser.parse_args()

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
        print(f"Re-check mode: processing videos with ad_status = No")
        print(f"Recheck rounds: {args.recheck_rounds}")
    if skipped > 0:
        print(f"Skipping {skipped} videos")
    print(f"Processing {len(videos_to_process)} videos")

    if not videos_to_process:
        print("All videos already processed. Nothing to do.")
        return

    # Run detection
    print("\nStarting network API ad detection...")
    print("NOTE: This requires a visible browser window. Bot detection may interfere in headless mode.")
    print()

    async def run_detection():
        all_round_results = {}

        for round_num in range(1, args.recheck_rounds + 1):
            if args.recheck_rounds > 1:
                print(f"\n--- Round {round_num}/{args.recheck_rounds} ---")

            detector = NetworkAPIDetector(headless=False)
            await detector.setup()

            try:
                def progress_callback(current, total, result):
                    verdict = "Yes" if result.has_ads else "No"
                    ad_reqs = result.ad_requests_count
                    print(f"[{current}/{total}] {videos_to_process[current - 1]}: "
                          f"{verdict} ({ad_reqs} ad requests)")

                results = await detector.detect_batch(
                    videos_to_process,
                    progress_callback=progress_callback
                )

                # Merge results: if any round detects ads, keep that result
                for vid, res in zip(videos_to_process, results):
                    if vid not in all_round_results or res.has_ads:
                        all_round_results[vid] = res

            finally:
                await detector.cleanup()

        # Return results in original order
        return [all_round_results[vid] for vid in videos_to_process]

    results = asyncio.run(run_detection())

    # Create results mapping
    results_map = {vid: res for vid, res in zip(videos_to_process, results)}

    # Update ad_status in video_urls.csv
    if 'ad_status' not in df.columns:
        df['ad_status'] = ''

    for idx, video_id in zip(video_indices, videos_to_process):
        if video_id in results_map:
            df.at[idx, 'ad_status'] = 'Yes' if results_map[video_id].has_ads else 'No'

    # Save updated CSV back to input
    df.to_csv(input_csv, index=False)
    print(f"\nUpdated {input_csv} with ad detection results")

    # Save detailed results to output
    detailed_data = [result_to_dict(vid, res) for vid, res in zip(videos_to_process, results)]
    detailed_df = pd.DataFrame(detailed_data)
    detailed_df.to_csv(output_csv, index=False)
    print(f"Saved detailed results to {output_csv}")

    # Print summary
    yes_count = sum(1 for r in results if r.has_ads)
    no_count = len(results) - yes_count
    error_count = sum(1 for r in results if r.error)

    print(f"\n{'='*40}")
    print("SUMMARY")
    print(f"{'='*40}")
    print(f"Videos processed: {len(results)}")
    print(f"With ads (ad_break): {yes_count}")
    print(f"Without ads:         {no_count}")
    if error_count:
        print(f"Errors:              {error_count}")

    # Additional signal breakdown
    pagead_count = sum(1 for r in results if r.pagead_detected)
    doubleclick_count = sum(1 for r in results if r.doubleclick_detected)
    adunit_count = sum(1 for r in results if r.adunit_detected)
    activeview_count = sum(1 for r in results if r.activeview_detected)

    print(f"\nSignal breakdown:")
    print(f"  ad_break:    {yes_count}")
    print(f"  pagead:      {pagead_count}")
    print(f"  doubleclick: {doubleclick_count}")
    print(f"  adunit:      {adunit_count}")
    print(f"  activeview:  {activeview_count}")


if __name__ == "__main__":
    # Single video mode: pass a video ID as argument (not a flag)
    if len(sys.argv) == 2 and not sys.argv[1].startswith('--'):
        video_id = sys.argv[1]
        print(f"Detecting ads (network API) for video: {video_id}")
        print("(This requires a visible browser window)")
        print()

        async def _detect_single():
            detector = NetworkAPIDetector(headless=False)
            await detector.setup()
            try:
                return await detector.detect(video_id)
            finally:
                await detector.cleanup()

        result = asyncio.run(_detect_single())

        print("\n=== Network Detection Results ===")
        print(f"Video ID: {video_id}")
        print(f"\nNetwork Signals:")
        print(f"  Ad requests:  {result.ad_requests_count}")
        print(f"  ad_break:     {result.ad_break_detected}")
        print(f"  pagead:       {result.pagead_detected}")
        print(f"  doubleclick:  {result.doubleclick_detected}")
        print(f"  adunit:       {result.adunit_detected}")
        print(f"  activeview:   {result.activeview_detected}")
        print(f"\nVerdict: {'Has Ads' if result.has_ads else 'No Ads'} (based on ad_break)")
        if result.error:
            print(f"Error: {result.error}")
        if result.matched_urls:
            print(f"\nMatched URLs ({len(result.matched_urls)}):")
            for u in result.matched_urls[:20]:
                print(f"  {u[:120]}")
            if len(result.matched_urls) > 20:
                print(f"  ... and {len(result.matched_urls) - 20} more")
    else:
        # Batch processing on video_urls.csv (supports --recheck-no and --recheck-rounds flags)
        main()
