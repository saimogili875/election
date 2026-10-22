import re
from typing import Dict, List, Set, Tuple

# Simple Telugu and English word tokenizer
WORD_RE = re.compile(r"[\w\u0C00-\u0C7F]+", re.UNICODE)

COMMON_FILLER_WORDS = {
    "మరియు", "కూడా", "కానీ", "లేదు", "ఉంది", "ఉన్నారు", "చేసి", "అని", "తో",
    "వల్ల", "కోసం", "లో", "పై", "దగ్గర", "ఇలా", "అలా", "ఇది", "అది", "ఆ", "ఈ",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "+", "and", "the", "in", "of", "to"
}

FIELD_KEYWORD_MAP = {
    "where": ["నగర్", "కాలనీ", "బస్తీ", "గల్లి", "రోడ్", "సర్కిల్", "స్టాప్", "గేట్", "లైన్", "బూత్"],
    "why": ["కారణం", "డబ్బు", "నిర్లక్ష్యం", "అవినీతి", "ఆలస్యం", "ఫెయిల్యూర్", "పట్టించుకో", "వదిలే"],
    "solution": ["పరిష్కారం", "చేయాలి", "చేస్తే", "మార్చాలి", "వేయాలి", "బాగు", "సరిచేయాలి"],
    "dept_official": ["GHMC", "కార్పొరేటర్", "ఆఫీసర్", "ఇన్స్పెక్టర్", "వాటర్ బోర్డ్", "పోలీస్", "ఎమ్మెల్యే", "ఎంపీ", "AE"],
    "past_complaint": ["ఫిర్యాదు", "కంప్లైంట్", "లెటర్", "చెప్పాం", "అడిగాం", "లెక్కచేయలేదు"],
    "urgency": ["ఎమర్జెన్సీ", "ప్రమాదం", "యాక్సిడెంట్", "వెంటనే", "భయం", "రోజు"],
    "to_people": ["డబ్బులు డిమాండ్", "బూతులు", "కోపం", "బెదిరింపులు", "భయం", "ప్రజలు"],
    "how": ["మొదట", "తర్వాత", "చేస్తారు", "1", "2", "3"],
    "voter_impact": ["ఓట్లు", "ఓటు", "ప్రజల అభిప్రాయం", "కోపం", "వ్యతిరేకం", "మద్దతు"],
}

def extract_tokens(text: str) -> List[str]:
    """Tokenize text into lowercase words/tokens."""
    if not text:
        return []
    return [t.lower() for t in WORD_RE.findall(text)]

def check_invented_words(cell_value: str, transcript: str) -> Tuple[bool, List[str]]:
    """
    Checks if words in cell_value appear to be invented (not present in transcript).
    Returns (is_invented, list_of_missing_words).
    """
    if not cell_value or not cell_value.strip():
        return False, []
    
    transcript_tokens = set(extract_tokens(transcript))
    cell_tokens = extract_tokens(cell_value)
    
    missing_tokens = []
    for token in cell_tokens:
        if len(token) <= 2:
            continue
        if token in COMMON_FILLER_WORDS:
            continue
        # Check direct token match or substring match in transcript
        if token not in transcript_tokens and token not in transcript.lower():
            missing_tokens.append(token)
            
    # If more than 2 significant words or >30% of significant words are missing from transcript
    significant_tokens = [t for t in cell_tokens if len(t) > 2 and t not in COMMON_FILLER_WORDS]
    if not significant_tokens:
        return False, []
    
    is_invented = len(missing_tokens) >= 2 or (len(missing_tokens) / len(significant_tokens) >= 0.4)
    return is_invented, missing_tokens

def check_missing_info(field_name: str, cell_value: str, transcript: str) -> bool:
    """
    Checks if a field is empty, but the transcript seems to contain relevant keywords.
    """
    if cell_value and cell_value.strip():
        return False
    
    keywords = FIELD_KEYWORD_MAP.get(field_name, [])
    if not keywords or not transcript:
        return False
    
    lower_transcript = transcript.lower()
    for kw in keywords:
        if kw.lower() in lower_transcript:
            return True
    return False

def validate_cell(field_name: str, cell_value: str, transcript: str) -> Dict[str, any]:
    """
    Returns validation status for a cell:
    {
       'highlight': 'red' | 'yellow' | 'none',
       'reason': str,
       'details': list
    }
    """
    is_invented, missing_words = check_invented_words(cell_value, transcript)
    if is_invented:
        return {
            'highlight': 'red',
            'reason': 'Possible invented facts (words not found in transcript)',
            'details': missing_words,
        }
        
    if check_missing_info(field_name, cell_value, transcript):
        return {
            'highlight': 'yellow',
            'reason': 'Field is empty but transcript contains relevant keywords',
            'details': [],
        }
        
    return {
        'highlight': 'none',
        'reason': '',
        'details': [],
    }
