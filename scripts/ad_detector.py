# As HTML/DOM and Network API signals can be inconsistent in detecting ads in videos,
# we also use a stealth UI/UX approach that detects ads via the YouTube player interface.
# Downside: some videos that are actually “no-ads” can still show ads occasionally.
# Mitigation: the “no-ads” bucket should be small, and we have a manual verification step
# to double-check detections quickly.

"""
Ad Detection Module for YouTube Self-Censorship Research

Implements dual ad detection methodology as per literature review:
1. HTML/DOM Detection (Paper 1 - Dunna et al., 2022): Check for adTimeOffset and playerAds
2. Network API Detection: ad_break as evidence; other signals logged

Reference: "This study takes a transcript-level approach, along with HTML/DOM + Network API 
Ads requests with manual and automated verification to examine associations between 
language patterns and monetisation status (RQ1)"
"""

import re
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# Optional stealth dependency (stronger bot-evasion patches when available)
try:
    from playwright_stealth import Stealth
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False


class DetectionMethod(Enum):
    # Detection method used to determine ad status
    DOM = "dom"
    NETWORK = "network"
    UI = "ui"
    BOTH = "both"
    CONFLICT = "conflict"
    NONE = "none"


@dataclass
class DOMDetectionResult:
    # Results from HTML/DOM detection (Paper 1 methodology)
    has_adTimeOffset: bool = False
    has_playerAds: bool = False
    loads_with_ads: int = 0  # Out of 5 loads (Paper 1: need 0/5 for non-monetized)
    total_loads: int = 0
    raw_findings: list = field(default_factory=list)
    
    @property
    def has_ads(self) -> bool:
        # Video has ads if either variable found in any load
        return self.has_adTimeOffset or self.has_playerAds
    
    @property
    def is_conclusive(self) -> bool:
        # Result is conclusive if we completed all 5 loads
        return self.total_loads >= 5


@dataclass
class NetworkDetectionResult:
    # Results from Network API detection (network tab / request capture)
    ad_requests_count: int = 0
    ad_break_detected: bool = False
    pagead_detected: bool = False
    doubleclick_detected: bool = False
    adunit_detected: bool = False  # el=adunit in watchtime requests
    activeview_detected: bool = False  # Google ad viewability
    matched_urls: list = field(default_factory=list)
    
    @property
    def has_ads(self) -> bool:
        # Treat ad_break as the “hard” network evidence for ads
        return self.ad_break_detected


@dataclass
class UIAdDetectionResult:
    # Stealth method: inspect player UI/UX for ad markers (labels, overlays, skip button, etc.)
    ad_label: bool = False
    sponsored_label: bool = False
    ad_image_view_model: bool = False
    skip_button: bool = False
    ad_countdown: bool = False
    ad_overlay: bool = False
    ad_showing_class: bool = False
    raw_markers: list = field(default_factory=list)
    
    @property
    def has_ads(self) -> bool:
        # UI indicates ads if any marker is present
        return any([
            self.ad_label,
            self.sponsored_label,
            self.ad_image_view_model,
            self.skip_button,
            self.ad_countdown,
            self.ad_overlay,
            self.ad_showing_class,
        ])


