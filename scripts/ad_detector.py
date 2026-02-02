# As HTML/DOM and Network API signals can be inconsistent in detecting ads in videos,
# we also use a stealth UI/UX approach that detects ads via the YouTube player interface.
# Downside: some videos that are actually "no-ads" can still show ads occasionally.
# Mitigation: the "no-ads" bucket should be small, and we have a manual verification step
# to double-check detections quickly.
import re
import sys
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, List, Dict

try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


# We set up the method by using Enum
class DetectionMethod(Enum):
    DOM = "dom"
    NETWORK = "network"
    UI = "ui"
    BOTH = "both"
    CONFLICT = "conflict"
    NONE = "none"


# DOM indicators from Paper 1 (Dunna et al., 2022)
DOM_ADTIME_PATTERN = re.compile(r'["\']?adTimeOffset["\']?\s*:', re.IGNORECASE)
DOM_PLAYERADS_PATTERN = re.compile(r'["\']?playerAds["\']?\s*:', re.IGNORECASE)

# Network patterns (we only treat ad_break as evidence for ads, but we also log others)
AD_BREAK_PATTERN = re.compile(r"ad_break", re.IGNORECASE)
PAGEAD_PATTERN = re.compile(r"pagead", re.IGNORECASE)
DOUBLECLICK_PATTERN = re.compile(r"doubleclick\.net", re.IGNORECASE)
ADUNIT_PATTERN = re.compile(r"el=adunit", re.IGNORECASE)
ACTIVEVIEW_PATTERN = re.compile(r"/activeview\?", re.IGNORECASE)

# Pattern set used to mark a request as "ad-related" (for counting / debugging)
NETWORK_AD_PATTERNS: List[re.Pattern] = [
    re.compile(r"googlevideo\.com.*adformat", re.IGNORECASE),
    AD_BREAK_PATTERN,
    re.compile(r"pagead2\.googlesyndication", re.IGNORECASE),
    DOUBLECLICK_PATTERN,
    re.compile(r"youtube\.com/api/stats/ads", re.IGNORECASE),
    re.compile(r"youtube\.com/pagead/", re.IGNORECASE),
    re.compile(r"/ptracking\?", re.IGNORECASE),
    re.compile(r"adsapi\.youtube\.com", re.IGNORECASE),
    ADUNIT_PATTERN,
    ACTIVEVIEW_PATTERN,
]


@dataclass
class DOMDetectionResult:
    has_adTimeOffset: bool = False
    has_playerAds: bool = False
    loads_with_ads: int = 0  # Paper 1 uses 5 loads; "0/5" is used as non-monetised proxy
    total_loads: int = 0
    raw_findings: List[Dict] = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        # Video has ads if either variable appears in any load
        return self.has_adTimeOffset or self.has_playerAds

    @property
    def is_conclusive(self) -> bool:
        # Conclusive if we completed the intended number of loads (caller decides threshold)
        return self.total_loads > 0


# When inspecting the page, we can see ad_break in the Network API requests.
# Here we track ad breaks and also log related ad domains/params for debugging.
@dataclass
class NetworkDetectionResult:
    ad_requests_count: int = 0
    ad_break_detected: bool = False
    pagead_detected: bool = False
    doubleclick_detected: bool = False
    adunit_detected: bool = False
    activeview_detected: bool = False
    matched_urls: List[str] = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        # Treat ad_break as the "hard" network evidence for ads
        return self.ad_break_detected


# Stealth method: check the UI/UX of YouTube player for ad markers shown
@dataclass
class UIAdDetectionResult:
    ad_label: bool = False
    sponsored_label: bool = False
    ad_image_view_model: bool = False
    skip_button: bool = False
    ad_countdown: bool = False
    ad_overlay: bool = False
    ad_showing_class: bool = False
    raw_markers: List[Dict] = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        return any(
            [
                self.ad_label,
                self.sponsored_label,
                self.ad_image_view_model,
                self.skip_button,
                self.ad_countdown,
                self.ad_overlay,
                self.ad_showing_class,
            ]
        )

