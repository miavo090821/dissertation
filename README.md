# dissertation
Investigating YouTube Self-censorship practices
A computational audit of YouTube’s algorithmic moderation, monetisation, and creator self-censorship.

📌 Table of Contents
1. Research Focus
2. API architecture and set-up
3. Folder Structure
4. Full Workflow + Manual Ad Classification (Critical)
5. Methodology Overview
RQ1 Sensitivity Analysis
RQ2 Comments Perception
RQ3 Algospeak Detection
6. Adding New Videos
7. Data Formats
8. Libraries Used
9. Visualisation Set




## 1. Research Questions

| RQ | Question | Analysis Step |
|----|----------|---------------|
| **RQ1** | How does sensitive content correlate with monetization status? | Step 3: Sensitivity Analysis |
| **RQ2** | How do viewers perceive creator speech alteration? | Step 4: Comments Perception |
| **RQ3** | What algospeak substitutions do creators use? | Step 5: Algospeak Detection |


## API Architecture and Set-up
### Why Two APIs?

| API | Used For | Rationale |
|-----|----------|-----------|
| **Supadata API** | Transcripts | YouTube's `youtube-transcript-api` library aggressively IP-blocks scraping requests. Supadata provides reliable transcript access without IP bans. |
| **YouTube Data API v3** | Metadata, Comments, Replies | Official API with generous quota (10,000/day). Reliable for structured data. |

### Rate Limits & Quotas

| API | Limit | Our Safety Margin | Usage |
|-----|-------|-------------------|-------|
| Supadata (free tier) | 100 videos/month, 1 req/sec | 3 second delay | ~20 used (as of 2024-11-30) |
| YouTube Data API | 10,000 quota/day | 0.5 sec delay | Resets daily |

**Note:** Supadata free tier allows 100 transcript requests per month. Track usage to avoid hitting limits.

---

**API keys are loaded from a .env file (REQUIRED)**

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

## Folder Structure

```
dissertation/
├── config.py                    # Configuration (requires .env file)
├── requirements.txt             # Python dependencies
│
├── scripts/
│   ├── step1_extract_single_video.py    # Test ONE video
│   ├── step2_batch_extract.py           # Extract ALL videos
│   ├── step3_sensitivity_analysis.py    # RQ1: Sensitive word analysis
│   ├── step4_comments_analysis.py       # RQ2: Comment perception
│   ├── step5_algospeak_detection.py     # RQ3: Algospeak in transcripts + comments
│   ├── step6_generate_report.py         # Compile Excel report
│   ├── step7_visualizations.py          # Generate charts
│   └── utils/                           # Helper functions
│
├── data/
│   ├── input/video_urls.csv             # Video list with manual ad status
│   ├── raw/{video_id}/                  # Extracted data per video
│   ├── output/                          # Current analysis results
│   └── archive/                         # Previous run archives
│
├── dictionaries/
    ├── sensitive_words.json             
    └── perception_keywords.json         
```
---
## Workflow

### Initial Setup

```bash
cd dissertation
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env file with your API keys
cp .env.example .env
# Edit .env and add your actual API keys

# Note: config.py is already included, no need to copy it
```

### Step 1: Test Single Video

```bash
python scripts/step1_extract_single_video.py "VIDEO_URL"
```

Tests extraction pipeline on one video before batch processing.

## Manual Ad Status Classification (Critical Step)

This stage provides the ground truth for monetisation status in my dataset. Because YouTube does not expose monetisation information through any API, I must determine it manually before running the analysis.

### Why I Needed to Classify Ads Manually

I observed that YouTube’s ad delivery is highly personalised and cannot be reliably inferred through automated means. Specifically:

- YouTube does not return monetisation status via the public API.
- I found that automated detection methods vary due to:
  - regional differences in ad availability,
  - personalised targeting based on watch history,
  - interference from browser extensions or ad blockers,
  - dynamic changes in YouTube’s ad insertion logic.
- Using incognito mode allowed me to eliminate personalisation as much as possible.
- This manual verification became the dependent variable for RQ1.

