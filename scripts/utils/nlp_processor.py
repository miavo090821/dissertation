# nlp processor
#
# nlp processor
#
# 1. prepares transcript text for analysis by tokenising, cleaning, and lemmatising it
# 2. loads the sensitive-word dictionary from JSON files
# 3. counts both single-word and phrase-based sensitive matches
# 4. calculates a sensitive-word ratio for each transcript
# 5. supports category-level analysis for different types of sensitive content
# 6. includes helper utilities for monetisation classification, word frequencies,
#    and extracting context snippets for qualitative interpretation


# json is part of Python's standard library.
# We use it to read the sensitive-words dictionary stored in a .json file
# For example, it lets us load structured data such as:
# {
#   "words": ["kill", "suicide", "drug use"]
# }
import json

# os is part of Python's standard library.
# We use it for file and folder operations, such as:
# - checking whether a path exists
# - building file paths safely across operating systems
# - finding the user's home directory for nltk_data
import os

# string is part of Python's standard library.
# We use it mainly for string.punctuation, which gives us a ready-made
# list of punctuation characters like . , ! ? : ; and so on
# This helps us remove punctuation during text cleaning
import string

# shutil is part of Python's standard library
# It is used for high-level file and folder operations
# Here we use it to delete a corrupted NLTK resource folder
# before re-downloading a clean copy
import shutil

# nltk is a third-party NLP library (Natural Language Toolkit)
# It provides the main language-processing tools we need, including:
# - tokenisation
# - lemmatisation
# - downloadable language resources such as punkt and wordnet
# This is the core NLP library used in this file
import nltk

# word_tokenize is a tokenizer function from NLTK
# Tokenisation means splitting text into smaller units, usually words
# Example:
# "I was running fast." -> ["I", "was", "running", "fast", "."]
# We use this before cleaning and lemmatising the transcript
from nltk.tokenize import word_tokenize

# WordNetLemmatizer is an NLTK lemmatisation tool.
# Lemmatisation reduces words to their base or dictionary form
# Example:
# - "running" -> "run"
# - "runs" -> "run"
# - "children" -> "child"   (in some cases depending on context/rules)
# We use this so different word forms can match the same sensitive-word entry.
from nltk.stem import WordNetLemmatizer


def ensure_nltk_resources():
    """checks that all the nltk data packages we need are installed,
    and re-downloads any that are missing or corrupted."""

    # Why this matters:
    # - NLTK code often depends on external data packages, not just the library itself.
    # - For example, tokenisation needs 'punkt', and lemmatisation relies on WordNet
    # - If these resources are missing, NLTK will raise LookupError
    # - Sometimes a resource folder exists but is corrupted, so we also handle that case

    # Resources used here:
    # - punkt: sentence/word tokenisation support
    # - wordnet: lexical database used for lemmatisation
    # - omw-1.4: multilingual WordNet support, often needed by WordNet tools
    # - stopwords: not directly used below yet, but useful if this pipeline expands
    
    resources = [
        ('tokenizers/punkt', 'punkt'),
        ('corpora/wordnet', 'wordnet'),
        ('corpora/omw-1.4', 'omw-1.4'),
        ('corpora/stopwords', 'stopwords')
    ]

    # Loop through each required resource and check whether it exists locally
    for path, name in resources:
        resource_available = False

        try:
            # try to locate the resource in the user's NLTK data folders
            nltk.data.find(path)
            resource_available = True

        except LookupError:
            # this means the resource is simply not installed
            pass

        except OSError:
            # this can happen if the resource exists but is corrupted
            # in that case, we try to delete the broken folder and re-download it.
            print(f"  [NLTK] Resource {name} appears corrupted, re-downloading...")
            try:
                # Default NLTK data location in the home directory
                nltk_data_dir = os.path.expanduser('~/nltk_data')

                # if that folder does not exist, try to infer an NLTK path.
                if not os.path.exists(nltk_data_dir):
                    try:
                        nltk_data_dir = nltk.data.find('')
                    except:
                        # fallback: build the standard home/nltk_data path manually
                        nltk_data_dir = os.path.join(os.path.expanduser('~'), 'nltk_data')

                # construct the full path to the suspected corrupted resource
                resource_path = os.path.join(nltk_data_dir, path)

                # Remove it so a clean version can be downloaded
                if os.path.exists(resource_path):
                    shutil.rmtree(resource_path, ignore_errors=True)

            except Exception:
                # If cleanup fails, we do not crash the whole script
                pass

        # if the resource was missing or corrupted, try to download it
        if not resource_available:
            print(f"  [NLTK] Downloading {name}...")
            try:
                nltk.download(name, quiet=False)

                # after download, check again to confirm it now exists
                try:
                    nltk.data.find(path)
                    resource_available = True
                except:
                    pass

            except Exception as e:
                # If the download fails, warn the user but avoid killing the program
                print(f"  [NLTK] Warning: Could not download {name}: {e}")
                pass