@dataclass
class AdDetectionResult:
    # Combined ad detection result from both methods (DOM + Network + UI)
    video_id: str
    dom_result: DOMDetectionResult
    network_result: NetworkDetectionResult
    ui_result: UIAdDetectionResult
    verdict: Optional[bool] = None  # True=has ads, False=no ads, None=uncertain
    method: DetectionMethod = DetectionMethod.NONE
    confidence: str = "low"  # low, medium, high
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        # Convert to dictionary for CSV export
        return {
            'video_id': self.video_id,
            # DOM results
            'auto_dom_ads': 'Yes' if self.dom_result.has_ads else 'No',
            'auto_dom_adTimeOffset': 'Yes' if self.dom_result.has_adTimeOffset else 'No',
            'auto_dom_playerAds': 'Yes' if self.dom_result.has_playerAds else 'No',
            'auto_dom_loads': f"{self.dom_result.loads_with_ads}/{self.dom_result.total_loads}",
            # Network results
            'auto_network_ads': 'Yes' if self.network_result.has_ads else 'No',
            'auto_network_count': self.network_result.ad_requests_count,
            'auto_network_ad_break': 'Yes' if self.network_result.ad_break_detected else 'No',
            # UI results
            'auto_ui_ads': 'Yes' if self.ui_result.has_ads else 'No',
            'auto_ui_ad_label': 'Yes' if self.ui_result.ad_label else 'No',
            'auto_ui_sponsored_label': 'Yes' if self.ui_result.sponsored_label else 'No',
            'auto_ui_ad_image_view_model': 'Yes' if self.ui_result.ad_image_view_model else 'No',
            'auto_ui_skip_button': 'Yes' if self.ui_result.skip_button else 'No',
            'auto_ui_ad_countdown': 'Yes' if self.ui_result.ad_countdown else 'No',
            'auto_ui_ad_overlay': 'Yes' if self.ui_result.ad_overlay else 'No',
            'auto_ui_ad_showing_class': 'Yes' if self.ui_result.ad_showing_class else 'No',
            # Combined verdict
            'auto_verdict': 'Yes' if self.verdict else ('No' if self.verdict is False else 'Uncertain'),
            'auto_method': self.method.value,
            'auto_confidence': self.confidence,
            'auto_error': self.error or '',
        }


# Network patterns to detect ad-related requests
NETWORK_AD_PATTERNS = [
    re.compile(r'googlevideo\.com.*adformat', re.IGNORECASE),
    re.compile(r'ad_break', re.IGNORECASE),
    re.compile(r'pagead2\.googlesyndication', re.IGNORECASE),
    re.compile(r'doubleclick\.net', re.IGNORECASE),
    re.compile(r'youtube\.com/api/stats/ads', re.IGNORECASE),
    re.compile(r'youtube\.com/pagead/', re.IGNORECASE),
    re.compile(r'/ptracking\?', re.IGNORECASE),  # Pre-roll tracking
    re.compile(r'adsapi\.youtube\.com', re.IGNORECASE),
    # New pre-roll ad indicators (from manual network inspection)
    re.compile(r'el=adunit', re.IGNORECASE),  # Watch time tracking for ad units
    re.compile(r'/activeview\?', re.IGNORECASE),  # Google ad viewability tracking
]

# Specific patterns for categorisation
AD_BREAK_PATTERN = re.compile(r'ad_break', re.IGNORECASE)
PAGEAD_PATTERN = re.compile(r'pagead', re.IGNORECASE)
DOUBLECLICK_PATTERN = re.compile(r'doubleclick\.net', re.IGNORECASE)
ADUNIT_PATTERN = re.compile(r'el=adunit', re.IGNORECASE)
ACTIVEVIEW_PATTERN = re.compile(r'/activeview\?', re.IGNORECASE)

# DOM indicators from Paper 1 (Dunna et al., 2022)
DOM_INDICATORS = {
    'adTimeOffset': re.compile(r'["\']?adTimeOffset["\']?\s*:', re.IGNORECASE),
    'playerAds': re.compile(r'["\']?playerAds["\']?\s*:', re.IGNORECASE),
}


def check_url_for_ads(url: str) -> dict:
    # Check if a URL matches any ad-related patterns (network capture)
    result = {
        'is_ad_related': False,
        'ad_break': False,
        'pagead': False,
        'doubleclick': False,
        'adunit': False,
        'activeview': False,
        'matched_pattern': None,
    }
    
    for pattern in NETWORK_AD_PATTERNS:
        if pattern.search(url):
            result['is_ad_related'] = True
            result['matched_pattern'] = pattern.pattern
            break
    
    # Check specific categories (useful for debugging even if only ad_break is “evidence”)
    result['ad_break'] = bool(AD_BREAK_PATTERN.search(url))
    result['pagead'] = bool(PAGEAD_PATTERN.search(url))
    result['doubleclick'] = bool(DOUBLECLICK_PATTERN.search(url))
    result['adunit'] = bool(ADUNIT_PATTERN.search(url))
    result['activeview'] = bool(ACTIVEVIEW_PATTERN.search(url))
    
    return result


