# nlp processor
#
#1. handles all the text preprocessing - cleaning up transcripts before we can count words
#2. uses nltk lemmatisation so "running" and "runs" match the same dictionary entry
#3. the main function analyze_transcript() takes raw text and returns how many sensitive words it found
#4. also has a category breakdown version so we can see which types of sensitive content appear most

import json
import os
import string
import shutil
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


def ensure_nltk_resources():
    """checks that all the nltk data packages we need are installed,
    and re-downloads any that are missing or corrupted."""
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
        except LookupError:
            pass
        except OSError:
            # corrupted resource - nuke it and re-download
            print(f"  [NLTK] Resource {name} appears corrupted, re-downloading...")
            try:
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


ensure_nltk_resources()

_lemmatizer = WordNetLemmatizer()


def load_sensitive_words(filepath: str) -> tuple:
    """reads the sensitive words json and splits them into single words vs multi-word
    phrases - we need to handle these differently during matching."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    words = data.get('words', [])

    singles = set()
    phrases = []

    for term in words:
        term_lower = term.lower()
        if ' ' in term_lower or '-' in term_lower:
            phrases.append(term_lower)
        else:
            singles.add(term_lower)

    return singles, phrases


def load_sensitive_words_by_category(filepath: str) -> dict:
    """same as load_sensitive_words but grouped by category.
    returns dict of category_name -> (singles_set, phrases_list)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    categories = data.get('categories', {})
    result = {}

    for cat_name, cat_data in categories.items():
        words = cat_data.get('words', [])
        singles = set()
        phrases = []
        for term in words:
            term_lower = term.lower()
            if ' ' in term_lower or '-' in term_lower:
                phrases.append(term_lower)
            else:
                singles.add(term_lower)
        result[cat_name] = (singles, phrases)

    return result


def analyze_transcript_by_category(transcript_text: str, sensitive_words_path: str) -> dict:
    """runs the sensitive word analysis per category so we can see which types
    of sensitive content show up most in each transcript."""
    if not transcript_text:
        return {}

    categories = load_sensitive_words_by_category(sensitive_words_path)
    tokens = clean_and_lemmatize(transcript_text)

    result = {}
    for cat_name, (singles, phrases) in categories.items():
        count, found = count_sensitive_matches(transcript_text, tokens, singles, phrases)
        result[cat_name] = {
            'count': count,
            'found_terms': found
        }

    return result


def clean_and_lemmatize(text: str) -> list:
    """tokenises and lemmatises the text - does verb then noun lemmatisation
    so we catch as many word form variations as possible."""
    try:
        tokens = word_tokenize(text.lower())
    except LookupError:
        ensure_nltk_resources()
        tokens = word_tokenize(text.lower())

    clean_tokens = []
    for token in tokens:
        if token in string.punctuation:
            continue

        # verb lemma first, then noun - catches more variations this way
        lemma = _lemmatizer.lemmatize(token, pos='v')
        lemma = _lemmatizer.lemmatize(lemma, pos='n')
        clean_tokens.append(lemma)

    return clean_tokens


def count_sensitive_matches(raw_text: str, tokens: list,
                           single_terms: set, phrase_terms: list) -> tuple:
    """counts how many sensitive terms appear. phrases get checked against the raw
    text (since tokenising breaks them up), singles get checked against lemmatised tokens."""
    count = 0
    found = []
    raw_lower = raw_text.lower()

    # phrases need raw text matching since they span multiple tokens
    for phrase in phrase_terms:
        matches = raw_lower.count(phrase)
        if matches > 0:
            count += matches
            found.append(phrase)

    # single words match against our lemmatised token list
    for token in tokens:
        if token in single_terms:
            count += 1
            found.append(token)

    return count, list(set(found))


def analyze_transcript(transcript_text: str, sensitive_words_path: str) -> dict:
    """takes the raw transcript text and checks it against our sensitive words dictionary.
    returns the count, ratio, and which words were found."""
    if not transcript_text:
        return {
            'total_words': 0,
            'sensitive_count': 0,
            'sensitive_ratio': 0.0,
            'found_terms': []
        }

    singles, phrases = load_sensitive_words(sensitive_words_path)

    tokens = clean_and_lemmatize(transcript_text)
    total_words = len(tokens)

    sensitive_count, found_terms = count_sensitive_matches(
        transcript_text, tokens, singles, phrases
    )

    sensitive_ratio = (sensitive_count / total_words * 100) if total_words > 0 else 0.0

    return {
        'total_words': total_words,
        'sensitive_count': sensitive_count,
        'sensitive_ratio': round(sensitive_ratio, 4),
        'found_terms': found_terms[:20]
    }


def classify_monetization(sensitive_ratio: float, has_ads: bool = None) -> str:
    """classifies monetisation likelihood based on thresholds we picked from the data.
    under 2% = probably monetised, over 3% = probably demonetised, between = uncertain."""
    T2_THRESHOLD = 2.0
    T1_THRESHOLD = 3.0

    if sensitive_ratio < T2_THRESHOLD:
        return "Likely Monetised"
    elif sensitive_ratio > T1_THRESHOLD:
        return "Likely Demonetised"
    else:
        return "Uncertain"


def get_word_frequencies(tokens: list) -> dict:
    """builds a frequency table from tokens, sorted highest count first.
    useful for seeing what words dominate a transcript."""
    freq = {}
    for token in tokens:
        freq[token] = freq.get(token, 0) + 1

    return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))


def extract_context_snippets(text: str, term: str, window: int = 50) -> list:
    """grabs the text around each sensitive term occurrence so we can see
    how it's being used in context. returns up to 5 snippets."""
    snippets = []
    text_lower = text.lower()
    term_lower = term.lower()

    start = 0
    while True:
        pos = text_lower.find(term_lower, start)
        if pos == -1:
            break

        snippet_start = max(0, pos - window)
        snippet_end = min(len(text), pos + len(term) + window)

        snippet = text[snippet_start:snippet_end]
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(text):
            snippet = snippet + "..."

        snippets.append(snippet.replace('\n', ' ').strip())

        start = pos + 1

    return snippets[:5]
