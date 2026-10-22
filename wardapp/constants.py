# Ward 119 Survey Constants

AREAS = [
    "అంజయ్య నగర్ & జయశంకర్ నగర్",
    "మనోవికాస్ నగర్, అబ్రార్ నగర్, షేర్ గల్లి, దుబాయ్ గేట్ లైన్, పంచశీల నగర్, సిండికేట్ బ్యాంక్ ఆఫీసర్స్ కాలనీ",
    "హరిజన బస్తీ",
    "యాదవ బస్తీ, యాదిరెడ్డి కాలనీ, అలీ కాంప్లెక్స్, కళ్యాణ్ థియేటర్, మల్లికార్జున కాలనీ, కుమ్మరి బస్తీ, ముస్లిం కాలనీ, హర్షవర్ధన్ కాలనీ, వార్డ్ ఆఫీస్ సర్కిల్, లాస్ట్ బస్ స్టాప్",
    "మాల బస్తీ",
    "వల్లభ్ నగర్ (హరిజన బస్తీ)",
    "మల్లికార్జున నగర్ రోడ్ 1, 2, 3",
    "భవాని నగర్",
    "సాయి విల్లాస్, టీచర్స్ కాలనీ, MSH డ్రీమ్ ఎస్టేట్స్ / షాదుల్లా హనుమంత్ నగర్",
    "ఇతర కాలనీ / Other",
]

CATEGORIES_AND_SUBCATEGORIES = {
    "Water Supply": [
        "Water for drinking",
        "Water for washing / daily use",
    ],
    "Drainage & Flooding": [
        "Drainage overflow",
        "Rainwater entering houses",
        "Open nala hazard",
    ],
    "Sanitation & Cleanliness": [
        "Cleaning of roads & silt removal",
        "Garbage & dump yards",
        "Mosquitoes & fogging",
        "Public toilets",
    ],
    "Roads & Electricity": [
        "Roads & potholes",
        "Streetlights",
        "Electric poles & hanging wires",
        "Speed breakers & traffic",
    ],
    "Health & Community": [
        "Parks & playgrounds",
        "Hospital & medicines",
        "Stray dogs",
    ],
    "Safety & Law/Order": [
        "Drugs & ganja nuisance",
        "Police patrolling & night safety",
        "Bribery & worker extortion",
    ],
    "Welfare & Schemes": [
        "Pensions (Widow / Old Age / Disability)",
        "Ration cards",
        "Double bedroom houses (2BHK)",
    ],
    "Local Leaders & Cadre": [
        "Leader behaviour with public",
    ],
}

CELL_FIELDS = [
    "where",
    "what",
    "why",
    "to_people",
    "how",
    "solution",
    "solution_impact",
    "voter_impact",
    "vote_plus",
    "vote_minus",
    "urgency",
    "scale",
    "dept_official",
    "influencer",
    "law_route",
    "work_done",
    "past_complaint",
]

FIELD_LABELS = {
    "where": "1. Where",
    "what": "2. What is happening",
    "why": "3. Why (root cause)",
    "to_people": "4. To people",
    "how": "5. How it happens",
    "solution": "6. Solution",
    "solution_impact": "7. Solution impact",
    "voter_impact": "8. Voter impact",
    "vote_plus": "9a. + done",
    "vote_minus": "9b. - not done",
    "urgency": "10. Urgency (1-5)",
    "scale": "11. Scale",
    "dept_official": "12. Dept / Official",
    "influencer": "13. Influencer",
    "law_route": "14. Law route",
    "work_done": "15. Work done?",
    "past_complaint": "16. Past complaint",
}

REVIEW_REASONS = [
    ("wrong_transcription", "Wrong Transcription"),
    ("wrong_category", "Wrong Category / Sub-category"),
    ("wrong_split", "Wrong Split (merged/split incorrectly)"),
    ("invented_fact", "Invented Fact (Hallucination)"),
    ("missing_info", "Missing Info (Spoken but skipped)"),
    ("wrong_vote", "Wrong Vote Sign/Number"),
    ("wrong_level", "Wrong Leader Level"),
    ("wrong_cause", "Wrong Root Cause Category"),
    ("other", "Other"),
]
