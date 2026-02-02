# as the HTML/DOM and network API were not consistent in detecting ads in videos. 
# I decided to go to a different approach which is a stealth approach which will detect ads based on UI/UX of Youtube 
# The only downside of this method is that some of the "no ads videos" can sometimes have ads, 
# the good news is the number of "no ads video" is small and we have the manual verification step to double check 
# the dectection, which should take little time. 

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict

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


class AdDetector:
    async def setup(self): ...
    async def cleanup(self): ...

    async def detect(self, video_id: str) -> AdDetectionResult:
        #  we will have each stage results reported by running the checking method 
        dom = DOMDetectionResult()
        net = NetworkDetectionResult()
        ui = UIAdDetectionResult()
        return AdDetectionResult(video_id=video_id, dom=dom, net=net, ui=ui)


def main():
    print("_")

if __name__ == "__main__":
    main()
