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
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    print("ERROR: YOUTUBE_API_KEY not found!")
    print("Create a .env file with: YOUTUBE_API_KEY=your_key_here")
    print("Or set environment variable: export YOUTUBE_API_KEY='your_key_here'")
    sys.exit(1)

# Supadata API Key (for transcript fetching)
# Loads from .env file or environment variable
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
if not SUPADATA_API_KEY:
    print("ERROR: SUPADATA_API_KEY not found!")
    print("Create a .env file with: SUPADATA_API_KEY=your_key_here")
    print("Or set environment variable: export SUPADATA_API_KEY='your_key_here'")
    sys.exit(1)

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