# dissertation
Investigating YouTube Self-censorship practices

A computational audit of YouTube's algorithmic moderation, monetisation, and creator self-censorship.

## Table of Contents
1. [Research Questions](#1-research-questions)
2. [Quick Start](#2-quick-start)
3. [API Architecture](#3-api-architecture)
4. [Folder Structure](#4-folder-structure)
5. [Running the Pipeline](#5-running-the-pipeline)
6. [Automated Ad Detection Methodology](#6-automated-ad-detection-methodology)
7. [Analysis Methodology](#7-analysis-methodology)
8. [Adding New Videos](#8-adding-new-videos)
9. [Data Formats](#9-data-formats)
10. [Libraries Used](#10-libraries-used)
11. [Visualisation Documentation](#11-visualisation-documentation)

---

## 1. Research Questions

| RQ | Question | Analysis Step |
|----|----------|---------------|
| **RQ1** | How does sensitive content correlate with monetisation status? | Step 3: Sensitivity Analysis |
| **RQ2** | How do viewers perceive creator speech alteration? | Step 4: Comments Perception |
| **RQ3** | What algospeak substitutions do creators use? | Step 5: Algospeak Detection |

---

## 2. Quick Start

```bash
# 1. Navigate to project
cd dissertation

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API keys
cp .env.example .env
# Edit .env and add your actual API keys

# 5. Run the full pipeline
python main.py
```

**Note:** Step 1 (Ad Detection) requires a visible browser window and cannot run in headless mode.

---

## 3. API Architecture

### Why Two APIs?

| API | Used For | Rationale |
|-----|----------|-----------|
| **Supadata API** | Transcripts | YouTube's `youtube-transcript-api` library aggressively IP-blocks scraping requests. Supadata provides reliable transcript access without IP bans. |
| **YouTube Data API v3** | Metadata, Comments, Replies | Official API with generous quota (10,000/day). Reliable for structured data. |

### Rate Limits & Quotas

| API | Limit | Our Safety Margin | Usage |
|-----|-------|-------------------|-------|
| Supadata (free tier) | 100 videos/month, 1 req/sec | 3 second delay | Track monthly usage |
| YouTube Data API | 10,000 quota/day | 0.5 sec delay | Resets daily |

### API Key Setup

API keys are loaded from a `.env` file (REQUIRED):

```bash
# 1. Copy the example file
cp .env.example .env

# 2. Edit .env and add your API keys:
YOUTUBE_API_KEY=your_youtube_api_key
SUPADATA_API_KEY=your_supadata_api_key
```

The `.env` file is automatically loaded when you run scripts. It's gitignored so your keys won't be committed.

**Get API Keys:**
- YouTube: https://console.cloud.google.com/apis/credentials
- Supadata: https://supadata.ai/ (for transcripts)

---

## 4. Folder Structure

```
dissertation/
├── main.py                              # Pipeline orchestrator (runs Steps 1-7)
├── config.py                            # Configuration (requires .env file)
├── requirements.txt                     # Python dependencies
│
├── scripts/
│   ├── step1_ad_detector.py             # Step 1: Automated ad detection
│   ├── step2_batch_extract.py           # Step 2: Extract ALL videos
│   ├── step3_sensitivity_analysis.py    # Step 3: RQ1 - Sensitive word analysis
│   ├── step4_comments_analysis.py       # Step 4: RQ2 - Comment perception
│   ├── step5_algospeak_detection.py     # Step 5: RQ3 - Algospeak detection
│   ├── step6_generate_report.py         # Step 6: Compile Excel report
│   ├── step7_visualizations.py          # Step 7: Generate charts
│   ├── archive_output.py                # Archive previous run data
│   └── utils/                           # Helper functions
│
├── tests/
│   ├── test_ad_detector.py              # Unit tests for ad detection
│   └── fixtures/                        # Test data
│
├── data/
│   ├── input/video_urls.csv             # Video list (ad status updated by Step 1)
│   ├── raw/{video_id}/                  # Extracted data per video
│   ├── output/                          # Current analysis results
│   └── archive/                         # Previous run archives
│
└── dictionaries/
    ├── sensitive_words.json             # Sensitive word lexicon
    └── perception_keywords.json         # Perception keyword categories
```

---

## 5. Running the Pipeline

### Full Pipeline (Recommended)

```bash
python main.py
```

This runs all 7 steps in sequence:

| Step | Name | Description |
|------|------|-------------|
| **1** | Ad Detection | Detects ads on each video using stealth browser automation |
| **2** | Batch Extract | Fetches metadata, transcripts, and comments via APIs |
| **3** | Sensitivity Analysis | RQ1: Calculates sensitive word ratios in transcripts |
| **4** | Comments Perception | RQ2: Identifies viewer awareness of monetisation pressure |
| **5** | Algospeak Detection | RQ3: Detects coded language in transcripts and comments |
| **6** | Generate Report | Compiles all results into Excel workbook |
| **7** | Visualisations | Generates 13 analytical charts |

### Pipeline Options

```bash
# Run full pipeline
python main.py

# Skip ad detection (if already done or doing manually)
python main.py --steps 2 3 4 5 6 7

# Skip extraction (use existing data in data/raw/)
python main.py --skip-extraction

# Run only specific steps
python main.py --steps 3 6 7

# Archive previous output before running
python main.py --archive

# Skip already-processed videos in Steps 2 and 5
python main.py --skip-existing
```

### Running Individual Steps

```bash
# Step 1: Ad Detection (requires visible browser)
python scripts/step1_ad_detector.py

# Step 1: Test single video
python scripts/step1_ad_detector.py VIDEO_ID

# Steps 2-7: Can run individually
python scripts/step2_batch_extract.py
python scripts/step3_sensitivity_analysis.py
python scripts/step4_comments_analysis.py
python scripts/step5_algospeak_detection.py
python scripts/step6_generate_report.py
python scripts/step7_visualizations.py
```

### Archiving Previous Runs

Before re-running analysis, archive previous results:

```bash
# Archive all data (output, raw, input CSV) then clear originals
python scripts/archive_output.py

# Archive without clearing
python scripts/archive_output.py --no-clear

# Archive with custom name
python scripts/archive_output.py --name "experiment_1"
```

---

## 6. Automated Ad Detection Methodology

This study employs automated browser-based detection to determine whether advertisements appear on YouTube videos. The methodology was refined through pilot testing to ensure accurate detection of actual ad delivery rather than mere ad infrastructure.

### Background: Prior Approaches and Their Limitations

Prior computational audits (Dunna et al., 2022) used DOM-based heuristics, specifically checking for `adTimeOffset` and `playerAds` variables in page source. Pilot testing on 19 videos revealed that these variables indicate *ad infrastructure availability* rather than *actual ad delivery*. Videos classified manually as non-monetised frequently contained these DOM variables, producing false positives.

This aligns with YouTube's November 2020 policy change permitting advertisements on non-monetised content, where the platform—not the creator—receives revenue. Similarly, network-level signals (requests to `pagead`, `doubleclick.net`, and ad tracking endpoints) reflect advertising infrastructure presence but do not confirm that an advertisement was rendered.

### This Study's Approach: Stealth Browser UI Detection

To address these limitations, this study adopts **player UI detection** as the primary indicator of ad presence. Specifically, automated detection checks for the **"Sponsored" label** that YouTube displays within the video player during advertisement playback. This label appears only when an advertisement is actively rendered, providing a reliable signal that distinguishes between:

- **Ad infrastructure** (which may exist on any video)
- **Actual ad delivery** (which indicates monetisation status at time of observation)

The "Sponsored" label serves as the **sole criterion** for classifying a video as showing advertisements. DOM variables and network signals have been removed from the detection logic as they produce systematic false positives on non-monetised content.

### Technical Implementation: Stealth Browser Automation

YouTube's advertising systems employ bot detection that suppresses ad delivery to automated browsers. Standard browser automation tools set `navigator.webdriver=true`, which advertising fraud prevention systems use to identify non-human traffic. When detected, YouTube loads videos normally but withholds advertisements entirely—producing systematic false negatives.

To obtain valid observations, the ad detector uses:

1. **Headed browser mode** - Visible Chrome window (not headless)
2. **Stealth settings** - Disables `AutomationControlled` blink feature
3. **Navigator override** - Sets `navigator.webdriver` to `undefined`
4. **Incognito context** - Fresh session without cookies or history
5. **Playwright stealth patches** - Additional anti-detection measures (if available)

### Detection Strategy

For each video, the detector:

1. Loads the video page in a fresh incognito context
2. Dismisses cookie consent banners
3. Polls for pre-roll ads (checking for "Sponsored" label)
4. Plays the video and seeks to 25%, 50%, 75% positions to trigger mid-roll ads
5. Records whether the "Sponsored" label appeared at any point

### Output

Step 1 produces two outputs:

1. **Updates `video_urls.csv`** - Sets `Ads (Yes / No)` column to "Yes" or "No" for each video
2. **Creates `ad_detection_results.csv`** - Detailed detection results including all UI markers observed

### Implications for Interpretation

This methodological approach means the study observes *ad delivery at time of measurement* rather than creator monetisation status. Following YouTube's 2020 policy change, ad presence indicates that the video is serving advertisements but does not confirm whether revenue flows to the creator. The study therefore examines associations between transcript language patterns and ad presence, interpreted within the context that ad presence is a necessary but not sufficient condition for creator monetisation.

### Limitations

**Geographic Variation (Critical)**

Ad delivery varies significantly by geographic region. YouTube serves different advertisements (or no advertisements) based on:

- **Viewer location** - The country/region where the detection is run
- **Regional advertiser demand** - Some markets have fewer advertisers willing to pay for ad placements
- **Regional monetisation policies** - YouTube's monetisation thresholds and policies differ by country

**Example:** A video that shows ads when viewed from the UK may show no ads when viewed from Vietnam, due to differences in regional advertiser demand and monetisation rates.

**Implication for this study:** All ad detection observations in this study were conducted from a single geographic location (UK). Results may not generalise to other regions. Researchers replicating this study in different countries may observe different ad presence patterns for the same videos.

**Other Limitations:**

- **Temporal variation** - Ad status can change over time as advertisers adjust campaigns
- **Probabilistic ad serving** - YouTube does not serve ads on every view; multiple observations increase confidence
- **User profile effects** - Even in incognito mode, IP-based targeting may influence ad delivery

### Manual Verification (Validation)

Manual classification provides ground truth validation for the automated detection system. Because YouTube does not expose monetisation information through any API, manual verification establishes baseline accuracy.

**Protocol:**
1. Clear browsing history and cookies
2. Open the YouTube link in a new incognito/private window
3. Accept all cookies
4. Observe for starting ads and mid-roll ad markers on timeline
5. Compare with automated detection results

---

## 7. Analysis Methodology

### Step 3: Sensitivity Analysis (RQ1)

**Purpose:** Quantify sensitive/controversial content in transcripts to examine associations with monetisation status.

**Method:**
1. Load transcript text
2. Tokenise and lemmatise using NLTK
3. Match against 357-word sensitive dictionary (profanity, violence, drugs, slurs, etc.)
4. Calculate `sensitive_ratio = sensitive_words / total_words * 100`

**Classification Thresholds** (from pilot study):

| Ratio | Classification |
|-------|----------------|
| < 2.0% | Likely Monetised |
| 2.0% - 3.0% | Uncertain |
| > 3.0% | Likely Demonetised |

**Output:** `sensitivity_scores.csv`

---

### Step 4: Comments Perception Analysis (RQ2)

**Purpose:** Detect viewer awareness of monetisation pressure and speech alteration.

**Method:**
1. Load all comments + replies (flattened)
2. Identify creator vs viewer comments (using `channel_id` matching)
3. Search for 90 perception keywords across 7 categories using word boundary regex

**Categories:**
- `monetization_pressure`: demonetized, yellow dollar, adpocalypse
- `algospeak_and_slang`: unalive, seggs, code words
- `censorship_behavior`: can't say, self-censor, youtube won't let
- `editing_artifacts`: bleep, muted, jump cut
- `compliance_and_fear`: walking on eggshells, watered down, family friendly
- `off_platform_diversion`: patreon, rumble, uncensored version
- `suppression_mechanisms`: shadowban, throttled, restricted mode

**Output:**
- `comments_perception.csv` - All matching comments with `is_creator` flag
- `comments_perception_summary.csv` - Per-video summary

---

### Step 5: Algospeak Detection (RQ3)

**Purpose:** Detect coded language substitutions in BOTH creator speech (transcripts) AND viewer comments.

**Method:**
1. **Transcripts:** Detect algospeak terms the creator uses (direct self-censorship evidence)
2. **Comments:** Detect algospeak terms viewers use (perception + mimicry)
3. Match against 99-term algospeak dictionary with context extraction

**Algospeak Categories:**
- `violence_death`: unalive, sewerslide, self-delete
- `sexual`: seggs, grape, spicy accountant
- `profanity`: f*ck, bs, btch
- `drugs`: devil's lettuce, nose candy
- `mental_health`: grippy sock vacation, big sad
- `weapons`: pew pew, boom stick
- `platform_moderation`: yellow dollar, shadow realm

**Output:**
- `algospeak_findings.csv` - All instances with source (transcript/comment)
- `algospeak_findings_summary.csv` - Per-video summary

---

### Step 6: Generate Report

**Purpose:** Compile all analysis results into a single Excel workbook.

**Sheets:**
1. Main Analysis - Combined data
2. Sensitivity Details - Full sensitivity results
3. Comments Analysis - Perception keyword analysis
4. Algospeak Findings - Coded language detection
5. Summary Statistics - Key metrics

**Output:** `analysis_results.xlsx`

---

### Step 7: Visualisations

**Charts Generated:**
1. Risk% vs Ads (scatter)
2. Risk% by Ad Status (box plot)
3. Risk% vs Upload Year (scatter with trend)
4. Average Risk% by Ad Status (bar)
5. Risk% vs View Count (scatter, log scale)
6. Risk% Distribution (histogram with thresholds)
7. Classification Distribution (pie)
8. Perception Categories (horizontal bar)
9. Top Videos by Perception Ratio (horizontal bar)
10. Algospeak in Transcripts vs Comments (grouped bar)
11. Top Algospeak Terms (horizontal bar)
12. Algospeak by Category (pie)
13. Risk% vs Algospeak Count (scatter with correlation)

**Output:** `charts/*.png`

---

## 8. Adding New Videos

1. **Edit `data/input/video_urls.csv`** - Add new rows with URL and channel name
2. **Run the pipeline:**
   ```bash
   # Full pipeline (ad detection + extraction + analysis)
   python main.py

   # Or skip already-processed videos (Steps 2 and 5)
   python main.py --skip-existing
   ```
3. **Archive previous output before re-running** (optional):
   ```bash
   python scripts/archive_output.py
   ```

**Note:** Step 1 will automatically detect ads and update the `Ads (Yes / No)` column. Manual verification can validate the automated results.

---

## 9. Data Formats

### video_urls.csv

```csv
url,channel_name,Ads (Yes / No)
https://www.youtube.com/watch?v=VIDEO_ID,Channel Name,Yes
https://www.youtube.com/watch?v=VIDEO_ID2,Channel Name,No
```

The `Ads (Yes / No)` column is automatically populated by Step 1 (Ad Detection).

### ad_detection_results.csv

```csv
video_id,auto_verdict,auto_confidence,auto_sponsored_label,auto_ad_label,auto_skip_button,...
VIDEO_ID,Yes,high,Yes,No,Yes,...
```

Detailed detection results with all UI markers observed.

### comments.json (nested structure)

```json
[
  {
    "id": "comment_id",
    "author": "Username",
    "author_channel_id": "UC...",
    "text": "Comment text",
    "like_count": 42,
    "is_reply": false,
    "reply_count": 5,
    "replies": [
      {"id": "reply_id", "text": "Reply", "is_reply": true, ...}
    ]
  }
]
```

---

## 10. Libraries Used

### Core Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **pandas** | >=2.0 | Data manipulation, CSV/Excel reading/writing |
| **requests** | >=2.28 | HTTP requests to Supadata API |
| **google-api-python-client** | >=2.0 | YouTube Data API v3 client |
| **python-dotenv** | >=1.0 | Load environment variables from .env |

### Browser Automation (Ad Detection)

| Library | Version | Purpose |
|---------|---------|---------|
| **playwright** | >=1.40 | Browser automation for ad detection |
| **playwright-stealth** | >=1.0 | Anti-bot-detection patches (optional) |

### NLP Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **nltk** | >=3.8 | Text tokenisation and lemmatisation |

### Visualisation Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **matplotlib** | >=3.7 | Chart generation |
| **seaborn** | >=0.12 | Statistical visualisation |
| **numpy** | >=1.24 | Numerical computing |

### File Handling

| Library | Version | Purpose |
|---------|---------|---------|
| **openpyxl** | >=3.1 | Excel file handling |

---

## 11. Visualisation Documentation

### RQ1 Visualisations (Sensitivity Analysis)

| Chart | Purpose |
|-------|---------|
| **01: Risk% vs Ads** | Test core hypothesis - does sensitive content correlate with ad removal? |
| **02: Risk% by Ad Status (Box)** | Compare distribution characteristics between groups |
| **03: Risk% vs Upload Year** | Detect temporal patterns in content risk |
| **04: Average Risk% by Ad Status** | Simple comparison of mean sensitive ratio |
| **05: Risk% vs View Count** | Test if sensitive content affects video reach |
| **06: Risk% Distribution** | Understand overall distribution of content sensitivity |
| **07: Classification Distribution** | Summary of how videos are classified |

### RQ2 Visualisations (Perception Analysis)

| Chart | Purpose |
|-------|---------|
| **08: Perception Categories** | Which aspects of moderation do viewers notice most? |
| **09: Top Videos by Perception** | Identify which videos generate most awareness comments |

### RQ3 Visualisations (Algospeak Analysis)

| Chart | Purpose |
|-------|---------|
| **10: Transcripts vs Comments** | Compare creator self-censorship with viewer mimicry |
| **11: Top Algospeak Terms** | Identify most common coded language substitutions |
| **12: Algospeak by Category** | Distribution across content categories |

### Combined Insight

| Chart | Purpose |
|-------|---------|
| **13: Risk% vs Algospeak Count** | Test relationship between sensitivity and coded language |

---

## Channels in Dataset

- **Actual Justice Warrior** — Videos 1–51
- **The Podcast of the Lotus Eaters** — Videos 52–70

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "API key not found" | Check your `.env` file exists and has valid keys |
| "Module not found" | Run `pip install -r requirements.txt` |
| "Permission denied" | Make sure virtual environment is activated |
| "Rate limit exceeded" | Wait and retry - YouTube has daily quotas |
| "No ads detected" (false negatives) | Ensure browser window is visible; ads not served to headless browsers |
| "Browser not found" | Run `playwright install chromium` |
