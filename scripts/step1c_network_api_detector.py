"""
Network API-Based Ad Detection for YouTube Self-Censorship Research

This script detects possible advertisements on YouTube videos by watching
the network requests made while the page is open and the video is playing.

Main idea:
- instead of checking what appears on screen, this method checks what the browser requests in the background
- it listens for ad-related request patterns such as ad_break, pagead, doubleclick, and similar signals
- it also seeks through the video timeline to increase the chance of triggering mid-roll ad requests

Important limitation:
- network signals show ad-related infrastructure/activity, but not necessarily that an ad was actually shown to the viewer
- because of that, this method is used as a supporting method, not the strongest one on its own
- in this project, ad_break is treated as the main conclusive signal, while the others are tracked for comparison

This file is kept as part of the research methodology so the three ad detection methods
can be compared in the report:
1. UI-based detection
2. DOM-based detection
3. Network API-based detection
"""

# this file was restored mainly for research comparison
# the point is to compare how effective the network method is against the ui and dom methods
#  the main python3 running is not runing this file method, this is only for comparison

# step 1c: network api-based ad detection
#
# 1. this script checks for ads by intercepting network requests while a youtube video is open
# 2. it listens to every request the page makes and checks whether the url matches known ad-related patterns
# 3. the script also plays the video and seeks to 25%, 50%, and 75% to try to trigger mid-roll ad requests
# 4. several signals are tracked, but only ad_break is used for the final Yes/No verdict
# 5. this is because other signals like pagead or doubleclick can appear even when an actual ad is not clearly delivered
# 6. so this method is useful for detecting ad-related activity in the background, but it is weaker than the ui method for proving delivery
# 7. this method is kept in the project to help compare the strengths and weaknesses of all three detection approaches


import argparse   # lets the script accept command-line arguments like flags and options
import asyncio    # needed because Playwright runs with async browser actions
import logging    # used for progress messages, warnings, and debugging output
import os         # used for file paths and folder handling
import random     # used to randomise delays, user agents, and viewport sizes
import re         # used for regex pattern matching in request urls
import sys        # used for system actions like exiting and editing sys.path

from dataclasses import dataclass, field
# dataclass makes it easier to create a clean result object
# field(default_factory=list) is used so each result gets its own empty list

from typing import Optional
# Optional means a value can either exist normally or be None

# third-party imports
import pandas as pd   # used to read and update csv files

# add project root to path for imports
# this allows the script to import config.py from the parent project folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import project configuration paths
try:
    from config import DATA_INPUT_DIR, DATA_OUTPUT_DIR
except ImportError:
    # fallback defaults if config.py is missing
    # useful when testing the file on its own
    DATA_INPUT_DIR = "data/input"
    DATA_OUTPUT_DIR = "data/output"

# check for optional stealth library
# stealth helps the browser look less automated to YouTube
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


# these are regex patterns for urls that often appear in ad-related requests
# not all of them are equally reliable, so they are tracked separately later
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

# separate patterns are kept so the script can record exactly which type of signal was seen
# this helps later analysis in the report instead of just storing one simple yes/no
AD_BREAK_PATTERN = re.compile(r'ad_break', re.IGNORECASE)
PAGEAD_PATTERN = re.compile(r'pagead', re.IGNORECASE)
DOUBLECLICK_PATTERN = re.compile(r'doubleclick\.net', re.IGNORECASE)
ADUNIT_PATTERN = re.compile(r'el=adunit', re.IGNORECASE)
ACTIVEVIEW_PATTERN = re.compile(r'/activeview\?', re.IGNORECASE)


@dataclass
class NetworkDetectionResult:
    """
    Stores the result of network-based ad detection for one video.

    The idea is to keep both:
    - the final verdict
    - the lower-level signals that led to that verdict

    This is useful because for the report we do not just want a yes/no answer,
    we also want to compare how noisy or reliable each network signal was.
    """
    ad_requests_count: int = 0                 # total number of matched ad-related requests
    ad_break_detected: bool = False            # strongest signal, used for final verdict
    pagead_detected: bool = False              # weaker signal, tracked for comparison
    doubleclick_detected: bool = False         # weaker signal, tracked for comparison
    adunit_detected: bool = False              # weaker signal, tracked for comparison
    activeview_detected: bool = False          # weaker signal, tracked for comparison
    matched_urls: list = field(default_factory=list)   # stores matched urls for debugging/review
    error: str = None                          # stores any error instead of crashing the whole run

    @property
    def has_ads(self) -> bool:
        # final verdict for this method
        # only ad_break counts as conclusive enough to mark the video as having ads
        return self.ad_break_detected


def check_url_for_ads(url: str) -> bool:
    # checks whether a request url matches any ad-related pattern at all
    # this is the first broad filter before we look at specific signals
    for pattern in NETWORK_AD_PATTERNS:
        if pattern.search(url):
            return True
    return False


