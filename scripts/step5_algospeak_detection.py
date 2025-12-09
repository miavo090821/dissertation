# Step 5: Algospeak Detection (RQ3)

# Detect coded language (algospeak) in transcripts and comments.
# Uses word boundary matching to avoid false positives.
# Separates creator vs viewer usage.

import sys
import os
import csv
import json
import re
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATA_RAW_DIR, DATA_OUTPUT_DIR, ALGOSPEAK_FINDINGS_FILE
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

from scripts.utils.algospeak_dict import (
    ALGOSPEAK_DICT,
    ALGOSPEAK_CATEGORIES,
    get_category
)

def get_extracted_videos(raw_dir: str) -> list:

def load_transcript(raw_dir: str, video_id: str) -> str:

def load_comments(raw_dir: str, video_id: str) -> list:
    
def load_metadata(raw_dir: str, video_id: str) -> dict:
    
def detect_algospeak_with_boundaries(text: str) -> list:
    
def archive_output(output_dir: str) -> str:
    
def main():