Because of these limitations, I manually checked each video to establish a consistent and unbiased ground truth.

---

### How I Classified Ads for Each Video

1. I cleared browsing history and cookies  
   This removed stored preferences that could influence ad delivery.

2. I opened the YouTube link in a new incognito/private window  
   This ensured no extensions or account data affected the results.

3. I visited the video URL and accepted all cookies  
   This allowed ads to load normally.

4. I checked the video for ads by observing:
   - **Starting ads** – I watched for ads that appear before playback.
   - **Mid-roll ads** – I looked for ad markers on the timeline during playback.
   - **Network-level ad insertion** – I opened Developer Tools → Network → filtered for `ad_break` requests.
     - When I saw `ad_break` events, I recorded mid-roll ads as detected.

5. I recorded my findings in `video_urls.csv`:
   - `starting_ads`: Yes/No
   - `mid_roll_ads`: Yes/No
   - `ad_breaks_detected`: Yes/No

On average, it took me about **2–3 minutes** to classify each video.

---

### What I Observed During Classification

As I analysed the first 20 videos, I noticed a consistent pattern:

- Whenever I saw **starting ads**, I also observed **mid-roll `ad_break` requests** in the network tab.
- Whenever I did **not** see starting ads, I never observed any mid-roll `ad_break` events.

This relationship held across the rest of the dataset. I therefore treated the presence of starting ads as a strong indicator that the video is monetised.

This empirical observation allowed me to classify videos more confidently and ensured that the monetisation variable used in RQ1 was grounded in direct observation.

---

### Channels I Classified

- **Actual Justice Warrior** — Video IDs 1–51  
- **The Podcast of the Lotus Eaters** — Video IDs 52–71+  

I manually classified every video from these channels before running the extraction scripts.

---

### Reminder for Future Additions

Whenever I add new videos to the dataset, I will repeat this exact classification process before extracting transcripts, comments, or metadata.


### Step 2: Batch Extract All Videos

```bash
python scripts/step2_batch_extract.py
python scripts/step2_batch_extract.py --skip-existing  # Skip already extracted videos
```

**Adding new videos:** Edit `data/input/video_urls.csv`, then run with `--skip-existing` to only extract new videos.

### Step 3-7: Analysis Pipeline

```bash
python scripts/step3_sensitivity_analysis.py   # RQ1
python scripts/step4_comments_analysis.py      # RQ2
python scripts/step5_algospeak_detection.py    # RQ3
python scripts/step6_generate_report.py        # Compile
python scripts/step7_visualizations.py         # Charts
```

**Note:** Steps 3-7 regenerate outputs. Use `--archive` flag to save previous results before re-running.

---


## Analysis Methodology

### Step 3: Sensitivity Analysis (RQ1)

**Purpose:** Quantify sensitive/controversial content in transcripts to predict monetization status.

**Method:**
1. Load transcript text
2. Tokenize and lemmatize using NLTK
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

**Purpose:** Detect viewer awareness of monetization pressure and speech alteration.

**Method:**
1. Load all comments + replies (flattened)
2. Identify creator vs viewer comments (using `channel_id` matching)
3. Search for 90 perception keywords across 7 categories using **word boundary regex** (avoids false positives like "corn" matching "corner")

**Categories:**
- `monetization_pressure`: demonetized, yellow dollar, adpocalypse
- `algospeak_and_slang`: unalive, seggs, code words
- `censorship_behavior`: can't say, self-censor, youtube won't let
- `editing_artifacts`: bleep, muted, jump cut
- `compliance_and_fear`: walking on eggshells, watered down, family friendly
- `off_platform_diversion`: patreon, rumble, uncensored version
- `suppression_mechanisms`: shadowban, throttled, restricted mode

**Design Decision:** Removed ambiguous keywords (corn, locals, silence, buried, hidden) that caused false positives in v2.0 → v2.1.

**Output:** 
- `comments_perception.csv` - All matching comments with `is_creator` flag
- `comments_perception_summary.csv` - Per-video summary with creator vs viewer breakdown

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

### Step 7: Visualizations

