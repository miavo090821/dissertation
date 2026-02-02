# as the HTML/DOM and network API were not consistent in detecting ads in videos. 
# I decided to go to a different approach which is a stealth approach which will detect ads based on UI/UX of Youtube 
# The only downside of this method is that some of the "no ads videos" can sometimes have ads, 
# the good news is the number of "no ads video" is small and we have the manual verification step to double check 
# the dectection, which should take little time. 

# ad_detector.py (Iteration 2)

from dataclasses import dataclass
from enum import Enum
from typing import Optional

class DetectionMethod(Enum):
    NONE = "none"
    DOM = "dom"
    NETWORK = "network"
    UI = "ui"
    BOTH = "both"
    CONFLICT = "conflict"


@dataclass
class AdDetectionResult:
    video_id: str
    verdict: Optional[bool] = None
    method: DetectionMethod = DetectionMethod.NONE
    confidence: str = "low"
    error: str = ""


class AdDetector:
    def __init__(self):
        # TEMP: nothing here yet
        pass

    async def setup(self):
        # TEMP: later we start Playwright here
        return

    async def cleanup(self):
        return

    async def detect(self, video_id: str) -> AdDetectionResult:
        print(f"[TEMP] detect({video_id}) called")
        return AdDetectionResult(video_id=video_id, verdict=None, method=DetectionMethod.NONE, confidence="low")


def main():
    print("[TEMP] AdDetector class ok")

if __name__ == "__main__":
    main()
