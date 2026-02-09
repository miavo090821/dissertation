"""
Configuration file for YouTube Self-Censorship Research Project.

INSTRUCTIONS:
1. Create a .env file in the dissertation folder with your API keys:
   
   YOUTUBE_API_KEY=your_youtube_api_key
   SUPADATA_API_KEY=your_supadata_api_key
   
   The .env file will be automatically loaded when you run scripts.
   (The .env file is gitignored and won't be committed)

To get API keys:
- YouTube: https://console.cloud.google.com/apis/credentials
- Supadata: https://supadata.ai/ (for transcripts)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# YouTube Data API v3 Key
# Loads from .env file or environment variable
# Note: Only required for extraction (Step 2). Analysis steps work without it.
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    print("WARNING: YOUTUBE_API_KEY not found - extraction will not work")
    print("To enable extraction, create a .env file with: YOUTUBE_API_KEY=your_key_here")
    YOUTUBE_API_KEY = None  # Allow analysis steps to proceed

# Supadata API Key (for transcript fetching)
# Loads from .env file or environment variable
# Note: Only required for extraction (Step 2). Analysis steps work without it.
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
if not SUPADATA_API_KEY:
    print("WARNING: SUPADATA_API_KEY not found - transcript extraction will not work")
    print("To enable extraction, create a .env file with: SUPADATA_API_KEY=your_key_here")
    SUPADATA_API_KEY = None  # Allow analysis steps to proceed

SUPADATA_BASE_URL = "https://api.supadata.ai/v1/transcript"

# API Settings
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Data Collection Settings
MAX_COMMENTS_PER_VIDEO = 200  # Number of comments to fetch per video
COMMENT_ORDER = "relevance"   # "relevance" or "time"

# File paths (relative to dissertation folder)
DATA_INPUT_DIR = "data/input"
DATA_RAW_DIR = "data/raw"
DATA_OUTPUT_DIR = "data/output"
DICTIONARIES_DIR = "dictionaries"

# Output filenames
SENSITIVITY_SCORES_FILE = "sensitivity_scores.csv"
COMMENTS_ANALYSIS_FILE = "comments_perception.csv"
ALGOSPEAK_FINDINGS_FILE = "algospeak_findings.csv"
FINAL_REPORT_FILE = "analysis_results.xlsx"
AD_DETECTION_FILE = "ad_detection_results.csv"