# Algospeak Dictionary and Detection
# Maps common word substitutions used to evade content moderation

# Algospeak: Coded language that content creators use to avoid algorithmic 
# content moderation on platforms like YouTube, TikTok, and Instagram.


# Algospeak substitutions: algospeak_term -> original_meaning
# Organized by category for easier maintenance

ALGOSPEAK_DICT = {
    #   Violence & Death  
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
    
    #   Sexual Content  
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
    "accountant": "sex worker",  # TikTok specific
    "onlyfans": "OnlyFans",
    "only fans": "OnlyFans",
    "the hub": "PornHub",
    
    #   Profanity  
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
    
    #   Drugs & Substances  
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
    
    #   Mental Health  
    "le sad": "depression",
    "big sad": "depression",
    "the big D": "depression",
    "panic merchant": "anxiety",
    "spicy brain": "ADHD/mental illness",
    "grippy sock vacation": "psychiatric hospitalization",
    "grippy socks": "mental hospital",
    
    #   Political/Controversial  
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
    
    #   Violence-adjacent  
    "mascara": "gun (in some contexts)",
    "pew pew": "gun/shooting",
    "boom stick": "gun",
    "stabby": "knife",
    "ouch sword": "knife",
    "lead dispenser": "gun",
    "freedom seed dispenser": "gun",
    
    #   Platform-specific Terms  
    "cornfield": "banned (TikTok)",
    "naughty step": "content strike",
    "community guideline": "violation warning",
    "yellow dollar": "demonetized",
    "no money": "demonetized",
    "money gone": "demonetized",
    "ad unfriendly": "demonetized",
    
    # Slurs (Censored versions) 
    "n-word": "racial slur",
    "the n word": "racial slur",
    "f-slur": "homophobic slur",
    "r-word": "ableist slur",
    "r slur": "ableist slur",
}


# Categories for analysis
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

# Return a list of all algospeak terms available in the dictionary
def get_all_algospeak_terms() -> list:
    return list(ALGOSPEAK_DICT.keys())

# Look up the meaning of an algospeak term inside the dictionary
def get_algospeak_meaning(term: str) -> str:
    return ALGOSPEAK_DICT.get(term.lower())

# Determine which category a given algospeak term belongs to
def get_category(term: str) -> str:
    term_lower = term.lower()
    for category, terms in ALGOSPEAK_CATEGORIES.items():
        # Check if the term exists inside the current category list
        if term_lower in terms:
            return category
    # Default category if the term does not belong to any known category
    return "other"

# Detect algospeak terms within a body of text
def detect_algospeak(text: str) -> list:
    text_lower = text.lower()
    results = []
    
    # Iterate over the algospeak dictionary to check occurrences in text
    for term, meaning in ALGOSPEAK_DICT.items():
        term_lower = term.lower()
        count = text_lower.count(term_lower)
        
        # Add entry only if term appears at least once
        if count > 0:
            results.append({
                'term': term,
                'meaning': meaning,
                'category': get_category(term),
                'count': count
            })
    
    # Sort terms by frequency in descending order
    return sorted(results, key=lambda x: x['count'], reverse=True)

# Extract text snippets surrounding each occurrence of an algospeak term
def extract_algospeak_context(text: str, term: str, window: int = 60) -> list:
    snippets = []
    text_lower = text.lower()
    term_lower = term.lower()
    
    start = 0
    while True:
        # Find next position of the algospeak term
        pos = text_lower.find(term_lower, start)
        if pos == -1:
            break
        
        # Define the window around the matched term
        snippet_start = max(0, pos - window)
        snippet_end = min(len(text), pos + len(term) + window)
        
        # Extract snippet from original text (preserves case)
        snippet = text[snippet_start:snippet_end]
        
        # Add ellipses to indicate truncated sections
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(text):
            snippet = snippet + "..."
        
        # Remove line breaks and whitespace
        snippets.append(snippet.replace('\n', ' ').strip())
        start = pos + 1
        
        # Limit context snippets to a maximum of three
        if len(snippets) >= 3:
            break
    
    return snippets

# Perform full algospeak analysis including counts, categories, and contexts
def analyze_algospeak_usage(text: str) -> dict:
    # Handle empty input text gracefully
    if not text:
        return {
            'total_algospeak_count': 0,
            'unique_terms': 0,
            'terms': [],
            'categories': {}
        }
    
    # Detect all algospeak terms in the text
    detected = detect_algospeak(text)
    
    # Attach context snippets to each detected term
    for item in detected:
        item['contexts'] = extract_algospeak_context(text, item['term'])
    
    # Count occurrences grouped by category
    category_counts = {}
    for item in detected:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + item['count']
    
    # Return combined analysis results
    return {
        'total_algospeak_count': sum(item['count'] for item in detected),
        'unique_terms': len(detected),
        'terms': detected,
        'categories': category_counts
    }
