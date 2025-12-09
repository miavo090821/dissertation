# NLP Processor for Sensitive Word Analysis

import os
import json
from typing import List, Dict   
from collections import Counter
from config import DATA_RAW_DIR, DATA_OUTPUT_DIR
from scripts.utils.nlp_processor import NLPProcessor

def ensure_nltk_resources():
    # Download required NLTK resources if not already present.
    # Handles both missing resources (LookupError) and corrupted resources (OSError).
    
    resources = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/wordnet', 'wordnet'),
        ('corpora/omw-1.4', 'omw-1.4'),
        ('corpora/stopwords', 'stopwords')
    ]
    for path, name in resources:
        resource_available = False
        try:
            nltk.data.find(path)
            resource_available = True
        except (LookupError, OSError):
            pass    
        
        if not resource_available:
            print(f"  [NLTK] Downloading {name}...")
            try:
                nltk.download(name, quiet=False)
                # Verify download worked
                try:
                    nltk.data.find(path)
                    resource_available = True
                except:
                    pass
            except Exception as e:
                print(f"  [NLTK] Warning: Could not download {name}: {e}")
                # Try to continue anyway
                pass

# Initialize NLTK resources
ensure_nltk_resources()

# Initialize lemmatizer
_lemmatizer = WordNetLemmatizer()


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
    # Clean text and return lemmatized tokens.
    # Args:
    #     text: Raw text string
        
    # Returns:
    #     List of cleaned, lemmatized tokens

    try:
        tokens = word_tokenize(text.lower())
    except LookupError:
        ensure_nltk_resources()
        tokens = word_tokenize(text.lower())
    
    clean_tokens = []
    for token in tokens:
        # Skip pure punctuation
        if token in string.punctuation:
            continue
        
        # Lemmatize (try verb first, then noun)
        lemma = _lemmatizer.lemmatize(token, pos='v')
        lemma = _lemmatizer.lemmatize(lemma, pos='n')
        clean_tokens.append(lemma)
    
    return clean_tokens  

def load_sensitive_words(filepath: str) -> tuple:
    # Load sensitive words from JSON file.
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('sensitive_words', [])    

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

def count_sensitive_matches(raw_text: str, tokens: list, 
                           single_terms: set, phrase_terms: list) -> tuple:
    # Count sensitive term matches in text.
    
    # - Phrases are matched against raw (lowercased) text for exact matching
    # - Single words are matched against lemmatized tokens
    
    # Args:
    #     raw_text: Original text (for phrase matching)
    #     tokens: Lemmatized tokens (for single word matching)
    #     single_terms: Set of single sensitive words
    #     phrase_terms: List of sensitive phrases
        
    # Returns:
    #     Tuple of (count, found_terms_list)
    count = 0
    found = []
    raw_lower = raw_text.lower()
    
    # 1. Phrase matching (in raw text)
    for phrase in phrase_terms:
        matches = raw_lower.count(phrase)
        if matches > 0:
            count += matches
            found.append(phrase)
    
    # 2. Single word matching (in lemmatized tokens)
    for token in tokens:
        if token in single_terms:
            count += 1
            found.append(token)
    
    return count, list(set(found))

def classify_monetization(sensitive_ratio: float, has_ads: bool = None) -> str:
    """
    Classify video monetization status based on thresholds from pilot study.
    
    Thresholds (from progress report):
    - T2 (Likely Monetised): Sensitive Ratio < 2.0%
    - T1 (Likely Demonetised): Sensitive Ratio > 3.0%
    - Uncertain: Between 2% and 3%
    
    Args:
        sensitive_ratio: Percentage of sensitive words
        has_ads: Optional - whether video has ads (for validation)
        
    Returns:
        Classification string: "Likely Monetised", "Likely Demonetised", or "Uncertain"
    """
    T2_THRESHOLD = 2.0  # Below this = Likely Monetised
    T1_THRESHOLD = 3.0  # Above this = Likely Demonetised
    
    if sensitive_ratio < T2_THRESHOLD:
        return "Likely Monetised"
    elif sensitive_ratio > T1_THRESHOLD:
        return "Likely Demonetised"
    else:
        return "Uncertain"