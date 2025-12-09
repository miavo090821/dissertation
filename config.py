import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "output"
DICT_DIR = BASE_DIR / "dictionaries"


# Constants
SENSITIVITY_WORDS_FILE = DICT_DIR / "sensitive_words.json"
PERCEPTION_KEYWORDS_FILE = DICT_DIR / "perception_keywords.json"
ALGOSPEAK_DICT_FILE = DICT_DIR / "algospeak_dict.json" 