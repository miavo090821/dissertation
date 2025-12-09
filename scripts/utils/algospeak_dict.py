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

def get_category(term: str) -> str:
    # Get the category of an algospeak term.
    
    # Args:
    #     term: Algospeak term
        
    # Returns:
    #     Category name or "other"
    
    term_lower = term.lower()
    for category, terms in ALGOSPEAK_CATEGORIES.items():
        if term_lower in terms:
            return category
    return "other"

def analyze_algospeak_usage(text: str) -> dict:
    # Analyze text for algospeak usage.
    
    # Args:
    #     text: Input text to analyze
        
    # Returns:
    #     Dictionary with counts of algospeak terms by category
    
    usage_counts = {category: 0 for category in ALGOSPEAK_CATEGORIES.keys()}
    usage_counts["other"] = 0
    
    # Normalize text to lowercase for matching
    text_lower = text.lower()
    
    for term in ALGOSPEAK_DICT.keys():
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        matches = re.findall(pattern, text_lower)
        if matches:
            category = get_category(term)
            usage_counts[category] += len(matches)
    
    return usage_counts