# as the HTML/DOM and network API were not consistent in detecting ads in videos. 
# I decided to go to a different approach which is a stealth approach which will detect ads based on UI/UX of Youtube 
# The only downside of this method is that some of the "no ads videos" can sometimes have ads, 
# the good news is the number of "no ads video" is small and we have the manual verification step to double check 
# the dectection, which should take little time. 

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
import re
import asyncio
class AdDetector:
    def __init__(self, headless: bool = False):
        self.headless = headless  # Store launch mode
        self.playwright = None    # Will hold the Playwright controller once started
        self.browser = None       # Will hold the launched browser instance

    # initialise Playwright and launch a Chromium browser.
    # this should be called once before running any detection to avoid repeatedly
    # starting/stopping the browser (which is slow and can be flaky).
    async def setup(self):
        # import here to keep module import lightweight until setup is actually invoked.
        from playwright.async_api import async_playwright

        # start Playwright (manages browser automation drivers)
        self.playwright = await async_playwright().start()

        # launch Chromium. headless controls whether a visible window is shown.
        self.browser = await self.playwright.chromium.launch(headless=self.headless)

        # logging for debugging; consider replacing with a proper logger later.
        print("Playwright launched")

    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Playwright closed")

    async def detect(self, video_id: str) -> AdDetectionResult:
        # DOM + basic network capture (net/ui placeholders)
        dom, net, ui = DOMDetectionResult(), NetworkDetectionResult(), UIAdDetectionResult()
        url = f"https://www.youtube.com/watch?v={video_id}"

        # Create an isolated browser context for this run (fresh cookies/storage)
        # This helps reduce cross-test contamination when running many videos.
        context = await self.browser.new_context()
        page = await context.new_page()

        captured_urls = []

        async def update_ui_markers(page, ui: UIAdDetectionResult, context: str = ""):
    markers = await page.evaluate('''() => {
        const player = document.querySelector('.html5-video-player');
        const adShowing = !!(player && player.classList.contains('ad-showing'));

        const badgeTexts = Array.from(document.querySelectorAll('.ytp-ad-badge__text'))
            .map(el => (el.textContent || '').trim().toLowerCase());

        const hasAdLabel = badgeTexts.some(t => t === 'ad');
        const hasSponsored = badgeTexts.some(t => t.includes('sponsored'));

        return { adShowing, hasAdLabel, hasSponsored, badgeTexts };
    }''')

    newly = []
    if markers["hasSponsored"] and not ui.sponsored_label:
        ui.sponsored_label = True; newly.append("sponsored_label")
    if markers["hasAdLabel"] and not ui.ad_label:
        ui.ad_label = True; newly.append("ad_label")

    if newly:
        ui.raw_markers.append({"context": context, "new": newly, "badgeTexts": markers.get("badgeTexts", [])})

        async def on_request(req):
            captured_urls.append(req.url)

        page.on("request", on_request)

        try:
            # Navigate to the page and wait for network to become idle.
            # note: YouTube can keep background requests going; adjust strategy if needed.
            await page.goto(url, wait_until="networkidle", timeout=30_000)

            # small additional delay to allow late-rendered player state to appear in HTML.
            await asyncio.sleep(2)

            # DOM
            dom_check = check_dom_for_ads(await page.content())
            dom.total_loads += 1
            dom.raw_findings.append(dom_check)
            dom.has_adTimeOffset |= dom_check["has_adTimeOffset"]
            dom.has_playerAds |= dom_check["has_playerAds"]

        except Exception as e:
            await context.close()
            return AdDetectionResult(
                video_id=video_id,
                dom=dom,
                net=net,
                ui=ui,
                verdict=None,
                method=DetectionMethod.NONE,
                confidence="low",
                error=str(e),
            )

        # Network analysis (TEMP minimal)
        for u in captured_urls:
            chk = check_url_for_ads(u)
            if chk["ad_break"]:
                net.ad_break_detected = True
                net.ad_requests_count += 1
                net.matched_urls.append(u)

        await context.close()

        verdict, method, confidence = determine_verdict(dom, net, ui)
        return AdDetectionResult(
            video_id=video_id,
            dom=dom,
            net=net,
            ui=ui,
            verdict=verdict,
            method=method,
            confidence=confidence,
        )

