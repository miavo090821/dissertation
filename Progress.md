# Dissertation Pipeline Enhancement - Progress Log

This document tracks all changes from thhe day we realised HTML and Network API is not consistent and we need to go with another layer of detecting ads which is using Stealth method to detect ads via UI. This doc is for my own use to keep track of implementations, and progress for the YouTube Self-Censorship Research project enhancements.

---

## Project Overview

**Goal:** Enhance the dissertation pipeline with:
1. Main orchestrator for 7-step pipeline
2. Automated ad detection (HTML/DOM + Network API + Stealth)
3. Expanded video dataset support



---

## Session Log

## 15/03/2026 — Removed Step 3c (LLM Temporal Analysis) from Pipeline

### What Changed
Removed Step 3c (LLM-based temporal analysis via Claude API) from the research pipeline entirely.

### Why
LLM analysis will be done in the consumer app instead of the research pipeline. The pipeline should focus on deterministic, reproducible analysis steps. LLM analysis is better suited to the interactive consumer layer where results can be reviewed and iterated on in real time.

### Files Modified
| File | Changes |
|------|---------|
| `main.py` | Removed 3c from STEP_NAMES, ALL_STEPS, PHASES; removed `--skip-llm` flag and step 3c execution block; updated help text scenarios (7→6) |
| `config.py` | Removed ANTHROPIC_API_KEY loading/warning and LLM_MODEL constant |
| `README.md` | Removed 3c from pipeline diagram, step table, scenarios, flags table, selective steps, .env example, folder structure |
| `PROGRESS.md` | Removed LLM Temporal Analysis Methodology section; added this entry |

### File Deleted
| File | Why |
|------|-----|
| `scripts/step3c_llm_analysis.py` | Entire step removed from pipeline |

### Not Affected
- Steps 6 (report) and 7 (visualizations) had no dependency on 3c output
- Pipeline now has 8 steps: 1, 2, 3, 3b, 4, 5, 6, 7


## 01-14/03/2026 — Resilient Pipeline Orchestrator Redesign

### Problem
The pipeline had three weaknesses:
1. **No failure resilience** — if any step crashed, the entire pipeline stopped (video 101 failing killed 102-257)
2. **No progress tracking** — after a crash, no way to know which steps ran, which failed, or what to run next
3. **Scattered sys.argv logic** — each step had ad-hoc `sys.argv = [...]` manipulation

### Changes Made

**`main.py` — full rewrite of orchestrator logic:**

1. **New `--continue-on-failure` flag** — when a step fails, logs the error and continues to the next step instead of stopping. Enables overnight runs where you deal with failures in the morning.

2. **Pipeline progress report** (`data/output/pipeline_report.txt`) — saved after every run, appends to file for history. Shows:
   - Timing for each step (identifies slow steps)
   - Actual error messages for failures
   - Exact recovery command (`python main.py --steps 3c`) to re-run just the failed steps
   - SKIPPED/NOT RUN status for steps that didn't execute

3. **`_set_step_argv()` helper** — replaced all scattered `sys.argv = [...]` blocks with a clean helper that builds argv from keyword arguments. Eliminates inconsistent flag handling.

4. **`run_step()` now returns `(success, elapsed_seconds, error_message)`** — previously returned just `bool`. The richer return enables the progress report.

5. **Phase-based code organisation** — steps grouped into logical phases with clear comments:
   - Phase 1: Data Collection (Steps 1-2)
   - Phase 2: Analysis (Steps 3-5)
   - Phase 3: Output (Steps 6-7)
   - Phase 4: Summary (report + recovery commands)

6. **7 recovery scenarios in `--help` and README** — concrete commands for: fresh start, resume after crash, ad detection failure, LLM API error, different detection method, re-run analysis only, overnight run.

**`README.md` — updated Commands Reference section:**
- Replaced "Common Workflows" with 7 named scenarios with explanations
- Added flags reference table
- Documented `--continue-on-failure` flag and `pipeline_report.txt` output

### No Changes To
- Individual step scripts — all resilience handled at orchestrator level
- Existing flags — `--skip-existing`, `--skip-extraction`, `--skip-llm`, `--steps`, `--method`, `--archive`, `--recheck-no`, `--recheck-rounds` all unchanged

### 20-28/02/2026: Ad Detection Testing - Probabilistic Ad Serving Discovery

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

### 02-01-2026: Update Main Pipeline Orchestrator

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

### 01-01-2026: Added Methodology Section to README

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
