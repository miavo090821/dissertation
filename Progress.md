# Dissertation Pipeline Enhancement - Progress Log

This document tracks all changes, implementations, and progress for the YouTube Self-Censorship Research project enhancements.

---

## Project Overview

**Goal:** Enhance the dissertation pipeline with:
1. Main orchestrator for 7-step pipeline
2. Automated ad detection (HTML/DOM + Network API)
3. Expanded video dataset support



---

## Session Log

### 2026-02-01: Ad Detection Testing - Probabilistic Ad Serving Discovery

#### What We Did

Ran ad detector on 5 new test videos to validate the methodology:

| Video ID | DOM Signals | Network `ad_break` | UI `sponsored_label` | **Verdict** |
|----------|-------------|-------------------|---------------------|-------------|
| `Nqmd4iU8J3k` | adTimeOffset=✓, playerAds=✓ | ✓ | ✓ | **Has Ads** |
| `mfkVwzA6sXU` | adTimeOffset=✓, playerAds=✓ | ✓ | ✓ | **Has Ads** |
| `7AAhVg9cUo0` | adTimeOffset=✓, playerAds=✓ | ✗ | ✓ | **Has Ads** |
| `oNHuEdy6cZM` | adTimeOffset=✓, playerAds=✓ | ✓ | ✓ (run 3) | **Has Ads** |
| `8NX4KOZ5nvI` | adTimeOffset=✗, playerAds=✗ | ✗ | ✗ | **No Ads** |

#### Key Finding: Probabilistic Ad Serving

Video `oNHuEdy6cZM` demonstrated probabilistic ad serving:

| Run | DOM Signals | Network | UI Detection | Verdict |
|-----|-------------|---------|--------------|---------|
| 1 | ✓ | ad_break=✓ | No markers | No Ads |
| 2 | ✓ | ad_break=✓ | No markers | No Ads |
| 3 | ✓ | ad_break=✓ | sponsored_label=✓ (at 75% seek) | **Has Ads** |

**Analysis:**
- DOM and network signals were **consistent across all runs** (infrastructure exists)
- UI detection **varied** based on whether YouTube served an ad
- The ad appeared as a **mid-roll** triggered at the 75% seek position
- This confirms that **single observations can produce false negatives**

#### Implications

1. **DOM/Network detect capability, not delivery** - These signals remain stable while actual ad serving varies
2. **UI detection is correct but probabilistic** - It accurately detects when ads render, but rendering is not guaranteed
3. **Multiple runs increase confidence** - For uncertain videos, repeated observations reduce false negatives
4. **Mid-roll ads require seeking** - The detection system's seek strategy (25%, 50%, 75%) is essential for catching mid-roll ads

#### Documentation Updates

- Added "Probabilistic Ad Serving" section to `docs/methodology_ad_detection.md`
- Added finding paragraph to `docs/email_methodology_update.md`
- Updated this progress log

---

### 02-01-2026: Created Main Pipeline Orchestrator

#### What We Did

1. **Created `main.py`** - Main orchestrator for the 7-step pipeline:
   - Sequential execution: Step 2 → Steps 3/4/5 → Step 6 → Step 7
   - Command-line arguments for flexible runs
   - Progress logging with timestamps
   - Error handling with graceful continuation
   - Final summary of results

#### Command-Line Arguments

| Argument | Purpose |
|----------|---------|
| `--skip-extraction` | Skip Step 2, use existing extracted data |
| `--skip-existing` | Pass to Step 2 to skip already extracted videos |
| `--steps N [N ...]` | Run specific steps only (e.g., `--steps 3 6 7`) |
| `--archive` | Archive previous output before running |

#### Usage Examples

```bash
# Run full pipeline
python main.py

# Skip extraction, run analysis only
python main.py --skip-extraction

# Run specific steps
python main.py --steps 3 6 7

# Full run but skip already extracted videos
python main.py --skip-existing
```

#### Files Created

| File | Purpose |
|------|---------|
| `main.py` | Main pipeline orchestrator |
| `scripts/__init__.py` | Package initialization |

---

### 30-01-2026: Added Methodology Section to README

#### What We Did

