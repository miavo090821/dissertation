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