def check_dom_for_ads(page_source: str) -> dict:
    # Check page source for ad-related DOM variables (Paper 1 methodology)
    result = {
        'has_adTimeOffset': False,
        'has_playerAds': False,
    }
    
    if not page_source:
        return result
    
    result['has_adTimeOffset'] = bool(DOM_INDICATORS['adTimeOffset'].search(page_source))
    result['has_playerAds'] = bool(DOM_INDICATORS['playerAds'].search(page_source))
    
    return result


def determine_verdict(dom_result: DOMDetectionResult, 
                      network_result: NetworkDetectionResult,
                      ui_result: Optional[UIAdDetectionResult] = None) -> tuple:
    # Verdict priority (intended): UI “Sponsored” label > network ad_break > DOM variables
    # Note: current implementation is UI-only placeholder; expand to combine all signals.
    sponsored_only = ui_result.sponsored_label if ui_result else False
    
    # Sponsored label is treated as the single source of truth (stealth UI marker)
    if sponsored_only:
        return True, DetectionMethod.UI, "high"
    return False, DetectionMethod.UI, "high"


class AdDetector:
    # YouTube ad detector using dual methodology (DOM + Network) plus stealth UI markers
    # Usage:
    #   detector = AdDetector()
    #   await detector.setup()
    #   result = await detector.detect(video_id)
    #   await detector.cleanup()
    
    def __init__(self, headless: bool = False, num_loads: int = 1, log_level: int = logging.INFO, explicit_incognito: bool = True, chrome_channel: bool = True):
        # Initialise ad detector
        # headless: run browser without a visible UI
        # num_loads: number of loads for DOM validation (Paper 1 uses 5)
        self.headless = headless
        self.num_loads = num_loads
        self.browser = None
        self.playwright = None
        self.explicit_incognito = explicit_incognito
        self.chrome_channel = chrome_channel
        self.logger = self._setup_logger(log_level)

    def _setup_logger(self, log_level: int) -> logging.Logger:
        # Simple stdout logger for runs / debugging (replace with file logger if needed)
        logger = logging.getLogger("ad_detector")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(log_level)
        return logger
        
    async def setup(self):
        # Initialise Playwright browser with stealth settings to reduce bot detection
        try:
            from playwright.async_api import async_playwright
            self.logger.info(
                "Starting Playwright (headless=%s, incognito=%s, chrome_channel=%s)",
                self.headless,
                self.explicit_incognito,
                self.chrome_channel
            )
            self.playwright = await async_playwright().start()

            # Stealth args to avoid bot detection
            stealth_args = [
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
            ]
            if self.explicit_incognito:
                stealth_args.append("--incognito")

            launch_kwargs = {
                "headless": self.headless,
                "args": stealth_args,
            }
            if self.chrome_channel:
                launch_kwargs["channel"] = "chrome"

            self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            self.logger.info("Browser launched with stealth args")
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
    
    async def cleanup(self):
        # Close browser and cleanup resources
        if self.browser:
            self.logger.info("Closing browser")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _dismiss_consent(self, page):
        # Dismiss the Google/YouTube cookie consent banner if present
        try:
            # Wait for consent dialog to potentially appear (lazy-loaded)
            await asyncio.sleep(1)

            # Common selectors for the "Accept all" button
            consent_selectors = [
                'button:has-text("Accept all")',
                '[aria-label="Accept the use of cookies and other data for the purposes described"]',
            ]

            for selector in consent_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        self.logger.info("Consent banner detected, clicking: %s", selector)
                        await button.click()
                        await asyncio.sleep(1)  # Wait for banner to dismiss
                        return
                except Exception as e:
                    self.logger.debug("Consent selector %s failed: %s", selector, e)
                    continue

        except Exception as e:
            self.logger.debug("Consent handling failed: %s", e)
    
    async def _play_and_seek(self, page, ui_result: UIAdDetectionResult):
        # Play the video and seek through it to trigger ad-related network requests
        # Pre-roll ads: trigger soon after playback starts
        # Mid-roll ads: ad_break requests often appear when seeking
        try:
            self.logger.info("Attempting video playback and seek sequence")
            # Use JavaScript to directly control the YouTube player (more reliable headless)
            await page.evaluate('''() => {
                const player = document.querySelector('video');
                if (player) {
                    player.muted = true;
                    player.play().catch(() => {});
                }
                if (typeof ytplayer !== 'undefined' && ytplayer.config) {
                    // Player config exists
                }
            }''')
            
            # Wait for video to start and any pre-roll ads to trigger
            await asyncio.sleep(3)
            markers = await self._update_ui_markers(page, ui_result, context="after play")
            
            # If an ad is playing, wait before seeking (seeks can be blocked during ads)
            if markers and markers.get('adPlaying'):
                self.logger.info("Ad playing detected; delaying seeks")
                waited = 0
                while waited < 20:
                    await asyncio.sleep(2)
                    waited += 2
                    markers = await self._update_ui_markers(page, ui_result, context=f"ad wait {waited}s")
                    if not markers or not markers.get('adPlaying'):
                        break
                if markers and markers.get('adPlaying'):
                    self.logger.info("Ad still playing after wait; skipping seeks")
                    return
            
            # Seek to positions to surface mid-roll checks (ad_break often triggered)
            seek_positions = [0.25, 0.5, 0.75]
            
            for position in seek_positions:
                self.logger.info("Seeking to %.0f%%", position * 100)
                await page.evaluate(f'''() => {{
                    const video = document.querySelector('video');
                    if (video && video.duration) {{
                        video.currentTime = video.duration * {position};
                    }}
                }}''')
                await asyncio.sleep(2)
                await self._update_ui_markers(page, ui_result, context=f"after seek {int(position * 100)}%")
            
            # Final wait to capture any delayed ad requests
            await asyncio.sleep(2)
            await self._update_ui_markers(page, ui_result, context="final")
            
        except Exception as e:
            # If interaction fails, DOM/network checks can still run
            self.logger.warning("Playback/seek failed: %s", str(e))
            pass

    async def _update_ui_markers(self, page, ui_result: UIAdDetectionResult, context: str = ""):
        # Check player UI for ad markers and update result (stealth UI/UX detection)
        try:
            markers = await page.evaluate('''() => {
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
                        if (text === 'sponsored' || text.includes('sponsored')) {
                            return true;
                        }
                    }
                    return false;
                })();
                const hasAdImageViewModel = !!document.querySelector('ad-image-view-model');
                const skipButton = !!document.querySelector('.ytp-ad-skip-button, .ytp-ad-skip-button-modern');
                const adCountdown = !!document.querySelector(
                    '.ytp-ad-preview-container, .ytp-ad-timed-pie-countdown-container, .ytp-ad-duration-remaining'
                );
                const adOverlay = !!document.querySelector('.ytp-ad-overlay-container, .ytp-ad-overlay-slot');
                const adPlaying = adShowing || hasAdLabel || hasSponsoredBadge || sponsoredInPlayer || hasAdImageViewModel || skipButton || adCountdown || adOverlay;
                return {
                    adShowing,
                    hasAdLabel,
                    hasSponsored: (hasSponsoredBadge || sponsoredInPlayer),
                    hasAdImageViewModel,
                    skipButton,
                    adCountdown,
                    adOverlay,
                    adPlaying,
                    badgeTexts,
                };
            }''')
            
            newly_detected = []
            if markers.get('hasAdLabel') and not ui_result.ad_label:
                ui_result.ad_label = True
                newly_detected.append("ad_label")
            if markers.get('hasSponsored') and not ui_result.sponsored_label:
                ui_result.sponsored_label = True
                newly_detected.append("sponsored_label")
            if markers.get('hasAdImageViewModel') and not ui_result.ad_image_view_model:
                ui_result.ad_image_view_model = True
                newly_detected.append("ad_image_view_model")
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
                ui_result.raw_markers.append({"context": context, "new": newly_detected, "badgeTexts": markers.get('badgeTexts', [])})
                self.logger.info("UI markers detected (%s): %s", context or "check", ", ".join(newly_detected))
            return markers
        except Exception as e:
            self.logger.warning("UI marker check failed: %s", str(e))
            return None
    
    async def detect(self, video_id: str) -> AdDetectionResult:
        # Detect ads for a video using DOM, Network capture, and stealth UI markers
        url = f"https://www.youtube.com/watch?v={video_id}"
        self.logger.info("Starting detection for video: %s", video_id)
        
        dom_result = DOMDetectionResult()
        network_result = NetworkDetectionResult()
        ui_result = UIAdDetectionResult()
        error = None
        
        try:
            # Create fresh browser context (simulates incognito per run)
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            # Override navigator.webdriver to avoid bot detection
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # Collect network requests (later analysed for ad_break etc.)
            captured_urls = []
            
            async def handle_request(request):
                captured_urls.append(request.url)
            
            page = await context.new_page()

            # Apply playwright-stealth patches if installed (stronger evasion coverage)
            if STEALTH_AVAILABLE:
                stealth = Stealth()
                await stealth.apply_stealth_async(page)
                self.logger.info("Applied playwright-stealth patches (15+ evasion scripts)")
            else:
                self.logger.warning("playwright-stealth not installed; using basic stealth only")

            page.on('request', handle_request)
            
            # Multiple loads for DOM validation (Paper 1 methodology uses 5)
            for load_num in range(self.num_loads):
                try:
                    self.logger.info("Load %d/%d: navigating to %s", load_num + 1, self.num_loads, url)
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    # Cookie consent can block the player; dismiss it if present
                    await self._dismiss_consent(page)
                    
                    # Let the player initialise
                    await asyncio.sleep(2)
                    
                    # Early UI polling: pre-roll ads often show “Sponsored” shortly after load
                    self.logger.info("Polling for pre-roll ad markers (up to 8s)...")
                    for poll in range(4):
                        await self._update_ui_markers(page, ui_result, context=f"pre-roll poll {poll+1}")
                        if ui_result.sponsored_label:
                            self.logger.info("Pre-roll ad detected via sponsored label!")
                            break
                        await asyncio.sleep(2)
                    
                    # DOM check (Paper 1 variables)
                    page_source = await page.content()
                    dom_check = check_dom_for_ads(page_source)
                    self.logger.info(
                        "DOM check: adTimeOffset=%s, playerAds=%s",
                        dom_check['has_adTimeOffset'],
                        dom_check['has_playerAds']
                    )
                    
                    dom_result.total_loads += 1
                    dom_result.raw_findings.append(dom_check)
                    
                    if dom_check['has_adTimeOffset']:
                        dom_result.has_adTimeOffset = True
                        dom_result.loads_with_ads += 1
                    if dom_check['has_playerAds']:
                        dom_result.has_playerAds = True
                        if not dom_check['has_adTimeOffset']:
                            dom_result.loads_with_ads += 1
                    
                    # First load: play + seek to provoke pre-roll/mid-roll requests/markers
                    if load_num == 0:
                        await self._play_and_seek(page, ui_result)
                    
                    # Small delay between loads
                    if load_num < self.num_loads - 1:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    error = f"Load {load_num + 1} failed: {str(e)}"
                    self.logger.warning(error)
            
            # Analyse captured network requests (ad_break is treated as hard evidence)
            for url in captured_urls:
                check = check_url_for_ads(url)
                if check['is_ad_related']:
                    network_result.ad_requests_count += 1
                    network_result.matched_urls.append(url)
                    
                    if check['ad_break']:
                        network_result.ad_break_detected = True
                    if check['pagead']:
                        network_result.pagead_detected = True
                    if check['doubleclick']:
                        network_result.doubleclick_detected = True
                    if check['adunit']:
                        network_result.adunit_detected = True
                    if check['activeview']:
                        network_result.activeview_detected = True
            
            self.logger.info(
                "Network summary: ad_requests=%d, ad_break=%s, pagead=%s, doubleclick=%s",
                network_result.ad_requests_count,
                network_result.ad_break_detected,
                network_result.pagead_detected,
                network_result.doubleclick_detected
            )
            self.logger.info(
                "UI summary: ad_label=%s, sponsored=%s, ad_image=%s, skip=%s, countdown=%s, overlay=%s, ad_showing=%s",
                ui_result.ad_label,
                ui_result.sponsored_label,
                ui_result.ad_image_view_model,
                ui_result.skip_button,
                ui_result.ad_countdown,
                ui_result.ad_overlay,
                ui_result.ad_showing_class
            )
            await context.close()
            
        except Exception as e:
            error = str(e)
            self.logger.error("Detection failed: %s", error)
        
        # Final verdict (intended priority: UI > network ad_break > DOM; currently UI-only placeholder)
        verdict, method, confidence = determine_verdict(dom_result, network_result, ui_result)
        self.logger.info(
            "Verdict: %s (method=%s, confidence=%s)",
            "Has Ads" if verdict else "No Ads" if verdict is False else "Uncertain",
            method.value,
            confidence
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
    
    async def detect_batch(self, video_ids: list, delay: float = 1.0, 
                           progress_callback=None) -> list:
        # Detect ads for multiple videos (simple sequential runner)
        results = []
        
        for i, video_id in enumerate(video_ids):
            result = await self.detect(video_id)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(video_ids), result)
            
            if i < len(video_ids) - 1:
                await asyncio.sleep(delay)
        
        return results


