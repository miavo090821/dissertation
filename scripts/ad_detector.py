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
# his should be called once before running any detection to avoid repeatedly
# starting/stopping the browser (which is slow and can be flaky).

    async def setup(self):
        # import here to keep module import lightweight until setup is actually invoked.
        from playwright.async_api import async_playwright

        # start Playwright (manages browser automation drivers)
        self.playwright = await async_playwright().start()

        # launch Chromium. headless controls whether a visible window is shown.
        self.browser = await self.playwright.chromium.launch(headless=self.headless)

        # logging for debugging; consider replacing with a proper logger later.
        print(" Playwright launched")

    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Playwright closed")

    async def detect(self, video_id: str) -> AdDetectionResult:
        # no browsing yet
        dom, net, ui = DOMDetectionResult(), NetworkDetectionResult(), UIAdDetectionResult()
        verdict, method, confidence = determine_verdict(dom, net, ui)
        return AdDetectionResult(video_id=video_id, dom=dom, net=net, ui=ui, verdict=verdict, method=method, confidence=confidence)

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


def main():
    print("_")

if __name__ == "__main__":
    main()
