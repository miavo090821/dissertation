# NLP Processor for Sensitive Word Analysis

# Import standard libraries needed for file handling, text processing, and NLTK usage
import json
import os
import string
import shutil
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Ensure NLTK resources are available or re-downloaded if missing or corrupted
def ensure_nltk_resources():
    # List of required NLTK components and their lookup paths
    resources = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/wordnet', 'wordnet'),
        ('corpora/omw-1.4', 'omw-1.4'),
        ('corpora/stopwords', 'stopwords')
    ]
    
    for path, name in resources:
        resource_available = False
        try:
            # Try to find resource locally
            nltk.data.find(path)
            resource_available = True
        except LookupError:
            # Resource missing and must be downloaded
            pass
        except OSError:
            # Resource exists but is corrupted, so re-download
            print(f"  [NLTK] Resource {name} appears corrupted, re-downloading...")
            try:
                # Attempt to remove corrupted resource
                nltk_data_dir = os.path.expanduser('~/nltk_data')
                if not os.path.exists(nltk_data_dir):
                    try:
                        nltk_data_dir = nltk.data.find('')
                    except:
                        nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
                
                resource_path = os.path.join(nltk_data_dir, path)
                if os.path.exists(resource_path):
                    shutil.rmtree(resource_path, ignore_errors=True)
            except Exception:
                pass
        
        if not resource_available:
            # Attempt to download missing resource
            print(f"  [NLTK] Downloading {name}...")
            try:
                nltk.download(name, quiet=False)
                try:
                    nltk.data.find(path)
                    resource_available = True
                except:
                    pass
            except Exception as e:
                print(f"  [NLTK] Warning: Could not download {name}: {e}")
                pass

# Load necessary NLTK components before running any NLP logic
ensure_nltk_resources()

# Initialise global lemmatiser instance for efficiency
_lemmatizer = WordNetLemmatizer()

# Load sensitive word lists from JSON file and separate single words from multi-word phrases
def load_sensitive_words(filepath: str) -> tuple:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    words = data.get('words', [])
    
    singles = set()
    phrases = []
    
    for term in words:
        term_lower = term.lower()
        # Any term containing spaces or hyphens is treated as a phrase
        if ' ' in term_lower or '-' in term_lower:
            phrases.append(term_lower)
        else:
            singles.add(term_lower)
    
    return singles, phrases

# Clean and lemmatise text before checking for sensitive terms
def clean_and_lemmatize(text: str) -> list:
    try:
        # Tokenise text into words
        tokens = word_tokenize(text.lower())
    except LookupError:
        ensure_nltk_resources()
        tokens = word_tokenize(text.lower())
    
    clean_tokens = []
    for token in tokens:
        # Skip punctuation tokens
        if token in string.punctuation:
            continue
        
        # Apply lemmatisation for verb and noun forms
        lemma = _lemmatizer.lemmatize(token, pos='v')
        lemma = _lemmatizer.lemmatize(lemma, pos='n')
        clean_tokens.append(lemma)
    
    return clean_tokens

# Count sensitive word occurrences in both raw text and cleaned token list
def count_sensitive_matches(raw_text: str, tokens: list, 
                           single_terms: set, phrase_terms: list) -> tuple:
    count = 0
    found = []
    raw_lower = raw_text.lower()
    
    # Count phrase matches using direct substring search
    for phrase in phrase_terms:
        matches = raw_lower.count(phrase)
        if matches > 0:
            count += matches
            found.append(phrase)
    
    # Count single word matches using cleaned lemmatised tokens
    for token in tokens:
        if token in single_terms:
            count += 1
            found.append(token)
    
    return count, list(set(found))

# Full transcript analysis combining text cleaning and sensitive-word detection
def analyze_transcript(transcript_text: str, sensitive_words_path: str) -> dict:
    if not transcript_text:
        return {
            'total_words': 0,
            'sensitive_count': 0,
            'sensitive_ratio': 0.0,
            'found_terms': []
        }
    
    # Load word lists
    singles, phrases = load_sensitive_words(sensitive_words_path)
    
    # Clean and tokenise transcript
    tokens = clean_and_lemmatize(transcript_text)
    total_words = len(tokens)
    
    # Count appearances of sensitive terms
    sensitive_count, found_terms = count_sensitive_matches(
        transcript_text, tokens, singles, phrases
    )
    
    # Compute ratio as a percentage
    sensitive_ratio = (sensitive_count / total_words * 100) if total_words > 0 else 0.0
    
    return {
        'total_words': total_words,
        'sensitive_count': sensitive_count,
        'sensitive_ratio': round(sensitive_ratio, 4),
        'found_terms': found_terms[:20]
    }

# Classify monetisation likelihood using thresholds from pilot study
def classify_monetization(sensitive_ratio: float, has_ads: bool = None) -> str:
    T2_THRESHOLD = 2.0
    T1_THRESHOLD = 3.0
    
    if sensitive_ratio < T2_THRESHOLD:
        return "Likely Monetised"
    elif sensitive_ratio > T1_THRESHOLD:
        return "Likely Demonetised"
    else:
        return "Uncertain"
    
# Extract contextual snippets around appearances of specific sensitive terms
def extract_context_snippets(text: str, term: str, window: int = 50) -> list:
    snippets = []
    text_lower = text.lower()
    term_lower = term.lower()
    
    start = 0
    while True:
        # Find next occurrence of the term
        pos = text_lower.find(term_lower, start)
        if pos == -1:
            break
        
        # Remove line breaks and tidy output
        snippets.append(snippet.replace('\n', ' ').strip())
        start = pos + 1
    
    return snippets[:5]