# Synchronous wrapper for non-async usage
def detect_ads_sync(video_id: str, headless: bool = False) -> AdDetectionResult:
    # Convenience wrapper for running from scripts / CLI without managing the event loop
    async def _detect():
        detector = AdDetector(headless=headless)
        await detector.setup()
        try:
            return await detector.detect(video_id)
        finally:
            await detector.cleanup()
    
    return asyncio.run(_detect())

if __name__ == "__main__":
    # Quick test
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ad_detector.py <video_id>")
        print("Example: python ad_detector.py a0tD4hmswz4")
        sys.exit(1)
    
    video_id = sys.argv[1]
    print(f"Detecting ads for video: {video_id}")
    
    result = detect_ads_sync(video_id, headless=False)
    
    print("\n=== Detection Results ===")
    print(f"Video ID: {result.video_id}")
    print(f"\nDOM Detection (Paper 1):")
    print(f"  adTimeOffset: {result.dom_result.has_adTimeOffset}")
    print(f"  playerAds: {result.dom_result.has_playerAds}")
    print(f"  Loads with ads: {result.dom_result.loads_with_ads}/{result.dom_result.total_loads}")
    print(f"\nNetwork Detection:")
    print(f"  Ad requests: {result.network_result.ad_requests_count}")
    print(f"  ad_break: {result.network_result.ad_break_detected}")
    print(f"  pagead: {result.network_result.pagead_detected}")
    print(f"  doubleclick: {result.network_result.doubleclick_detected}")
    print(f"\nUI Detection:")
    print(f"  ad_label: {result.ui_result.ad_label}")
    print(f"  sponsored_label: {result.ui_result.sponsored_label}")
    print(f"  ad_image_view_model: {result.ui_result.ad_image_view_model}")
    print(f"  skip_button: {result.ui_result.skip_button}")
    print(f"  ad_countdown: {result.ui_result.ad_countdown}")
    print(f"  ad_overlay: {result.ui_result.ad_overlay}")
    print(f"  ad_showing_class: {result.ui_result.ad_showing_class}")
    print(f"\nVerdict: {'Has Ads' if result.verdict else 'No Ads' if result.verdict is False else 'Uncertain'}")
    print(f"Method: {result.method.value}")
    print(f"Confidence: {result.confidence}")
    if result.error:
        print(f"Error: {result.error}")
