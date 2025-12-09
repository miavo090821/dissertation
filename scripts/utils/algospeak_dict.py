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


def get_all_algospeak_terms() -> list:
    # Get all algospeak terms as a list.
    # Returns:
    #     List of all algospeak terms
    return list(ALGOSPEAK_DICT.keys())


def get_algospeak_meaning(term: str) -> str:
    # Get the original meaning of an algospeak term.
    # Args:
    #     term: Algospeak term to look up
    # Returns:
    #     Original meaning or None if not found
    
    return ALGOSPEAK_DICT.get(term.lower())


def get_category(term: str) -> str:
    """
    Get the category of an algospeak term.
    
    Args:
        term: Algospeak term
        
    Returns:
        Category name or "other"
    """
    term_lower = term.lower()
    for category, terms in ALGOSPEAK_CATEGORIES.items():
        if term_lower in terms:
            return category
    return "other"


def detect_algospeak(text: str) -> list:
    # Detect algospeak terms in text.
    
    # Args:
    #     text: Text to analyze
        
    # Returns:
    #     List of dictionaries containing:
    #     - term: The algospeak term found
    #     - meaning: What it represents
    #     - category: Category of the term
    #     - count: Number of occurrences

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
    
    # Sort by count descending
    return sorted(results, key=lambda x: x['count'], reverse=True)


def analyze_algospeak_usage(text: str) -> dict:
    """
    Comprehensive algospeak analysis of text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary containing:
        - total_algospeak_count: Total algospeak instances
        - unique_terms: Number of unique terms found
        - terms: List of term details with contexts
        - categories: Breakdown by category
    """
    if not text:
        return {
            'total_algospeak_count': 0,
            'unique_terms': 0,
            'terms': [],
            'categories': {}
        }
    
    detected = detect_algospeak(text)
    
    # Add context to each term
    for item in detected:
        item['contexts'] = extract_algospeak_context(text, item['term'])
    
    # Category breakdown
    category_counts = {}
    for item in detected:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + item['count']
    
    return {
        'total_algospeak_count': sum(item['count'] for item in detected),
        'unique_terms': len(detected),
        'terms': detected,
        'categories': category_counts
    }

