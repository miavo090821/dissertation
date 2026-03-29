# step 1b: dom-based ad detection
#
# 1. this script checks whether youtube ad-related variables appear in the page html/dom

# 2. unlike the ui method in step 1, this does NOT confirm that an ad was actually shown to the viewer

# 3. instead, it checks for ad infrastructure in the page source, 
# mainly adTimeOffset and playerAds

# 4. each video page is loaded 5 times because youtube responses can vary between loads

# 5. if either variable appears in any load, the video is marked as 
# having ads at the dom level

# 6. this follows the dunna et al. (2022) style approach and is kept 
# mainly for method comparison

# 7. the goal is to compare this dom method against the ui method 
# and other detection methods in the report
#
# important idea:
# - ui method = checks actual ad delivery on screen
# - dom method = checks whether ad-related variables exist in the page source
# so this script is useful for comparison, but it is weaker evidence than the ui method

import argparse     # lets us add command-line options like --recheck-no
import asyncio      # needed because playwright works asynchronously
import logging      # used to print structured logs with timestamps
import os           # handles file paths and folder creation
import random       # used to randomise user agents, viewports, and delays
import re           # used for regex matching in urls and html content
import sys          # used for system path changes and exiting on errors
from dataclasses import dataclass, field   # makes a clean result object for storing detection results
from typing import Optional                # type hint support (not heavily used here)

import pandas as pd   # used to read and update the csv files

# need parent dir on path so we can import config
# this makes python able to find config.py from one folder above
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # these paths are normally stored in config.py
    from config import DATA_INPUT_DIR, DATA_OUTPUT_DIR
except ImportError:
    # fallback paths in case config.py cannot be imported
    DATA_INPUT_DIR = "data/input"
    DATA_OUTPUT_DIR = "data/output"

# stealth library helps avoid bot detection but it's optional
# if it is not installed, the script can still run without it
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


# regex patterns for the two dom indicators from paper 1 (dunna et al., 2022)
# these patterns search the html page source for ad-related variable names
DOM_INDICATORS = {
    'adTimeOffset': re.compile(r'["\']?adTimeOffset["\']?\s*:', re.IGNORECASE),
    'playerAds': re.compile(r'["\']?playerAds["\']?\s*:', re.IGNORECASE),
}

# default number of times we reload each video page
# repeated loads help reduce the risk of a one-off false negative
DEFAULT_LOADS_PER_VIDEO = 5


@dataclass
class DOMDetectionResult:
    """stores aggregated results from loading a video page multiple times and checking for ad dom variables."""
    # whether adTimeOffset was found in any of the loads
    has_adTimeOffset: bool = False

    # whether playerAds was found in any of the loads
    has_playerAds: bool = False

    # number of loads where at least one ad indicator was found
    loads_with_ads: int = 0

    # total number of loads completed, including failed ones
    total_loads: int = 0

    # detailed per-load findings so we can inspect exactly what happened
    raw_findings: list = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        """true if either dom indicator was found in any load."""
        # overall dom verdict:
        # if either indicator appears even once, we classify the video as 'has ads' at dom level
        return self.has_adTimeOffset or self.has_playerAds

    @property
    def is_conclusive(self) -> bool:
        """true if we completed all 5 loads."""
        # this checks whether we finished the full intended number of loads
        return self.total_loads >= DEFAULT_LOADS_PER_VIDEO


def check_dom_for_ads(page_source: str) -> dict:
    """runs the regex patterns against the page html to see if ad variables exist."""
    
    # store results for each indicator separately
    findings = {}

    # test each regex pattern against the page source html
    for name, pattern in DOM_INDICATORS.items():
        findings[name] = bool(pattern.search(page_source))

    return findings


# same video id extraction as step1
def extract_video_id(url: str) -> str:
    """pulls the 11-char video id from a youtube url."""
    
    # support normal watch urls, short youtu.be urls, embed urls,
    # or direct raw video ids
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # if no pattern matches, just return the input as-is
    # this avoids crashing and lets later steps handle the problem
    return url