# Run the resource check immediately when this file is loaded,
# so later functions can assume tokenisation/lemmatisation will work
ensure_nltk_resources()

# Create one reusable lemmatiser object at module level
# This is more efficient than creating a new one every time we process text
_lemmatizer = WordNetLemmatizer()


def load_sensitive_words(filepath: str) -> tuple:
    """reads the sensitive words json and splits them into single words vs multi-word
    phrases - we need to handle these differently during matching."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

 # expecting a structure like:
    # {
    #   "words": ["kill", "suicide", "self harm", "hard-drugs"]
    # }
    words = data.get('words', [])

    singles = set()
    phrases = []

    for term in words:
        term_lower = term.lower()

        # if the term contains a space or hyphen, treat it as a phrase
        if ' ' in term_lower or '-' in term_lower:
            phrases.append(term_lower)
        else:
            # Otherwise treat it as a single-token term
            singles.add(term_lower)

    return singles, phrases


def load_sensitive_words_by_category(filepath: str) -> dict:
    """same as load_sensitive_words but grouped by category
    returns dict of category_name -> (singles_set, phrases_list)."""

     """
    Load sensitive words grouped by category from JSON.

    Expected structure:
    {
      "categories": {
        "violence": {"words": [...]},
        "sexual": {"words": [...]},
        "drugs": {"words": [...]}
      }
    }

    Returns:
        {
          "violence": (singles_set, phrases_list),
          "sexual": (singles_set, phrases_list),
          ...
        }

    Why this is useful:
    - The normal load_sensitive_words() function only gives an overall dictionary.
    - this version preserves category structure so we can later ask:
      "Which type of sensitive content appears most?"
    """
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

        # store each category as a tuple of (single-word terms, phrase terms)
        result[cat_name] = (singles, phrases)

    return result


def analyze_transcript_by_category(transcript_text: str, sensitive_words_path: str) -> dict:
    """runs the sensitive word analysis per category so we can see which types
    of sensitive content show up most in each transcript."""

    """
    Analyse a transcript category by category

    example output:
    {
      "violence": {"count": 4, "found_terms": ["kill", "weapon"]},
      "sexual": {"count": 1, "found_terms": ["nude"]}
    }

    Why this matters:
    - A total sensitive count alone does not show what kind of content is present
    - Category-level analysis lets you compare patterns across videos more meaningfully
    """

    if not transcript_text:
        return {}

    # load the category-aware sensitive dictionary
    categories = load_sensitive_words_by_category(sensitive_words_path)

    # clean and lemmatise transcript once, then reuse it for every category
    tokens = clean_and_lemmatize(transcript_text)

    result = {}
    for cat_name, (singles, phrases) in categories.items():
        count, found = count_sensitive_matches(transcript_text, tokens, singles, phrases)
        # count matches for just this category
        result[cat_name] = {
            'count': count,
            'found_terms': found
        }

    return result


def clean_and_lemmatize(text: str) -> list:
    """tokenises and lemmatises the text - does verb then noun lemmatisation
    so we catch as many word form variations as possible."""

    # Steps:
    # 1. Lowercase the text so matching is case-insensitive
    # 2. Tokenise into words/punctuation
    # 3. Remove punctuation tokens
    # 4. Lemmatise each token:
    #    - first as a verb
    #    - then as a noun

    # Why do both verb and noun lemmatisation?
    #  different word forms may reduce differently depending on grammatical role
    #  doing verb first, then noun, helps catch more variants in practice.
    # - Example:
    #     "running" -> "run"
    #     "runs" -> "run"

    try:
        # tokenise the lowercase text into individual tokens
        tokens = word_tokenize(text.lower())

    except LookupError:
        # if tokeniser resources are missing, try restoring them and retry
        ensure_nltk_resources()
        tokens = word_tokenize(text.lower())

    clean_tokens = []

    for token in tokens:
        # skip punctuation such as .,!?() because it is not meaningful
        # for dictionary matching in this task
        if token in string.punctuation:
            continue

        # lemmatise as verb first
        # example: "running" -> "run"
        lemma = _lemmatizer.lemmatize(token, pos='v')

        # then lemmatise the result as noun
        # this can further normalise certain tokens
        lemma = _lemmatizer.lemmatize(lemma, pos='n')

        clean_tokens.append(lemma)

    return clean_tokens

def count_sensitive_matches(raw_text: str, tokens: list,
                           single_terms: set, phrase_terms: list) -> tuple:
    """counts how many sensitive terms appear. phrases get checked against the raw
    text (since tokenising breaks them up), singles get checked against lemmatised tokens."""

     """
    count sensitive-term matches in a transcript

    Matching logic:
    - phrase terms are matched against the raw lowercase text
      because phrases span multiple words
    - single-word terms are matched against cleaned/lemmatised tokens

    Returns:
        (count, found_terms)
        count = total number of matches
        found_terms = unique sensitive terms found

    Important notes:
    - phrase counting uses raw_lower.count(phrase), so it counts literal substring matches
    - Single-word counting counts every token occurrence
    """

    count = 0
    found = []

    # Lowercase the raw text for case-insensitive phrase matching
    raw_lower = raw_text.lower()

    # phrases need raw text matching since they span multiple tokens
    # Example: detect "self harm" in the original transcript text.
    for phrase in phrase_terms:
        matches = raw_lower.count(phrase)


        if matches > 0:
            count += matches
            found.append(phrase)

    # single words match against our lemmatised token list
    # Example: detect "kill" in the cleaned token list.
    for token in tokens:
        if token in single_terms:
            count += 1
            found.append(token)
 
 # Convert found terms to a unique list so repeated matches do not repeat in output.
    return count, list(set(found))


def analyze_transcript(transcript_text: str, sensitive_words_path: str) -> dict:
    """takes the raw transcript text and checks it against our sensitive words dictionary.
    returns the count, ratio, and which words were found."""

    # Main transcript-analysis function.

    # What it does:
    # 1. Load the sensitive-word dictionary.
    # 2. Clean and lemmatise the transcript.
    # 3. Count sensitive-word matches.
    # 4. Calculate the sensitive ratio:
    #        sensitive_count / total_words * 100
    # 5. Return a summary dictionary.

    # Returns:
    #     {
    #       'total_words': int,
    #       'sensitive_count': int,
    #       'sensitive_ratio': float,
    #       'found_terms': list
    #     }

    if not transcript_text:
        # # If the transcript is empty or missing, return a safe default result.
   
        return {
            'total_words': 0,
            'sensitive_count': 0,
            'sensitive_ratio': 0.0,
            'found_terms': []
        }

    # load sensitive dictionary split into single words and phrases
    singles, phrases = load_sensitive_words(sensitive_words_path)

    # clean and normalise the transcript text
    tokens = clean_and_lemmatize(transcript_text)

    # total words is based on cleaned tokens, not raw whitespace splitting
    total_words = len(tokens)

    # count sensitive matches using both phrase and token matching strategies
    sensitive_count, found_terms = count_sensitive_matches(
        transcript_text, tokens, singles, phrases
    )

    # convert raw count into a percentage of transcript length
    sensitive_ratio = (sensitive_count / total_words * 100) if total_words > 0 else 0.0

    return {
        'total_words': total_words,
        'sensitive_count': sensitive_count,
        'sensitive_ratio': round(sensitive_ratio, 4),
        # keep only the first 20 found terms so output stays manageable.
        'found_terms': found_terms[:20]
    }


def classify_monetization(sensitive_ratio: float, has_ads: bool = None) -> str:
    """classifies monetisation likelihood based on thresholds we picked from the data.
    under 2% = probably monetised, over 3% = probably demonetised, between = uncertain."""

    # Threshold logic:
    # - below 2.0%  -> Likely Monetised
    # - above 3.0%  -> Likely Demonetised
    # - between     -> Uncertain

#  uncertain is the probability that falls into other aspects: membership content only,...
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
 
    # Build a frequency dictionary from a list of tokens.

    # Example:
    #     ["run", "run", "fast"] -> {"run": 2, "fast": 1}

    # Why this is useful:
    # - It helps identify which words dominate a transcript
    # - It can support exploratory analysis or qualitative interpretation

    # returns:
    #     A dictionary sorted from most frequent to least frequent.
    

    freq = {}
    for token in tokens:

         # Increment count if token already exists, otherwise start at 1.
        freq[token] = freq.get(token, 0) + 1

# Sort by frequency descending
    return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))


def extract_context_snippets(text: str, term: str, window: int = 50) -> list:
    """grabs the text around each sensitive term occurrence so we can see
    how it's being used in context. returns up to 5 snippets."""
    
    snippets = []

    # Lowercase versions are used only for searching positions
    # we still extract snippets from the original text so original capitalisation is preserved
    text_lower = text.lower()
    term_lower = term.lower()

# Why this is useful:
    # - a raw count tells us that a term appeared
    # - a context snippet helps us understand how it was used
    # - this supports qualitative interpretation alongside quantitative counts

    start = 0
     # start searching from the beginning of the text

    while True:
        pos = text_lower.find(term_lower, start) # Find the next match position
        
         # stop once there are no more matches
        if pos == -1:
            break

        # compute snippet boundaries while staying inside the text length
        snippet_start = max(0, pos - window)
        snippet_end = min(len(text), pos + len(term) + window)

        # extract the original-text snippet
        snippet = text[snippet_start:snippet_end]

        # Add ellipsis if the snippet does not start at the beginning of the text
        if snippet_start > 0:
            snippet = "..." + snippet

        # add ellipsis if the snippet does not end at the end of the text
        if snippet_end < len(text):
            snippet = snippet + "..."

        # replace line breaks with spaces so the snippet is easier to display
        snippets.append(snippet.replace('\n', ' ').strip())

        # move forward and continue searching for later matches
        start = pos + 1

    # limit to 5 snippets so output remains readable
    return snippets[:5]