# YouTube Self-Censorship Research Pipeline

A computational audit examining whether YouTube's monetisation system influences creator language. Analyses 257 videos across 4 channels using automated ad detection, NLP-based sensitivity analysis, comment perception keywords, and algospeak detection.

# Notes: 
I have removed the raw data files, because they are limited by the number of files by submission's policies, which are only 35 files. 

After running the main.py, the pipeline will access the input folder - video_url.csv, then it will generate the data files into data/raw folder. 

## Quick Setup

1. **Python 3.11+** required
2. Clone repo and create virtual environment:
   ```bash
   cd dissertation
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```
3. Create `.env` with API keys:
   ```
   YOUTUBE_API_KEY=your_key
   SUPADATA_API_KEY=your_key
   ```
4. Run: `python3 main.py`

## Research Questions

- **RQ1:** Is there an association between sensitive language density in transcripts and the presence of advertisements?
- **RQ2:** Do viewer comments reflect awareness of creator self-censorship behaviour?
- **RQ3:** How prevalent is algospeak (coded language) as a self-censorship mechanism in YouTube content?

## Pipeline Architecture

```
video_urls.csv
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Ad Detection (choose one method)               │
│  ├─ 1a: Stealth/UI (default) — "Sponsored" label        │
│  ├─ 1b: HTML/DOM — adTimeOffset, playerAds              │
│  └─ 1c: Network API — ad_break, pagead, doubleclick     │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Batch Extract (YouTube API + Supadata)         │
│  → metadata.json, transcript.txt, comments.json         │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3:  Sensitivity Analysis (RQ1)                    │
│  Step 3b: Category Cross-Analysis                       │
│  Step 4:  Comments Perception (RQ2)                     │
│  Step 5:  Algospeak Detection (RQ3)                     │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: Generate Excel Report                          │
│  Step 7: Generate 15 Visualisation Charts               │
└─────────────────────────────────────────────────────────┘
```

## Pipeline Steps

| Step | Script | Purpose | Output |
|------|--------|---------|--------|
| 1a | `scripts/step1_ad_detector.py` | Stealth browser ad detection via "Sponsored" label | `ad_detection_results.csv` |
| 1b | `scripts/step1b_dom_detector.py` | HTML/DOM detection (adTimeOffset, playerAds) | `dom_detection_results.csv` |
| 1c | `scripts/step1c_network_api_detector.py` | Network API detection (ad_break, pagead) | `network_api_detection_results.csv` |
| 2 | `scripts/step2_batch_extract.py` | Extract metadata, transcripts, comments via APIs | `data/raw/{video_id}/` |
| 3 | `scripts/step3_sensitivity_analysis.py` | NLP sensitivity analysis with 357-word dictionary | `sensitivity_scores.csv` |
| 3b | `scripts/step3b_category_analysis.py` | Cross-category analysis (sensitive words vs algospeak) | `category_analysis.csv` |
| 4 | `scripts/step4_comments_analysis.py` | Comment perception keyword search (90+ keywords) | `comments_perception.csv` |
| 5 | `scripts/step5_algospeak_detection.py` | Algospeak coded language detection (128 terms) | `algospeak_findings.csv` |
| 6 | `scripts/step6_generate_report.py` | Compile all results into Excel workbook | `analysis_results.xlsx` |
| 7 | `scripts/step7_visualizations.py` | Generate 15 PNG charts across all RQs | `data/output/charts/` |


## Commands Reference

### 6 Scenarios — When Things Go Wrong (and What to Run)

**Scenario 1: Fresh start** — run everything from scratch:
```bash
python3 main.py
```

**Scenario 2: Resume after crash** — laptop closed, terminal killed, pick up where you left off:
```bash
python3 main.py --skip-existing --continue-on-failure
```

**Scenario 3: Ad detection failed mid-run** — video 101 of 257 crashed, resume from there:
```bash
python3 main.py --steps 1 --skip-existing
```

**Scenario 4: Try a different ad detection method** — stealth not working, try DOM or Network API:
```bash
python3 main.py --steps 1 --method dom
python3 main.py --steps 1 --method network-api
```

**Scenario 5: Re-run analysis only** — data already collected, just regenerate results:
```bash
python3 main.py --skip-extraction
```

**Scenario 6: Run overnight** — don't stop on failures, deal with them in the morning:
```bash
python3 main.py --continue-on-failure
```

After any run, check `data/output/pipeline_report.txt` for timing, errors, and recovery commands.

### All Flags

| Flag | What it does |
|------|--------------|
| `--continue-on-failure` | Log errors and keep going instead of stopping |
| `--skip-existing` | Skip already-processed videos (Steps 1, 2, 5) |
| `--skip-extraction` | Skip Step 2 entirely, use existing data |
| `--steps N [N ...]` | Run only specific steps (e.g., `--steps 3 3b 6 7`) |
| `--method {stealth,dom,network-api}` | Ad detection method for Step 1 (default: stealth) |
| `--archive` | Archive previous output before running |
| `--recheck-no` | Re-check videos where ad_status is No |
| `--recheck-rounds N` | Number of re-check rounds (default: 1) |

### Selective Steps

