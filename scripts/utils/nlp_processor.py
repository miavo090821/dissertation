# NLP Processor for Sensitive Word Analysis

import os
import json
from typing import List, Dict   
from collections import Counter
from config import DATA_RAW_DIR, DATA_OUTPUT_DIR
from scripts.utils.nlp_processor import NLPProcessor


def get_word_frequencies(tokens: list) -> dict:
    # Get frequency count of words in a list of tokens.
    return dict(Counter(tokens))    

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
    

def clean_and_lemmatize(text: str) -> list:
    # Clean and lemmatize text into list of words.
    nlp = NLPProcessor([])
    words = nlp.preprocess_text(text)
    return words    

def load_sensitive_words(filepath: str) -> tuple:
    # Load sensitive words from JSON file.
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('sensitive_words', [])    


def classify_monetization(sensitive_ratio: float, has_ads: bool = None) -> str:
    # Classify monetization status based on sensitive content ratio and ad status.
    if has_ads is False:
        return "Demonetized"
    if sensitive_ratio > 0.05:
        return "High Risk"
    elif sensitive_ratio > 0.02:
        return "Medium Risk"
    else:
        return "Low Risk"      


def extract_context_snippets(text: str, term: str, window: int = 50) -> list:
    # Extract context snippets around each occurrence of a term in the text.
    snippets = []
    start = 0
    term_lower = term.lower()
    text_lower = text.lower()
    while True:
        index = text_lower.find(term_lower, start)
        if index == -1:
            break
        snippet_start = max(0, index - window)
        snippet_end = min(len(text), index + len(term) + window)
        snippet = text[snippet_start:snippet_end].strip()
        snippets.append(snippet)
        start = index + len(term)
    return snippets