@dataclass
class AdDetectionResult:
    video_id: str
    dom_result: DOMDetectionResult
    network_result: NetworkDetectionResult
    ui_result: UIAdDetectionResult
    verdict: Optional[bool] = None  # True=has ads, False=no ads, None=uncertain
    method: DetectionMethod = DetectionMethod.NONE
    confidence: str = "low"  # low, medium, high
    error: Optional[str] = None

    # Convert to dictionary for CSV export
    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            # DOM results
            "auto_dom_ads": "Yes" if self.dom_result.has_ads else "No",
            "auto_dom_adTimeOffset": "Yes" if self.dom_result.has_adTimeOffset else "No",
            "auto_dom_playerAds": "Yes" if self.dom_result.has_playerAds else "No",
            "auto_dom_loads": f"{self.dom_result.loads_with_ads}/{self.dom_result.total_loads}",
            # Network results
            "auto_network_ads": "Yes" if self.network_result.has_ads else "No",
            "auto_network_count": self.network_result.ad_requests_count,
            "auto_network_ad_break": "Yes" if self.network_result.ad_break_detected else "No",
            # UI results
            "auto_ui_ads": "Yes" if self.ui_result.has_ads else "No",
            "auto_ui_ad_label": "Yes" if self.ui_result.ad_label else "No",
            "auto_ui_sponsored_label": "Yes" if self.ui_result.sponsored_label else "No",
            "auto_ui_ad_image_view_model": "Yes" if self.ui_result.ad_image_view_model else "No",
            "auto_ui_skip_button": "Yes" if self.ui_result.skip_button else "No",
            "auto_ui_ad_countdown": "Yes" if self.ui_result.ad_countdown else "No",
            "auto_ui_ad_overlay": "Yes" if self.ui_result.ad_overlay else "No",
            "auto_ui_ad_showing_class": "Yes" if self.ui_result.ad_showing_class else "No",
            # Combined verdict
            "auto_verdict": "Yes"
            if self.verdict
            else ("No" if self.verdict is False else "Uncertain"),
            "auto_method": self.method.value,
            "auto_confidence": self.confidence,
            "auto_error": self.error or "",
        }


def check_dom_for_ads(page_source: str) -> Dict[str, bool]:
    # Paper 1 DOM heuristics: adTimeOffset + playerAds
    if not page_source:
        return {"has_adTimeOffset": False, "has_playerAds": False}
    return {
        "has_adTimeOffset": bool(DOM_ADTIME_PATTERN.search(page_source)),
        "has_playerAds": bool(DOM_PLAYERADS_PATTERN.search(page_source)),
    }


def check_url_for_ads(url: str) -> Dict[str, object]:
    # Check if URL matches ad-related patterns, and categorise key sub-signals
    matched_pattern = None
    is_ad_related = False
    for p in NETWORK_AD_PATTERNS:
        if p.search(url):
            matched_pattern = p.pattern
            is_ad_related = True
            break

    return {
        "is_ad_related": is_ad_related,
        "matched_pattern": matched_pattern,
        "ad_break": bool(AD_BREAK_PATTERN.search(url)),
        "pagead": bool(PAGEAD_PATTERN.search(url)),
        "doubleclick": bool(DOUBLECLICK_PATTERN.search(url)),
        "adunit": bool(ADUNIT_PATTERN.search(url)),
        "activeview": bool(ACTIVEVIEW_PATTERN.search(url)),
    }