class NetworkAPIDetector:
    """
    Detects ad-related activity by intercepting network requests.

    The detector opens a real browser, visits a YouTube video page,
    listens to outgoing requests, and then tries to trigger more requests
    by playing and seeking through the video.

    This method looks at background network behaviour, not visible ad playback.
    """

    # initialise detector with browser mode and logging config
    def __init__(self, headless: bool = False, log_level: int = logging.INFO):
        self.headless = headless
        self.browser = None
        self.playwright = None
        self.logger = self._setup_logger(log_level)

        # several user agents are rotated so the browser looks less repetitive
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

    # configure stdout logger with timestamp format
    def _setup_logger(self, log_level: int) -> logging.Logger:
        logger = logging.getLogger("network_api_detector")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    # pick a random user agent so each session looks a bit different
    def _random_user_agent(self) -> str:
        return random.choice(self._user_agents)

    # generate a random window size to vary the browser fingerprint
    def _random_viewport(self) -> dict:
        width = random.randint(1250, 1400)
        height = random.randint(700, 800)
        return {'width': width, 'height': height}

    # start playwright and launch the browser with anti-detection settings
    async def setup(self):
        try:
            from playwright.async_api import async_playwright

            self.logger.info("Starting browser (headless=%s)", self.headless)
            self.playwright = await async_playwright().start()

            # these launch arguments try to hide obvious automation clues
            stealth_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--incognito",
            ]

            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=stealth_args,
                channel="chrome"  # use regular Chrome for better realism
            )
            self.logger.info("Browser launched with stealth settings")

        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

    # close the browser properly so resources do not stay open
    async def cleanup(self):
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # dismiss the cookie popup because it can block interaction with the page
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
            # not fatal, because some pages may not show the consent banner
            self.logger.debug("Consent handling: %s", e)

    # play the video and jump through the timeline to try to trigger more ad-related requests
    async def _play_and_seek(self, page):
        try:
            self.logger.info("Starting playback and seek sequence")

            # start playback muted so autoplay is less likely to fail
            await page.evaluate('''() => {
                const player = document.querySelector('video');
                if (player) {
                    player.muted = true;
                    player.play().catch(() => {});
                }
            }''')

            # wait a bit in case pre-roll ad requests happen near the start
            await asyncio.sleep(3)

            # seek to different positions to try to trigger mid-roll requests
            # these points are spread out so we sample different parts of the video
            for position in [0.25, 0.5, 0.75]:
                self.logger.info("Seeking to %.0f%%", position * 100)
                await page.evaluate(f'''() => {{
                    const video = document.querySelector('video');
                    if (video && video.duration) {{
                        video.currentTime = video.duration * {position};
                    }}
                }}''')
                await asyncio.sleep(2)

            # final pause to catch any delayed requests after seeking
            await asyncio.sleep(2)

        except Exception as e:
            self.logger.warning("Playback/seek failed: %s", str(e))

    # run detection for one video from start to finish
    async def detect(self, video_id: str) -> NetworkDetectionResult:
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("Detecting ads (network) for: %s", video_id)

        result = NetworkDetectionResult()
        captured_ad_urls = []

        try:
            # create a fresh browser context so each video starts in a cleaner environment
            ua = self._random_user_agent()
            vp = self._random_viewport()
            self.logger.info("Using viewport %dx%d", vp['width'], vp['height'])
            context = await self.browser.new_context(viewport=vp, user_agent=ua)

            # remove webdriver flag because websites often use it to detect automation
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = await context.new_page()

            # apply extra stealth patches if the package is installed
            if STEALTH_AVAILABLE:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
                self.logger.info("Applied stealth patches")

            # set up the request listener before opening the page
            # this is important because some useful requests may happen very early
            def handle_request(request):
                req_url = request.url

                # first check whether this request looks ad-related at all
                if check_url_for_ads(req_url):
                    captured_ad_urls.append(req_url)

                    # then record exactly which signal(s) appeared
                    # this gives more detailed evidence than one single flag
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

            # now load the video page
            self.logger.info("Loading video page...")
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # close cookie popup if it appears
            await self._dismiss_consent(page)

            # wait so the player can finish loading properly
            await asyncio.sleep(2)

            # play and seek through the video to try to trigger more ad calls
            await self._play_and_seek(page)

            # once done, store all the matched request information
            result.ad_requests_count = len(captured_ad_urls)
            result.matched_urls = captured_ad_urls

            # log the breakdown of which signals were seen
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

        # final verdict uses only ad_break because it is treated as the most reliable network signal
        verdict_str = "Has Ads" if result.has_ads else "No Ads"
        self.logger.info("Verdict: %s (based on ad_break signal)", verdict_str)

        return result

    # run detection over many videos one by one
    async def detect_batch(self, video_ids: list, progress_callback=None) -> list:
        results = []

        for i, video_id in enumerate(video_ids):
            detection = await self.detect(video_id)
            results.append(detection)

            # optional callback lets the main function print neat progress updates
            if progress_callback:
                progress_callback(i + 1, len(video_ids), detection)

            # restart browser every 5 videos so the session stays fresher
            # this helps reduce the risk of long-session fingerprinting
            if (i + 1) % 5 == 0 and i < len(video_ids) - 1:
                self.logger.info("Restarting browser to avoid detection...")
                await self.cleanup()
                await self.setup()

            # small random gap between videos to look less robotic
            if i < len(video_ids) - 1:
                wait_time = random.uniform(5.0, 12.0)
                self.logger.info("Waiting %.1f seconds before next video...", wait_time)
                await asyncio.sleep(wait_time)

        return results