class DOMDetector:
    """browser-based dom ad detector. uses the same stealth chromium setup as step1
    but instead of looking at ui elements, it grabs the page source and searches
    for adTimeOffset/playerAds variables with regex."""

    def __init__(self, headless: bool = False, loads_per_video: int = DEFAULT_LOADS_PER_VIDEO,
                 log_level: int = logging.INFO):
        # headless=False is safer here because youtube may detect automation more easily in headless mode
        self.headless = headless

        # number of times each video page will be loaded
        self.loads_per_video = loads_per_video

        # these will be filled later when playwright starts
        self.browser = None
        self.playwright = None

        # create logger for progress and debugging messages
        self.logger = self._setup_logger(log_level)

        # rotate user agents so youtube doesn't fingerprint us
        # changing user agents helps the browser look less repetitive
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

    def _setup_logger(self, log_level: int) -> logging.Logger:
        """sets up a simple stdout logger with timestamps."""
        logger = logging.getLogger("dom_detector")

        # only add a handler once, otherwise repeated runs can duplicate log lines
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        logger.setLevel(log_level)
        return logger

    def _random_user_agent(self) -> str:
        """picks a random ua from the list."""
        return random.choice(self._user_agents)

    def _random_viewport(self) -> dict:
        """randomises window size to vary the browser fingerprint."""
        width = random.randint(1250, 1400)
        height = random.randint(700, 800)
        return {'width': width, 'height': height}

    async def setup(self):
        """launches chromium with anti-detection args, same config as step1."""
        try:
            from playwright.async_api import async_playwright

            self.logger.info("Starting browser (headless=%s)", self.headless)
            self.playwright = await async_playwright().start()

            # launch arguments that try to reduce obvious automation signals
            stealth_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--incognito",
            ]

            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=stealth_args,
                channel="chrome"
            )
            self.logger.info("Browser launched with stealth settings")

        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    async def cleanup(self):
        """shuts down browser and releases playwright resources."""
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def _dismiss_consent(self, page):
        """clicks the cookie consent banner if youtube shows one."""
        try:
            # small wait so the page has time to fully render the consent popup
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
                    # ignore selector-specific failures and try the next selector
                    continue

        except Exception as e:
            # not critical if this fails, because some pages may not show the banner
            self.logger.debug("Consent handling: %s", e)

    async def detect(self, video_id: str) -> DOMDetectionResult:
        """loads the video page multiple times (default 5) and checks page source
        for adTimeOffset/playerAds on each load. aggregates findings across all loads."""
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("DOM detection for %s (%d loads)", video_id, self.loads_per_video)

        # result object that will collect findings across all page loads
        result = DOMDetectionResult()

        for load_num in range(1, self.loads_per_video + 1):
            load_label = f"load {load_num}/{self.loads_per_video}"
            self.logger.info("[%s] %s - starting", video_id, load_label)

            try:
                # fresh context each time with randomised fingerprint
                # using a new browser context per load helps reduce carry-over effects
                ua = self._random_user_agent()
                vp = self._random_viewport()
                context = await self.browser.new_context(viewport=vp, user_agent=ua)

                # hide the webdriver flag so youtube doesn't know we're automated
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                page = await context.new_page()

                # apply stealth if the package is available
                if STEALTH_AVAILABLE:
                    stealth = Stealth()
                    await stealth.apply_stealth_async(page)

                # load the video page and wait for the network to settle
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # remove cookie popup if it appears, otherwise it may interfere
                await self._dismiss_consent(page)

                # give youtube's js time to populate the ad variables
                # this matters because some variables may appear slightly after first render
                await asyncio.sleep(3)

                # get the full html content of the page
                page_source = await page.content()

                # check whether the ad-related variables appear in that html
                findings = check_dom_for_ads(page_source)

                # if any indicator is found, this load counts as a positive dom load
                load_has_ads = any(findings.values())
                if load_has_ads:
                    result.loads_with_ads += 1

                # once found in any load, keep the overall flag as True
                if findings.get('adTimeOffset'):
                    result.has_adTimeOffset = True
                if findings.get('playerAds'):
                    result.has_playerAds = True

                # record that this load completed successfully
                result.total_loads += 1

                # save the detailed findings for this individual load
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

                # close this context before the next load
                await context.close()

            except Exception as e:
                # if a load fails, still record it so the results stay transparent
                self.logger.warning("[%s] %s - error: %s", video_id, load_label, e)
                result.total_loads += 1
                result.raw_findings.append({
                    'load': load_num,
                    'adTimeOffset': False,
                    'playerAds': False,
                    'error': str(e),
                })

            # small delay between loads (skip after the last one)
            # adds a more human-like gap between requests
            if load_num < self.loads_per_video:
                delay = random.uniform(2.0, 4.0)
                await asyncio.sleep(delay)

        # final summary for this video after all loads are finished
        self.logger.info(
            "[%s] DOM verdict: has_ads=%s (adTimeOffset=%s, playerAds=%s, "
            "loads_with_ads=%d/%d)",
            video_id, result.has_ads, result.has_adTimeOffset, result.has_playerAds,
            result.loads_with_ads, result.total_loads,
        )

        return result

    async def detect_batch(self, video_ids: list, progress_callback=None) -> dict:
        """runs dom detection on a list of videos, restarts browser every 5 to stay fresh."""
        results = {}

        for i, video_id in enumerate(video_ids):
            # run detection for one video at a time
            result = self.detect(video_id)
            if asyncio.iscoroutine(result):
                result = await result
            results[video_id] = result

            # optional callback so the main script can print progress neatly
            if progress_callback:
                progress_callback(i + 1, len(video_ids), video_id, result)

            # restart browser every 5 videos for a fresh fingerprint
            # this helps reduce long-session detection or stale browser behaviour
            if (i + 1) % 5 == 0 and i < len(video_ids) - 1:
                self.logger.info("Restarting browser to refresh fingerprint...")
                await self.cleanup()
                await self.setup()

            # wait a bit before the next video so requests are not too robotic
            if i < len(video_ids) - 1:
                wait_time = random.uniform(5.0, 12.0)
                self.logger.info("Waiting %.1f seconds before next video...", wait_time)
                await asyncio.sleep(wait_time)

        return results