1. **Added "Automated Monetisation Detection" section** explaining:
   - Refinement of DOM-based detection (why Dunna et al.'s approach produces false positives)
   - UI-based detection as ground truth (Sponsored label)
   - Technical constraints (headed browser requirement for bot detection avoidance)
   - Detection methods summary table
   - Implications for interpretation (ad delivery ≠ creator monetisation)

2. **Restructured manual classification section** as "Validation":
   - Reframed manual verification as ground truth validation for automated system
   - Retained the full protocol for reproducibility
   - Added note that new videos undergo both automated + manual verification

#### Why This Matters

The methodology section now aligns with the literature review claim:
> "HTML/DOM + Network API Ads requests with manual and automated verification"

It explains:
- Why DOM/Network are supplementary (indicate infrastructure, not delivery)
- Why UI is ground truth ("Sponsored" label confirms actual ad render)
- Why manual verification matters (validates automated findings)
- Why headed browser is required (bot detection suppresses ads otherwise)

This frames the approach as a **refinement** of Dunna et al., not a contradiction.

---

#### Problem

YouTube detected automated browsers (`navigator.webdriver=true`) and suppressed ad serving, causing false negatives. Manual incognito showed ads; automated incognito didn't.

#### What We Did

1. **Removed CDP-based Chrome launch** - CDP connection itself can be detected
2. **Simplified to Playwright's native launch** with stealth args:
   - `--disable-blink-features=AutomationControlled`
   - `--disable-infobars`
   - `--no-first-run`
3. **Added `navigator.webdriver` override** via `context.add_init_script()`:
   ```python
   await context.add_init_script("""
       Object.defineProperty(navigator, 'webdriver', {
           get: () => undefined
       });
   """)
   ```

#### Test Results

```
python scripts/ad_detector.py _9ectEMceBk
```

**Before fix:** No ads detected (false negative)
**After fix:**
- Pre-roll ad detected via `sponsored_label`, `ad_image_view_model`, `ad_showing_class`
- DOM: `adTimeOffset=True`, `playerAds=True`
- Network: 37 ad requests (pagead, doubleclick)
- **Verdict: Has Ads** (high confidence)

#### Files Modified

| File | Changes |
|------|---------|
| `scripts/ad_detector.py` | Removed CDP launch, added stealth args + navigator.webdriver override |

#### Why Headless Mode Cannot Detect Ads

Even with stealth fixes, `headless=True` fails to detect ads. YouTube/Google use **multiple signals** to detect headless browsers:

| Signal | Headless | Headed |
|--------|----------|--------|
| `navigator.webdriver` | `true` (fixable) | `true` (fixable) |
| `window.chrome` | Missing/incomplete | Full object |
| `navigator.plugins` | Empty `[]` | Has plugins |
| WebGL renderer | "SwiftShader" (software) | Real GPU |
| Screen dimensions | Often 0x0 or fixed | Real screen |
| User interaction | None | Mouse/keyboard |

**Key issue:** Headless Chromium uses SwiftShader (software rendering) instead of a real GPU. Google's ad fraud prevention detects this and classifies it as a bot.

**Result in headless mode:**
- Video player loads normally
- Pre-roll ads are skipped entirely
- "Sponsored" label never injected into DOM

**Result in headed mode with stealth:**
- Appears as real browser with GPU
- Receives actual ads
- "Sponsored" label appears in player UI

**Conclusion:** For dissertation batch jobs, headed mode (`headless=False`) is the pragmatic solution. Large-scale headless scraping would require additional spoofing (WebGL strings, fake plugins, mouse simulation).

---

### 28/01/2026: UI Marker Expansion (Sponsored + ad-image-view-model)

#### What We Did

1. **Added UI markers** for Sponsored text and `<ad-image-view-model>` elements
2. **Kept existing UI signals** (ad label, skip button, countdown, overlay, ad-showing class)
3. **Updated unit tests** for new UI marker fields

#### Test Results

```
27 passed, 3 skipped in 0.20s
```

**Browser checks (pilot videos):**
- `yefIunm7Dgs` → UI markers false → Verdict: No Ads
- `_9ectEMceBk` → UI markers false (including sponsored/ad-image-view-model) → Verdict: No Ads (pre-roll ad seen manually; UI markers still missing)

---