# extract the 11-character video ID from different kinds of YouTube links
def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    # if nothing matches, return the input as it is
    return url


# flatten the result object into a normal dictionary
# this makes it easy to save one row per video into a csv file
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


# main batch mode: reads video_urls.csv, runs detection, then writes results back
def main():
    # get project base folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # build input and output paths
    input_csv = os.path.join(base_dir, DATA_INPUT_DIR, "video_urls.csv")
    output_dir = os.path.join(base_dir, DATA_OUTPUT_DIR)
    output_csv = os.path.join(output_dir, "network_api_detection_results.csv")

    # stop early if the input file does not exist
    if not os.path.exists(input_csv):
        print(f"ERROR: {input_csv} not found")
        sys.exit(1)

    # make sure the output folder exists before writing files
    os.makedirs(output_dir, exist_ok=True)

    # load the dataset of youtube urls
    print("Reading video_urls.csv...")
    df = pd.read_csv(input_csv)

    if 'url' not in df.columns:
        print("ERROR: 'url' column not found in CSV")
        sys.exit(1)

    # command-line options let us choose whether to re-check videos and how many rounds to run
    parser = argparse.ArgumentParser(description='Detect ads on YouTube videos via network API monitoring')
    parser.add_argument('--recheck-no', action='store_true',
                        help='Re-check only videos where ad_status is No')
    parser.add_argument('--recheck-rounds', type=int, default=1,
                        help='Number of recheck rounds to run (default: 1)')
    args = parser.parse_args()

    # work out which videos still need processing
    # by default, skip rows that already have Yes or No in ad_status
    ads_column = df.get('ad_status', pd.Series([''] * len(df)))
    videos_to_process = []
    video_indices = []

    if args.recheck_no:
        # in recheck mode, only re-run videos that were previously labelled No
        for i, (url, existing_ad) in enumerate(zip(df['url'], ads_column)):
            if str(existing_ad).strip().lower() == 'no':
                videos_to_process.append(extract_video_id(url))
                video_indices.append(i)
    else:
        # normal mode: only process videos with no result yet
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

    print("\nStarting network API ad detection...")
    print("NOTE: This requires a visible browser window. Bot detection may interfere in headless mode.")
    print()

    async def run_detection():
        # if multiple rounds are requested, keep the strongest result across rounds
        # meaning: if any round finds ads, that video stays marked positive
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

                # merge round results:
                # if any round detects ads for a video, keep that positive result
                for vid, res in zip(videos_to_process, results):
                    if vid not in all_round_results or res.has_ads:
                        all_round_results[vid] = res

            finally:
                await detector.cleanup()

        # return results in the same order as the original input list
        return [all_round_results[vid] for vid in videos_to_process]

    results = asyncio.run(run_detection())

    # create a quick lookup map from video id to result
    results_map = {vid: res for vid, res in zip(videos_to_process, results)}

    # update ad_status in the original input csv
    if 'ad_status' not in df.columns:
        df['ad_status'] = ''

    for idx, video_id in zip(video_indices, videos_to_process):
        if video_id in results_map:
            df.at[idx, 'ad_status'] = 'Yes' if results_map[video_id].has_ads else 'No'

    # save updated input file
    df.to_csv(input_csv, index=False)
    print(f"\nUpdated {input_csv} with ad detection results")

    # save a separate detailed output file for analysis and reporting
    detailed_data = [result_to_dict(vid, res) for vid, res in zip(videos_to_process, results)]
    detailed_df = pd.DataFrame(detailed_data)
    detailed_df.to_csv(output_csv, index=False)
    print(f"Saved detailed results to {output_csv}")

    # summary counts for the batch
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

    # also show how often each weaker signal appeared
    # this is useful for comparing which signals were noisier
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
    # single video mode:
    # if the user passes one plain argument, treat it as a video id
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

        # print only the first 20 matched urls so the output does not become too long
        if result.matched_urls:
            print(f"\nMatched URLs ({len(result.matched_urls)}):")
            for u in result.matched_urls[:20]:
                print(f"  {u[:120]}")
            if len(result.matched_urls) > 20:
                print(f"  ... and {len(result.matched_urls) - 20} more")
    else:
        # otherwise run normal batch mode on video_urls.csv
        main()