def determine_verdict(
    dom_result: DOMDetectionResult,
    network_result: NetworkDetectionResult,
    ui_result: Optional[UIAdDetectionResult] = None,
) -> Tuple[Optional[bool], DetectionMethod, str]:
    # Priority (intended): UI "Sponsored" label > network ad_break > other UI markers > DOM
    ui_result = ui_result or UIAdDetectionResult()

    if ui_result.sponsored_label:
        return True, DetectionMethod.UI, "high"
    if network_result.ad_break_detected:
        return True, DetectionMethod.NETWORK, "high"
    if ui_result.has_ads:
        return True, DetectionMethod.UI, "medium"
    if dom_result.has_ads:
        return True, DetectionMethod.DOM, "medium"

    # Assume no ads if nothing detected (manual verification can still override)
    return False, DetectionMethod.NONE, "medium"


class AdDetector:
    def __init__(
        self,
        headless: bool = False,
        num_loads: int = 1,
        log_level: int = logging.INFO,
        explicit_incognito: bool = True,
        chrome_channel: bool = True,
    ):
        self.headless = headless  # Store launch mode
        self.num_loads = num_loads  # Paper 1 suggests 5, but you can tune for cost/time
        self.playwright = None  # Will hold the Playwright controller once started
        self.browser = None  # Will hold the launched browser instance
        self.explicit_incognito = explicit_incognito
        self.chrome_channel = chrome_channel
        self.logger = self._setup_logger(log_level)

    # Initialise Playwright and launch a Chromium browser.
    # This should be called once before running detections to avoid repeated startup cost.
    async def setup(self):
        from playwright.async_api import async_playwright

        self.logger.info(
            "Starting Playwright (headless=%s, incognito=%s, chrome_channel=%s)",
            self.headless,
            self.explicit_incognito,
            self.chrome_channel,
        )

        self.playwright = await async_playwright().start()

        # Stealth args (basic)
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-first-run",
        ]
        if self.explicit_incognito:
            args.append("--incognito")

        launch_kwargs = {"headless": self.headless, "args": args}
        if self.chrome_channel:
            launch_kwargs["channel"] = "chrome"

        self.browser = await self.playwright.chromium.launch(**launch_kwargs)
        self.logger.info("Browser launched")

    async def cleanup(self):
        # Close browser and stop Playwright
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.logger.info("Playwright closed")

    def _setup_logger(self, log_level: int) -> logging.Logger:
        # Console logger (kept simple for CLI runs)
        logger = logging.getLogger("ad_detector")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger

    async def _dismiss_consent(self, page):
        # Dismiss Google/YouTube cookie consent if present (can block player/UI)
        try:
            await asyncio.sleep(1)
            selectors = [
                'button:has-text("Accept all")',
                '[aria-label="Accept the use of cookies and other data for the purposes described"]',
            ]
            for sel in selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        self.logger.info("Consent banner detected; clicking: %s", sel)
                        await btn.click()
                        await asyncio.sleep(1)
                        return
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug("Consent handling failed: %s", e)

    async def _update_ui_markers(
        self, page, ui_result: UIAdDetectionResult, context: str = ""
    ):
        # Check player UI/UX for ad markers and update ui_result
        try:
            markers = await page.evaluate(
                """() => {
                    const player = document.querySelector('.html5-video-player');
                    const adShowing = !!(player && player.classList.contains('ad-showing'));

                    const badgeTexts = Array.from(document.querySelectorAll('.ytp-ad-badge__text'))
                        .map(el => (el.textContent || '').trim().toLowerCase());

                    const hasAdLabel = badgeTexts.some(t => t === 'ad');

                    const hasSponsoredBadge = badgeTexts.some(t => t.includes('sponsored'));
                    const sponsoredInPlayer = (() => {
                        if (!player) return false;
                        const nodes = player.querySelectorAll('*');
                        for (const node of nodes) {
                            const text = (node.textContent || '').trim().toLowerCase();
                            if (text === 'sponsored' || text.includes('sponsored')) return true;
                        }
                        return false;
                    })();

                    const hasAdImageViewModel = !!document.querySelector('ad-image-view-model');
                    const skipButton = !!document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern');
                    const adCountdown = !!document.querySelector(
                        '.ytp-ad-preview-container, .ytp-ad-timed-pie-countdown-container, .ytp-ad-duration-remaining'
                    );
                    const adOverlay = !!document.querySelector('.ytp-ad-overlay-container, .ytp-ad-overlay-slot');

                    const hasSponsored = (hasSponsoredBadge || sponsoredInPlayer);
                    const adPlaying = adShowing || hasAdLabel || hasSponsored || hasAdImageViewModel || skipButton || adCountdown || adOverlay;

                    return {
                        adShowing,
                        hasAdLabel,
                        hasSponsored,
                        hasAdImageViewModel,
                        skipButton,
                        adCountdown,
                        adOverlay,
                        adPlaying,
                        badgeTexts
                    };
                }"""
            )

            # Map JS marker keys -> UIAdDetectionResult attributes
            mapping = {
                "hasAdLabel": ("ad_label", "ad_label"),
                "hasSponsored": ("sponsored_label", "sponsored_label"),
                "hasAdImageViewModel": ("ad_image_view_model", "ad_image_view_model"),
                "skipButton": ("skip_button", "skip_button"),
                "adCountdown": ("ad_countdown", "ad_countdown"),
                "adOverlay": ("ad_overlay", "ad_overlay"),
                "adShowing": ("ad_showing_class", "ad_showing_class"),
            }

            newly = []
            for js_key, (attr, label) in mapping.items():
                if markers.get(js_key) and not getattr(ui_result, attr):
                    setattr(ui_result, attr, True)
                    newly.append(label)

            if newly:
                ui_result.raw_markers.append(
                    {
                        "context": context,
                        "new": newly,
                        "badgeTexts": markers.get("badgeTexts", []),
                    }
                )
                self.logger.info(
                    "UI markers detected (%s): %s",
                    context or "check",
                    ", ".join(newly),
                )

            return markers

        except Exception as e:
            self.logger.warning("UI marker check failed: %s", e)
            return None

    async def _play_and_seek(self, page, ui_result: UIAdDetectionResult):
        # Trigger pre-roll and mid-roll checks: play video, then seek
        try:
            self.logger.info("Attempting playback + seek sequence")

            await page.evaluate(
                """() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = true;
                        v.play().catch(() => {});
                    }
                }"""
            )

            await asyncio.sleep(3)
            markers = await self._update_ui_markers(page, ui_result, context="after play")

            # If ad is playing, delay seeks (seeks can be blocked during ads)
            if markers and markers.get("adPlaying"):
                waited = 0
                self.logger.info("Ad playing detected; waiting before seeks")
                while waited < 20:
                    await asyncio.sleep(2)
                    waited += 2
                    markers = await self._update_ui_markers(
                        page, ui_result, context=f"ad wait {waited}s"
                    )
                    if not markers or not markers.get("adPlaying"):
                        break
                if markers and markers.get("adPlaying"):
                    self.logger.info("Ad still playing after wait; skipping seeks")
                    return

            for pos in (0.25, 0.5, 0.75):
                self.logger.info("Seeking to %.0f%%", pos * 100)
                await page.evaluate(
                    f"""() => {{
                        const v = document.querySelector('video');
                        if (v && v.duration) v.currentTime = v.duration * {pos};
                    }}"""
                )
                await asyncio.sleep(2)
                await self._update_ui_markers(
                    page, ui_result, context=f"after seek {int(pos * 100)}%"
                )

            await asyncio.sleep(2)
            await self._update_ui_markers(page, ui_result, context="final")

        except Exception as e:
            self.logger.warning("Playback/seek failed: %s", e)

    async def detect(self, video_id: str) -> AdDetectionResult:
        # Detect ads for a video using DOM + network capture + stealth UI markers
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("Starting detection for video: %s", video_id)

        dom_result = DOMDetectionResult()
        network_result = NetworkDetectionResult()
        ui_result = UIAdDetectionResult()
        error: Optional[str] = None

        if not self.browser:
            return AdDetectionResult(
                video_id=video_id,
                dom_result=dom_result,
                network_result=network_result,
                ui_result=ui_result,
                verdict=None,
                method=DetectionMethod.NONE,
                confidence="low",
                error="Browser not initialised. Call setup() first.",
            )

        # Create a fresh browser context (simulates incognito per run)
        context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        # Override navigator.webdriver to reduce bot detection
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """
        )

        page = await context.new_page()

        # Apply playwright-stealth if installed (stronger evasion coverage)
        if STEALTH_AVAILABLE:
            try:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
                self.logger.info("Applied playwright-stealth patches")
            except Exception as e:
                self.logger.warning("Stealth apply failed: %s", e)
        else:
            self.logger.warning("playwright-stealth not installed; using basic stealth only")

        # Collect network requests and update network_result on the fly
        def handle_request(request):
            chk = check_url_for_ads(request.url)
            if not chk["is_ad_related"]:
                return
            network_result.ad_requests_count += 1
            network_result.matched_urls.append(request.url)
            if chk["ad_break"]:
                network_result.ad_break_detected = True
            if chk["pagead"]:
                network_result.pagead_detected = True
            if chk["doubleclick"]:
                network_result.doubleclick_detected = True
            if chk["adunit"]:
                network_result.adunit_detected = True
            if chk["activeview"]:
                network_result.activeview_detected = True

        page.on("request", handle_request)

        try:
            # Multiple loads for DOM validation (Paper 1 methodology uses 5)
            for load_num in range(self.num_loads):
                try:
                    self.logger.info(
                        "Load %d/%d: navigating to %s",
                        load_num + 1,
                        self.num_loads,
                        url,
                    )
                    await page.goto(url, wait_until="networkidle", timeout=30_000)

                    # Consent banner can block player/UI
                    await self._dismiss_consent(page)

                    # Let the player initialise
                    await asyncio.sleep(2)

                    # Early UI polling: pre-roll ads often show "Sponsored" shortly after load
                    self.logger.info("Polling for pre-roll ad markers (up to 8s)...")
                    for poll in range(4):
                        await self._update_ui_markers(
                            page, ui_result, context=f"pre-roll poll {poll+1}"
                        )
                        if ui_result.sponsored_label:
                            self.logger.info("Pre-roll ad detected via sponsored label")
                            break
                        await asyncio.sleep(2)

                    # DOM check (Paper 1 variables)
                    dom_check = check_dom_for_ads(await page.content())
                    dom_result.total_loads += 1
                    dom_result.raw_findings.append(dom_check)

                    has_any = dom_check["has_adTimeOffset"] or dom_check["has_playerAds"]
                    if has_any:
                        dom_result.loads_with_ads += 1
                    if dom_check["has_adTimeOffset"]:
                        dom_result.has_adTimeOffset = True
                    if dom_check["has_playerAds"]:
                        dom_result.has_playerAds = True

                    # First load: play + seek to provoke pre-roll/mid-roll requests/markers
                    if load_num == 0:
                        await self._play_and_seek(page, ui_result)

                    if load_num < self.num_loads - 1:
                        await asyncio.sleep(1)

                except Exception as e:
                    error = f"Load {load_num + 1} failed: {e}"
                    self.logger.warning(error)

        except Exception as e:
            error = str(e)
            self.logger.error("Detection failed: %s", error)

        finally:
            await context.close()

        self.logger.info(
            "Network summary: ad_requests=%d, ad_break=%s, pagead=%s, doubleclick=%s, adunit=%s, activeview=%s",
            network_result.ad_requests_count,
            network_result.ad_break_detected,
            network_result.pagead_detected,
            network_result.doubleclick_detected,
            network_result.adunit_detected,
            network_result.activeview_detected,
        )
        self.logger.info(
            "UI summary: ad_label=%s, sponsored=%s, ad_image=%s, skip=%s, countdown=%s, overlay=%s, ad_showing=%s",
            ui_result.ad_label,
            ui_result.sponsored_label,
            ui_result.ad_image_view_model,
            ui_result.skip_button,
            ui_result.ad_countdown,
            ui_result.ad_overlay,
            ui_result.ad_showing_class,
        )

        # Determine verdict (priority: UI sponsored > network ad_break > UI other > DOM)
        verdict, method, confidence = determine_verdict(dom_result, network_result, ui_result)
        self.logger.info(
            "Verdict: %s (method=%s, confidence=%s)",
            "Has Ads" if verdict else ("No Ads" if verdict is False else "Uncertain"),
            method.value,
            confidence,
        )

        return AdDetectionResult(
            video_id=video_id,
            dom_result=dom_result,
            network_result=network_result,
            ui_result=ui_result,
            verdict=verdict,
            method=method,
            confidence=confidence,
            error=error,
        )

    async def detect_batch(
        self,
        video_ids: List[str],
        delay: float = 1.0,
        progress_callback=None,
    ) -> List[AdDetectionResult]:
        # Detect ads for multiple videos (sequential runner with optional delay)
        results: List[AdDetectionResult] = []
        total = len(video_ids)

        for i, vid in enumerate(video_ids):
            res = await self.detect(vid)
            results.append(res)

            if progress_callback:
                progress_callback(i + 1, total, res)

            if i < total - 1:
                await asyncio.sleep(delay)

        return results


# Synchronous wrapper for non-async usage
def detect_ads_sync(video_id: str, headless: bool = False) -> AdDetectionResult:
    # Convenience wrapper for running from scripts / CLI without managing the event loop
    async def _run():
        detector = AdDetector(headless=headless)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()

    return asyncio.run(_run())


if __name__ == "__main__":
    # Quick test: python ad_detector.py <video_id>
    if len(sys.argv) < 2:
        print("Usage: python ad_detector.py <video_id>")
        print("Example: python ad_detector.py a0tD4hmswz4")
        sys.exit(1)

    video_id = sys.argv[1]
    print(f"Detecting ads for video: {video_id}")

    result = detect_ads_sync(video_id, headless=False)

    print("\n=== Detection Results ===")
    print(f"Video ID: {result.video_id}")

    print("\nDOM Detection (Paper 1):")
    print(f"  adTimeOffset: {result.dom_result.has_adTimeOffset}")
    print(f"  playerAds: {result.dom_result.has_playerAds}")
    print(f"  Loads with ads: {result.dom_result.loads_with_ads}/{result.dom_result.total_loads}")

    print("\nNetwork Detection:")
    print(f"  Ad requests: {result.network_result.ad_requests_count}")
    print(f"  ad_break: {result.network_result.ad_break_detected}")
    print(f"  pagead: {result.network_result.pagead_detected}")
    print(f"  doubleclick: {result.network_result.doubleclick_detected}")
    print(f"  adunit: {result.network_result.adunit_detected}")
    print(f"  activeview: {result.network_result.activeview_detected}")

    print("\nUI Detection:")
    print(f"  ad_label: {result.ui_result.ad_label}")
    print(f"  sponsored_label: {result.ui_result.sponsored_label}")
    print(f"  ad_image_view_model: {result.ui_result.ad_image_view_model}")
    print(f"  skip_button: {result.ui_result.skip_button}")
    print(f"  ad_countdown: {result.ui_result.ad_countdown}")
    print(f"  ad_overlay: {result.ui_result.ad_overlay}")
    print(f"  ad_showing_class: {result.ui_result.ad_showing_class}")

    print(
        f"\nVerdict: {'Has Ads' if result.verdict else 'No Ads' if result.verdict is False else 'Uncertain'}"
    )
    print(f"Method: {result.method.value}")
    print(f"Confidence: {result.confidence}")
    if result.error:
        print(f"Error: {result.error}")
