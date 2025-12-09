# NLP Processor for Sensitive Word Analysis

import os
import json
from typing import List, Dict   
from collections import Counter
from config import DATA_RAW_DIR, DATA_OUTPUT_DIR
from scripts.utils.nlp_processor import NLPProcessor
def analyze_transcript(transcript: str, sensitive_words: List[str]) -> Dict[str, int]:
    # Analyze transcript for sensitive word occurrences.
    nlp = NLPProcessor(sensitive_words)
    word_counts = nlp.count_sensitive_words(transcript)
    return word_counts
def classify_monetization(sensitive_word_count: int, total_words: int) -> str:
    # Classify monetization likelihood based on sensitive word ratio.
    ratio = sensitive_word_count / total_words if total_words > 0 else 0
    if ratio > 0.05:
        return "High Risk"
    elif ratio > 0.02:
        return "Medium Risk"
    else:
        return "Low Risk"       
    