```bash
python3 main.py --steps 1          # Run only ad detection
python3 main.py --steps 2          # Run only data extraction
python3 main.py --steps 3          # Run only sensitivity analysis
python3 main.py --steps 3b         # Run only category cross-analysis
python3 main.py --steps 4          # Run only comments perception
python3 main.py --steps 5          # Run only algospeak detection
python3 main.py --steps 6          # Run only Excel report generation
python3 main.py --steps 7          # Run only chart generation
python3 main.py --steps 3 3b 4 5 6 7  # Run analysis + reporting (skip detection/extraction)
python3 main.py --steps 6 7        # Re-generate report and charts only
```

### Ad Detection Methods (Step 1)

```bash
python3 main.py --steps 1 --method stealth      # Default: UI "Sponsored" label detection
python3 main.py --steps 1 --method dom          # HTML/DOM detection (adTimeOffset, playerAds)
python3 main.py --steps 1 --method network-api  # Network API detection (ad_break, pagead)
```

### Ad Detection Recheck Modes

```bash
# Default flow (stealth): detect once, if No → auto-recheck 5 rounds inline
# If any recheck round finds ads → flips ad_status to Yes
python3 main.py --steps 1

# Resume interrupted detection (picks up unverified Nos + new videos)
python3 main.py --steps 1 --skip-existing

# Manual recheck: re-run all No videos through recheck (stealth)
python3 main.py --steps 1 --recheck-no

# Manual recheck with custom rounds (DOM/Network API methods)
python3 main.py --steps 1 --method dom --recheck-no --recheck-rounds 5
python3 main.py --steps 1 --method network-api --recheck-no --recheck-rounds 3
```

### Standalone Scripts

```bash
python3 scripts/step1_ad_detector.py              # Batch ad detection
python3 scripts/step1_ad_detector.py VIDEO_ID      # Single video ad check
python3 scripts/step1_ad_detector.py --skip-existing  # Resume detection
python3 scripts/step3_sensitivity_analysis.py      # Sensitivity analysis
python3 scripts/step5_algospeak_detection.py       # Algospeak detection
python3 scripts/step7_visualizations.py            # Generate charts
```

## Folder Structure

```
dissertation/
├── main.py                          # Pipeline orchestrator
├── config.py                        # API keys and paths
├── requirements.txt                 # Python dependencies
├── .env                             # API keys (not committed)
├── scripts/
│   ├── step1_ad_detector.py         # Stealth ad detection
│   ├── step1b_dom_detector.py       # DOM ad detection
│   ├── step1c_network_api_detector.py # Network API detection
│   ├── step2_batch_extract.py       # Data extraction
│   ├── step3_sensitivity_analysis.py # Sensitivity analysis
│   ├── step3b_category_analysis.py  # Category cross-analysis
│   ├── step4_comments_analysis.py   # Comment perception
│   ├── step5_algospeak_detection.py # Algospeak detection
│   ├── step6_generate_report.py     # Excel report
│   ├── step7_visualizations.py      # Chart generation
│   └── utils/
│       ├── ad_detection_engine.py   # Core detection classes
│       ├── chart_generators.py      # Chart functions
│       ├── nlp_processor.py         # NLP utilities
│       ├── algospeak_dict.py        # 128-term dictionary
│       └── youtube_api.py           # API helpers
├── dictionaries/
│   ├── sensitive_words.json         # 357 words, 9 categories
│   └── perception_keywords.json    # 90+ perception keywords
├── data/
│   ├── input/video_urls.csv         # Input URLs + ad_status + recheck_round_1..5
│   ├── raw/{video_id}/              # Extracted data per video
│   └── output/                      # Analysis results + charts
├── tests/
│   └── test_ad_detector.py          # Unit tests
└── preparation/
    └── video_script.md              # Demo video script
```

## Visualisations (15 Charts)

| # | Chart | Research Question |
|---|-------|-------------------|
| 1 | Risk% vs Ad Status (scatter) | RQ1 |
| 2 | Risk% by Ad Status (box plot) | RQ1 |
| 3 | Risk% vs Upload Year (scatter + trend) | RQ1 |
| 4 | Average Risk% by Ad Status (bar) | RQ1 |
| 5 | Risk% vs View Count (scatter, log) | RQ1 |
| 6 | Risk% Distribution (histogram) | RQ1 |
| 7 | Classification Distribution (pie) | RQ1 |
| 8 | Perception Categories (horizontal bar) | RQ2 |
| 9 | Top Videos by Perception Ratio (bar) | RQ2 |
| 10 | Transcripts vs Comments Algospeak (grouped bar) | RQ3 |
| 11 | Top Algospeak Terms (horizontal bar) | RQ3 |
| 12 | Algospeak by Category (pie) | RQ3 |
| 13 | Risk% vs Algospeak Count (scatter + correlation) | Combined |
| 14 | Sensitivity by Category (grouped bar) | Category |
| 15 | Category Correlation Heatmap | Category |

## Key Methodology Notes

- **Ad Detection:** The stealth/UI method detects actual ad *delivery* via the "Sponsored" label, not just ad *infrastructure* (unlike DOM/Network methods which show 30-40% false positives)
- **Geographical Limitation:** Results reflect UK-based ad serving only; ads are targeted by country
- **Sensitivity Thresholds:** <2% = Likely Monetised, 2-3% = Uncertain, >3% = Likely Demonetised
- **Algospeak:** 128 coded language terms that creators use to evade content moderation while still referencing sensitive topics
