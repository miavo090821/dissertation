# NLP Processor for Sensitive Word Analysis
# Handles text preprocessing, lemmatisation, and sensitive term detection
#  for step 3 
import json
import os
import string
import shutil
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


def ensure_nltk_resources():
    # Ensure required NLTK datasets are installed and not corrupted
    resources = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/wordnet', 'wordnet'),
        ('corpora/omw-1.4', 'omw-1.4'),
        ('corpora/stopwords', 'stopwords')
    ]
    
    for path, name in resources:
        resource_available = False
        try:
            # Attempt to find resource locally
            nltk.data.find(path)
            resource_available = True
        except LookupError:
            # Resource missing; must download
            pass
        except OSError:
            # Resource corrupted or incomplete; remove and re-download
            print(f"  [NLTK] Resource {name} appears corrupted, re-downloading...")
            try:
                nltk_data_dir = os.path.expanduser('~/nltk_data')
                if not os.path.exists(nltk_data_dir):
                    # Try alternative search paths
                    try:
                        nltk_data_dir = nltk.data.find('')
                    except:
                        nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')
                
                # Remove corrupted files if found
                resource_path = os.path.join(nltk_data_dir, path)
                if os.path.exists(resource_path):
                    shutil.rmtree(resource_path, ignore_errors=True)
            except Exception:
                pass
        
        # Download if unavailable
        if not resource_available:
            print(f"  [NLTK] Downloading {name}...")
            try:
                nltk.download(name, quiet=False)
                # Verify after download
                try:
                    nltk.data.find(path)
                    resource_available = True
                except:
                    pass
            except Exception as e:
                print(f"  [NLTK] Warning: Could not download {name}: {e}")
                pass


# Initialise NLTK resources on import
ensure_nltk_resources()

# Create a single lemmatiser instance
_lemmatizer = WordNetLemmatizer()


def load_sensitive_words(filepath: str) -> tuple:
    # Load sensitive words from JSON file and separate single words from multi-word phrases
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    words = data.get('words', [])
    
    singles = set()
    phrases = []
    
    # Distinguish between single terms and phrases
    for term in words:
        term_lower = term.lower()
        if ' ' in term_lower or '-' in term_lower:
            phrases.append(term_lower)
        else:
            singles.add(term_lower)
    
    return singles, phrases


def clean_and_lemmatize(text: str) -> list:
    # Convert raw text into cleaned, lemmatised tokens
    try:
        tokens = word_tokenize(text.lower())
    except LookupError:
        # Fallback if tokenizer missing
        ensure_nltk_resources()
        tokens = word_tokenize(text.lower())
    
    clean_tokens = []
    for token in tokens:
        # Remove punctuation
        if token in string.punctuation:
            continue
        
        # Apply verb then noun lemmatisation
        lemma = _lemmatizer.lemmatize(token, pos='v')
        lemma = _lemmatizer.lemmatize(lemma, pos='n')
        clean_tokens.append(lemma)
    
    return clean_tokens


def count_sensitive_matches(raw_text: str, tokens: list, 
                           single_terms: set, phrase_terms: list) -> tuple:
    # Count sensitive term appearances in transcript using both raw text and tokens
    count = 0
    found = []
    raw_lower = raw_text.lower()
    
    # Check phrase occurrences in raw text
    for phrase in phrase_terms:
        matches = raw_lower.count(phrase)
        if matches > 0:
            count += matches
            found.append(phrase)
    
    # Check single word matches in lemmatised tokens
    for token in tokens:
        if token in single_terms:
            count += 1
            found.append(token)
    
    return count, list(set(found))


def analyze_transcript(transcript_text: str, sensitive_words_path: str) -> dict:
    # Analyse transcript and compute sensitive word statistics
    if not transcript_text:
        # Return empty result for missing transcript
        return {
            'total_words': 0,
            'sensitive_count': 0,
            'sensitive_ratio': 0.0,
            'found_terms': []
        }
    
    # Load dictionaries
    singles, phrases = load_sensitive_words(sensitive_words_path)
    
    # Process text into lemmatised tokens
    tokens = clean_and_lemmatize(transcript_text)
    total_words = len(tokens)
    
    # Count sensitive term appearances
    sensitive_count, found_terms = count_sensitive_matches(
        transcript_text, tokens, singles, phrases
    )
    
    # Calculate sensitive word ratio
    sensitive_ratio = (sensitive_count / total_words * 100) if total_words > 0 else 0.0
    
    return {
        'total_words': total_words,
        'sensitive_count': sensitive_count,
        'sensitive_ratio': round(sensitive_ratio, 4),
        'found_terms': found_terms[:20]
    }


def classify_monetization(sensitive_ratio: float, has_ads: bool = None) -> str:
    # Classify monetisation likelihood based on sensitive word ratio thresholds
    T2_THRESHOLD = 2.0
    T1_THRESHOLD = 3.0
    
    if sensitive_ratio < T2_THRESHOLD:
        return "Likely Monetised"
    elif sensitive_ratio > T1_THRESHOLD:
        return "Likely Demonetised"
    else:
        return "Uncertain"


def get_word_frequencies(tokens: list) -> dict:
    # Generate word frequency table sorted by highest count
    freq = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1
    
    return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))


def extract_context_snippets(text: str, term: str, window: int = 50) -> list:
    # Extract local context around sensitive terms for qualitative analysis
    snippets = []
    text_lower = text.lower()
    term_lower = term.lower()
    
    start = 0
    while True:
        # Locate next appearance of term
        pos = text_lower.find(term_lower, start)
        if pos == -1:
            break
        
        # Compute snippet bounds
        snippet_start = max(0, pos - window)
        snippet_end = min(len(text), pos + len(term) + window)
        
        # Extract segment
        snippet = text[snippet_start:snippet_end]
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(text):
            snippet = snippet + "..."
        
        # Clean newlines
        snippets.append(snippet.replace('\n', ' ').strip())
        
        # Continue search
        start = pos + 1
    
    return snippets[:5]