AD_BREAK_PATTERN = re.compile(r"ad_break", re.IGNORECASE)
DOM_ADTIME_PATTERN = re.compile(r'["\']?adTimeOffset["\']?\s*:', re.IGNORECASE)
DOM_PLAYERADS_PATTERN = re.compile(r'["\']?playerAds["\']?\s*:', re.IGNORECASE)


#  we set up the method by using enum
class DetectionMethod(Enum):
    NONE = "none"
    DOM = "dom"
    NETWORK = "network"
    UI = "ui"
    BOTH = "both"
    CONFLICT = "conflict"


@dataclass
class DOMDetectionResult:
    has_adTimeOffset: bool = False
    has_playerAds: bool = False
    total_loads: int = 0
    raw_findings: List[Dict] = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        return self.has_adTimeOffset or self.has_playerAds

#  when inspect the page, we can see the ad_breaks in the network api
# in here we will check that by counting ad breaks 
@dataclass
class NetworkDetectionResult:
    ad_break_detected: bool = False
    ad_requests_count: int = 0
    matched_urls: List[str] = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        return self.ad_break_detected

#  this is stealth method by checking the UI for ads shown
@dataclass
class UIAdDetectionResult:
    sponsored_label: bool = False
    ad_label: bool = False
    raw_markers: List[Dict] = field(default_factory=list)

    @property
    def has_ads(self) -> bool:
        return self.sponsored_label or self.ad_label


@dataclass
class AdDetectionResult:
    video_id: str
    dom: DOMDetectionResult
    net: NetworkDetectionResult
    ui: UIAdDetectionResult
    verdict: Optional[bool] = None
    method: DetectionMethod = DetectionMethod.NONE
    confidence: str = "low"
    error: str = ""

def determine_verdict(dom: DOMDetectionResult, net: NetworkDetectionResult, ui: UIAdDetectionResult) -> Tuple[Optional[bool], DetectionMethod, str]:
    # UI sponsored is “truth”, then network ad_break, then DOM
    if ui.sponsored_label:
        return True, DetectionMethod.UI, "high"
    if net.ad_break_detected:
        return True, DetectionMethod.NETWORK, "high"
    if dom.has_ads:
        return True, DetectionMethod.DOM, "medium"
    # Assume no ads if nothing detected 
    return False, DetectionMethod.NONE, "medium"


def check_dom_for_ads(page_source: str) -> dict:
    if not page_source:
        return {"has_adTimeOffset": False, "has_playerAds": False}

    return {
        "has_adTimeOffset": bool(DOM_ADTIME_PATTERN.search(page_source)),
        "has_playerAds": bool(DOM_PLAYERADS_PATTERN.search(page_source)),
    }


def check_url_for_ads(url: str) -> dict:
    # only ad_break for now; later we categorise pagead/doubleclick etc.
    return {"ad_break": bool(AD_BREAK_PATTERN.search(url))}

def detect_ads_sync(video_id: str, headless: bool = False):
    async def _run():
        detector = AdDetector(headless=headless)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()

    return asyncio.run(_run())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ad_detector.py <video_id>")
        raise SystemExit(1)

    vid = sys.argv[1]
    res = detect_ads_sync(vid, headless=False)

    print("video_id:", res.video_id)
    print("dom:", res.dom.has_ads, res.dom.has_adTimeOffset, res.dom.has_playerAds)
    print("net:", res.net.has_ads, "ad_break=", res.net.ad_break_detected, "count=", res.net.ad_requests_count)
    print("ui:", res.ui.has_ads, "sponsored=", res.ui.sponsored_label, "ad_label=", res.ui.ad_label)
    print("verdict:", res.verdict, "method:", res.method.value, "confidence:", res.confidence, "error:", res.error)