**Charts Generated:**
1. Risk% vs Starting Ads (scatter)
2. Risk% by Ad Status (box plot)
3. Risk% vs Upload Year (scatter with trend)
4. Average Risk% by Ad Status (bar)
5. Risk% vs View Count (scatter, log scale)
6. Risk% Distribution (histogram with thresholds)
7. Classification Distribution (pie)

**Output:** `charts/*.png`

---


## Adding New Videos

1. **Edit `data/input/video_urls.csv`** - Add new rows with URL
2. **⚠️ MANUALLY CLASSIFY AD STATUS** - For each new video, follow the Manual Ad Status Classification protocol (see section above) and fill in `starting_ads`, `mid_roll_ads`, and `ad_breaks_detected` columns
3. **Extract new videos only:**
   ```bash
   python scripts/step2_batch_extract.py --skip-existing
   ```
4. **Archive previous output:**
   ```bash
   python scripts/step3_sensitivity_analysis.py --archive
   # Or manually: mv data/output data/archive/run_YYYYMMDD_HHMMSS
   ```
5. **Re-run analysis (steps 3-7)**

---

## Data Formats

### video_urls.csv

```csv
url,channel_name,starting_ads,mid_roll_ads,ad_breaks_detected,notes
https://www.youtube.com/watch?v=VIDEO_ID,Channel Name,Yes,No,Yes,Notes here
```

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

## Python Libraries Used

### Core Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **pandas** | >=2.0 | Data manipulation, CSV/Excel reading/writing, DataFrame operations |
| **requests** | >=2.28 | HTTP requests to Supadata API for transcript fetching |
| **google-api-python-client** | >=2.0 | Official YouTube Data API v3 client for metadata/comments |

### NLP Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **nltk** | >=3.8 | Natural Language Toolkit for text tokenization and lemmatization |
| - `word_tokenize` | | Splits transcript text into individual word tokens |
| - `WordNetLemmatizer` | | Reduces words to base form (running→run, killed→kill) |
| - `stopwords` | | Filters common words (the, is, and) for cleaner analysis |

### Visualization Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **matplotlib** | >=3.7 | Primary plotting library for all chart generation |
| - `pyplot` | | High-level interface for creating figures and axes |
| - `dates` | | Date formatting for time-series charts |
| **seaborn** | >=0.12 | Statistical visualization built on matplotlib |
| - Provides cleaner default styling (`seaborn-v0_8-whitegrid`) |
| - Better color palettes and statistical plots (boxplots) |
| **numpy** | >=1.24 | Numerical computing for trend line calculations |

### File Handling

| Library | Version | Purpose |
|---------|---------|---------|
| **openpyxl** | >=3.1 | Excel file reading/writing (.xlsx format) |
| **json** | stdlib | JSON parsing for comments, metadata, dictionaries |
| **csv** | stdlib | CSV file handling for video_urls.csv |
| **re** | stdlib | Regular expressions for word boundary matching |

---

## Step 7: Visualization Documentation

### Why These Charts?

Each visualization serves a specific purpose in answering the research questions and validating findings.

---

### RQ1 Visualizations (Sensitivity Analysis)

#### Chart 01: Risk% vs Starting Ads (Scatter)
**Purpose:** Test the core hypothesis - does sensitive content correlate with ad removal?
- X-axis: Binary (Has Ads / No Ads)
- Y-axis: Sensitive ratio percentage
- **What to look for:** If hypothesis is correct, "No Ads" videos should cluster at higher risk% values
- **Threshold lines:** T2 (2%) and T1 (3%) from pilot study classification

#### Chart 02: Risk% by Ad Status (Box Plot)
**Purpose:** Compare distribution characteristics between monetized and demonetized videos.
- Shows median, quartiles, and outliers for each group
- **What to look for:** 
  - Median difference between groups
  - Spread (variance) within each group
  - Outliers that don't fit the pattern

#### Chart 03: Risk% vs Upload Year (Scatter with Trend)
**Purpose:** Detect temporal patterns - has YouTube's moderation changed over time?
- Tests if newer videos show different risk patterns
- Trend line shows direction of change
- **What to look for:** 
  - Downward trend = creators may be self-censoring more over time
  - Upward trend = more boundary-pushing content recently

