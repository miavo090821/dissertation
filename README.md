# dissertation
Investigating YouTube Self-censorship practices
A computational audit of YouTube’s algorithmic moderation, monetisation, and creator self-censorship.

📌 Table of Contents
1. Research Focus
2. API Architecture
3. Folder Structure
4. Full Workflow
5. Methodology Overview
RQ1 Sensitivity Analysis
RQ2 Comments Perception
RQ3 Algospeak Detection
6. Manual Ad Classification (Critical)
7. Adding New Videos
8. Data Formats
9. Libraries Used
10. Visualisation Set




## Research Questions

| RQ | Question | Analysis Step |
|----|----------|---------------|
| **RQ1** | How does sensitive content correlate with monetization status? | Step 3: Sensitivity Analysis |
| **RQ2** | How do viewers perceive creator speech alteration? | Step 4: Comments Perception |
| **RQ3** | What algospeak substitutions do creators use? | Step 5: Algospeak Detection |


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