def detect_dom_sync(video_id: str, headless: bool = False,
                    loads_per_video: int = DEFAULT_LOADS_PER_VIDEO) -> DOMDetectionResult:
    """sync wrapper so you can call dom detection without async boilerplate."""
    
    # this helper makes it easier to run dom detection from normal synchronous code
    async def _detect():
        detector = DOMDetector(headless=headless, loads_per_video=loads_per_video)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()

    return asyncio.run(_detect())


def main():
    """batch dom detection on video_urls.csv, optionally rechecking only No videos."""

    # build absolute file paths relative to the project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_csv = os.path.join(output_dir, "dom_detection_results.csv")

    # stop early if the input file does not exist
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} not found")
        sys.exit(1)

    # make sure output folder exists before writing files to it
    os.makedirs(output_dir, exist_ok=True)

    # command-line options for controlling rechecks and number of loads
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

    print("Reading video_urls.csv...")
    df = pd.read_csv(input_csv)

    # make sure the csv has a url column, otherwise the script cannot continue
    if 'url' not in df.columns:
        print("ERROR: 'url' column not found in CSV")
        sys.exit(1)

    # figure out which videos still need processing
    # ad_status is used so we do not redo everything unnecessarily
    ads_column = df.get('ad_status', pd.Series([''] * len(df)))
    videos_to_process = []
    video_indices = []

    if args.recheck_no:
        # recheck only the videos that were previously marked as No
        for i, (url, existing_ad) in enumerate(zip(df['url'], ads_column)):
            if str(existing_ad).strip().lower() == 'no':
                videos_to_process.append(extract_video_id(url))
                video_indices.append(i)
    else:
        # default: only process videos with no ad_status yet
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

    print("\nStarting DOM-based ad detection...")
    print("NOTE: This requires a visible browser window.")
    print(f"Method: Check page source for adTimeOffset/playerAds ({args.recheck_rounds} loads per video)")
    print()

    async def run_detection():
        detector = DOMDetector(headless=False, loads_per_video=args.recheck_rounds)
        await detector.setup()

        try:
            def progress_callback(current, total, video_id, result):
                # simple live progress summary for each finished video
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

    # run the full async batch process
    results = asyncio.run(run_detection())

    # write ad_status back to the input csv
    # this updates the original dataset with the dom verdict
    if 'ad_status' not in df.columns:
        df['ad_status'] = ''

    for idx, video_id in zip(video_indices, videos_to_process):
        if video_id in results:
            r = results[video_id]
            df.at[idx, 'ad_status'] = 'Yes' if r.has_ads else 'No'

    df.to_csv(input_csv, index=False)
    print(f"\nUpdated {input_csv} with ad_status from DOM detection")

    # save per-video detailed results
    # this output is useful for later analysis and method comparison
    rows = []
    for video_id, r in results.items():
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

    # count up summary statistics across all processed videos
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
    # single video mode: just pass the video id directly
    # example: python script.py dQw4w9WgXcQ
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
                # mark a load as positive if either dom variable appeared
                status = "AD FOUND" if (f['adTimeOffset'] or f['playerAds']) else "clean"
                err = f" [ERROR: {f['error']}]" if f.get('error') else ""
                print(f"  Load {f['load']}: {status}{err}")
    else:
        # normal batch mode
        main()