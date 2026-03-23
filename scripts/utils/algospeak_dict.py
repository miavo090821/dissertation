# algospeak dictionary and detection
#
#1. maps coded language that creators use to dodge content moderation (e.g. "unalive" = kill)
#2. organised by category so we can analyse which types of algospeak appear most
#3. detect_algospeak() scans text and returns all matches with counts and context
#4. the full analysis function also builds category-level summaries

ALGOSPEAK_DICT = {
    # violence & death
    "unalive": "kill/suicide/dead",
    "unalived": "killed/died",
    "unaliving": "killing/dying",
    "d*e": "die",
    "d!e": "die",
    "de@th": "death",
    "d3ath": "death",
    "kll": "kill",
    "k!ll": "kill",
    "m*rder": "murder",
    "murd3r": "murder",
    "sewerslide": "suicide",
    "sewer slide": "suicide",
    "self delete": "suicide",
    "self-delete": "suicide",
    "final rest": "death/suicide",

    # sexual content
    "seggs": "sex",
    "s3x": "sex",
    "s*x": "sex",
    "secks": "sex",
    "spicy time": "sex",
    "spicy": "sexual",
    "doing the deed": "sex",
    "grape": "rape",
    "graped": "raped",
    "graping": "raping",
    "s.a.": "sexual assault",
    "SA'd": "sexually assaulted",
    "nip nops": "nipples",
    "bewbs": "breasts",
    "bobs": "breasts",
    "corn": "porn",
    "cornography": "pornography",
    "spicy accountant": "sex worker",
    "accountant": "sex worker",
    "onlyfans": "OnlyFans",
    "only fans": "OnlyFans",
    "the hub": "PornHub",

    # profanity
    "fck": "fuck",
    "f*ck": "fuck",
    "f**k": "fuck",
    "effing": "fucking",
    "sht": "shit",
    "sh*t": "shit",
    "bs": "bullshit",
    "b.s.": "bullshit",
    "a$$": "ass",
    "@ss": "ass",
    "btch": "bitch",
    "b*tch": "bitch",

    # drugs & substances
    "unmentionables": "drugs",
    "devil's lettuce": "marijuana",
    "jazz cabbage": "marijuana",
    "mary jane": "marijuana",
    "special brownies": "edibles",
    "nose candy": "cocaine",
    "booger sugar": "cocaine",
    "snow": "cocaine",
    "lucy": "LSD",
    "molly": "MDMA/ecstasy",
    "vitamins": "drugs (general)",
    "supplements": "drugs (general)",

    # mental health
    "le sad": "depression",
    "big sad": "depression",
    "the big D": "depression",
    "panic merchant": "anxiety",
    "spicy brain": "ADHD/mental illness",
    "grippy sock vacation": "psychiatric hospitalization",
    "grippy socks": "mental hospital",

    # political/controversial
    "panini": "pandemic",
    "panoramic": "pandemic",
    "panda express": "pandemic",
    "backpfeifengesicht": "punchable face",
    "accountable": "cancelled",
    "getting cancelled": "being held accountable",
    "ratio'd": "publicly disagreed with",
    "the algorithm": "content moderation system",
    "shadow realm": "shadowbanned",
    "in jail": "banned/suspended",
    "timeout": "banned",

    # violence-adjacent
    "mascara": "gun (in some contexts)",
    "pew pew": "gun/shooting",
    "boom stick": "gun",
    "stabby": "knife",
    "ouch sword": "knife",
    "lead dispenser": "gun",
    "freedom seed dispenser": "gun",

    # platform-specific terms
    "cornfield": "banned (TikTok)",
    "naughty step": "content strike",
    "community guideline": "violation warning",
    "yellow dollar": "demonetized",
    "no money": "demonetized",
    "money gone": "demonetized",
    "ad unfriendly": "demonetized",

    # slurs (censored versions)
    "n-word": "racial slur",
    "the n word": "racial slur",
    "f-slur": "homophobic slur",
    "r-word": "ableist slur",
    "r slur": "ableist slur",
}