#### Chart 04: Average Risk% by Ad Status (Bar)
**Purpose:** Simple comparison of mean sensitive ratio between groups.
- Easy-to-understand summary statistic
- Bar labels show exact percentages
- **What to look for:** Clear height difference suggests relationship

#### Chart 05: Risk% vs View Count (Scatter, Log Scale)
**Purpose:** Test if sensitive content affects video reach/promotion.
- Log scale handles wide range (thousands to millions of views)
- **What to look for:** 
  - Negative correlation = sensitive content gets fewer views (suppression?)
  - Positive correlation = controversial content gets more engagement

#### Chart 06: Risk% Distribution (Histogram)
**Purpose:** Understand the overall distribution of content sensitivity.
- Shows how many videos fall into each risk% range
- Threshold lines divide into classification zones
- **What to look for:** 
  - Normal distribution = natural variation
  - Bimodal = two distinct content strategies
  - Right-skewed = most videos low-risk with some outliers

#### Chart 07: Classification Distribution (Pie)
**Purpose:** Summary of how videos are classified based on thresholds.
- Shows proportion of "Likely Monetised" vs "Uncertain" vs "Likely Demonetised"
- **What to look for:** Sample balance and classification accuracy validation

---

### RQ2 Visualizations (Perception Analysis)

#### Chart 08: Perception Categories (Horizontal Bar)
**Purpose:** Which aspects of YouTube moderation do viewers notice most?
- Ranks the 7 perception categories by comment mentions
- **What to look for:**
  - If "monetization_pressure" is high → viewers consciously aware of ad economics
  - If "censorship_behavior" is high → viewers notice speech alteration
  - If "algospeak_and_slang" is high → viewers participate in coded language

#### Chart 09: Top Videos by Perception Ratio (Horizontal Bar)
**Purpose:** Identify which videos generate the most viewer awareness comments.
- Top 10 videos ranked by perception comment ratio
- **What to look for:**
  - Do high-perception videos correlate with demonetized videos?
  - Are certain topics more likely to trigger viewer awareness?
  - Outliers for case study analysis

---

### RQ3 Visualizations (Algospeak Analysis)

#### Chart 10: Algospeak in Transcripts vs Comments (Grouped Bar)
**Purpose:** Compare creator self-censorship (transcripts) with viewer mimicry (comments).
- Blue bars = Creator speech (direct evidence of self-censorship)
- Red bars = Viewer comments (shows awareness/adoption of algospeak)
- **What to look for:**
  - If transcripts > comments → Creator actively using coded language
  - If comments > transcripts → Viewers use more algospeak than creator
  - Pattern differences across videos

#### Chart 11: Top Algospeak Terms (Horizontal Bar)
**Purpose:** Identify the most common coded language substitutions.
- Shows term frequency with original meaning annotation
- **What to look for:**
  - Which categories dominate (profanity? violence? drugs?)
  - Specific terms to cite in dissertation
  - Evidence of evolving internet vocabulary

#### Chart 12: Algospeak by Category (Pie)
**Purpose:** Distribution of algospeak across content categories.
- Shows which types of sensitive content get the most coded substitutions
- **What to look for:**
  - If "profanity" dominates → Casual self-censorship (avoid strikes)
  - If "violence_death" dominates → Serious topic avoidance
  - If "platform_moderation" dominates → Meta-discussion about censorship itself

---

### Combined Insight Visualizations

#### Chart 13: Risk% vs Algospeak Count (Scatter with Correlation)
**Purpose:** Test relationship between content sensitivity and coded language usage.
- **Key question:** Do creators of high-risk content use MORE algospeak as evasion?
- Correlation coefficient shows strength/direction of relationship
- **What to look for:**
  - Positive correlation → High-risk creators actively evade detection
  - No correlation → Algospeak used independently of content risk
  - Negative correlation → Low-risk creators use MORE algospeak (preemptive?)

---