# groups terms by semantic category for the category-level analysis
ALGOSPEAK_CATEGORIES = {
    "violence_death": ["unalive", "unalived", "unaliving", "sewerslide", "sewer slide",
                       "self delete", "self-delete", "final rest", "kll", "k!ll",
                       "m*rder", "murd3r", "d*e", "d!e", "de@th", "d3ath"],

    "sexual": ["seggs", "s3x", "s*x", "secks", "spicy time", "grape", "graped",
               "graping", "s.a.", "SA'd", "nip nops", "bewbs", "bobs",
               "corn", "cornography", "spicy accountant", "accountant", "onlyfans", "only fans", "the hub"],

    "profanity": ["fck", "f*ck", "f**k", "effing", "sht", "sh*t", "bs", "b.s.",
                  "a$$", "@ss", "btch", "b*tch"],

    "drugs": ["unmentionables", "devil's lettuce", "jazz cabbage", "mary jane",
              "special brownies", "nose candy", "booger sugar", "snow", "lucy",
              "molly", "vitamins", "supplements"],

    "mental_health": ["le sad", "big sad", "the big D", "panic merchant",
                      "spicy brain", "grippy sock vacation", "grippy socks"],

    "weapons": ["mascara", "pew pew", "boom stick", "stabby", "ouch sword",
                "lead dispenser", "freedom seed dispenser"],

    "platform_moderation": ["cornfield", "naughty step", "yellow dollar",
                           "no money", "money gone", "ad unfriendly", "shadow realm",
                           "in jail", "timeout"]
}

# returns every algospeak term as a flat list
def get_all_algospeak_terms() -> list:
    return list(ALGOSPEAK_DICT.keys())

# looks up what a term actually means, returns none if not in our dict
def get_algospeak_meaning(term: str) -> str:
    return ALGOSPEAK_DICT.get(term.lower())

# figures out which category a term belongs to
def get_category(term: str) -> str:
    """checks each category list to find where this term lives.
    returns 'other' if it's not in any of them."""
    term_lower = term.lower()
    for category, terms in ALGOSPEAK_CATEGORIES.items():
        if term_lower in terms:
            return category
    return "other"

# scans text for all algospeak terms and returns structured results
def detect_algospeak(text: str) -> list:
    """does a simple substring search for every term in our dictionary.
    returns a list of dicts with term, meaning, category, and count, sorted by frequency."""
    text_lower = text.lower()
    results = []

    for term, meaning in ALGOSPEAK_DICT.items():
        term_lower = term.lower()
        count = text_lower.count(term_lower)

        if count > 0:
            results.append({
                'term': term,
                'meaning': meaning,
                'category': get_category(term),
                'count': count
            })

    return sorted(results, key=lambda x: x['count'], reverse=True)


# grabs surrounding text around each occurrence for qualitative analysis
def extract_algospeak_context(text: str, term: str, window: int = 60) -> list:
    """pulls out snippets of text around where the term appears so we can
    see how creators are actually using it in context. max 3 snippets."""
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

        if len(snippets) >= 3:
            break

    return snippets


# runs the full algospeak pipeline: detect, get context, summarise by category
def analyze_algospeak_usage(text: str) -> dict:
    """combines detection + context extraction + category summary into one result.
    returns total count, unique terms, per-term details, and category breakdown."""
    if not text:
        return {
            'total_algospeak_count': 0,
            'unique_terms': 0,
            'terms': [],
            'categories': {}
        }

    detected = detect_algospeak(text)

    for item in detected:
        item['contexts'] = extract_algospeak_context(text, item['term'])

    # tally up how many instances fall under each category
    category_counts = {}
    for item in detected:
        category = item['category']
        category_counts[category] = category_counts.get(category, 0) + item['count']

    return {
        'total_algospeak_count': sum(item['count'] for item in detected),
        'unique_terms': len(detected),
        'terms': detected,
        'categories': category_counts
    }
