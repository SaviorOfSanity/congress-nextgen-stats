"""
Legislative Vote Categorization and Policy Stance Classifier
"""
import re
from typing import Dict, List, Tuple
from backend.config import POLICY_CATEGORIES

# Keyword mappings for legislative topics
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Economy & Taxation": [
        "tax", "taxes", "taxation", "budget", "debt ceiling", "inflation", "tariff", "trade", 
        "appropriations", "treasury", "revenue", "irs", "spending", "deficit", "commerce", "small business"
    ],
    "Defense & National Security": [
        "defense", "national defense", "ndaa", "military", "armed forces", "pentagon", "army", "navy", 
        "air force", "marines", "intelligence", "surveillance", "foreign aid", "ukraine", "israel", "taiwan", "nato"
    ],
    "Healthcare & Medicare": [
        "health", "healthcare", "medicare", "medicaid", "prescription", "fda", "drug prices", 
        "affordable care", "aca", "hospitals", "mental health", "biomedical", "nih", "public health"
    ],
    "Energy & Environment": [
        "energy", "climate", "carbon", "clean energy", "oil", "gas", "drilling", "epa", "emissions", 
        "renewables", "solar", "wind", "nuclear", "conservation", "water", "pollution", "pipeline"
    ],
    "Technology & AI / Privacy": [
        "technology", "artificial intelligence", "ai", "tech", "semiconductor", "chips", "broadband", 
        "cybersecurity", "privacy", "data privacy", "fcc", "ftc", "telecom", "crypto", "digital"
    ],
    "Immigration & Border Security": [
        "immigration", "border", "border security", "customs", "asylum", "visa", "deportation", 
        "homeland security", "patrol", "citizenship", "daca", "alien", "migrant"
    ],
    "Agriculture & Rural Development": [
        "agriculture", "farm", "farm bill", "crop", "rural", "usda", "livestock", "food stamps", 
        "snap", "nutrition", "commodity", "forestry"
    ],
    "Infrastructure & Transportation": [
        "infrastructure", "transportation", "highway", "transit", "bridges", "roads", "rail", 
        "amtrak", "faa", "aviation", "ports", "broadband infrastructure", "waterways"
    ],
    "Education & Labor": [
        "education", "student loans", "teachers", "schools", "higher education", "labor", 
        "unions", "workforce", "minimum wage", "nlrb", "osha", "pension"
    ],
    "Judiciary & Civil Rights": [
        "judiciary", "court", "judge", "supreme court", "civil rights", "voting rights", 
        "constitution", "firearms", "gun", "second amendment", "abortion", "criminal justice", "police"
    ],
    "Foreign Affairs & Trade": [
        "foreign affairs", "treaty", "state department", "diplomacy", "sanctions", "china", 
        "russia", "iran", "embassy", "international", "export", "import"
    ],
    "Government Ethics & Spending": [
        "ethics", "oversight", "transparency", "lobbying", "campaign finance", "impeachment", 
        "subpoena", "government reform", "fisa", "inspector general", "accountability"
    ]
}

# Landmark roll call votes mapped for instant accuracy
LANDMARK_VOTES = [
    {
        "roll_call_id": "H-118-2-340",
        "bill_number": "H.R. 8035",
        "bill_title": "Ukraine Security Supplemental Appropriations Act",
        "category": "Defense & National Security",
        "date": "2024-04-20",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-2-120",
        "bill_number": "H.R. 7521",
        "bill_title": "Protecting Americans from Foreign Adversary Controlled Applications Act (TikTok Bill)",
        "category": "Technology & AI / Privacy",
        "date": "2024-03-13",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-1-249",
        "bill_number": "H.R. 3746",
        "bill_title": "Fiscal Responsibility Act of 2023 (Debt Ceiling Deal)",
        "category": "Economy & Taxation",
        "date": "2023-05-31",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-1-209",
        "bill_number": "H.R. 2",
        "bill_title": "Secure the Border Act of 2023",
        "category": "Immigration & Border Security",
        "date": "2023-05-11",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-1-182",
        "bill_number": "H.R. 1",
        "bill_title": "Lower Energy Costs Act",
        "category": "Energy & Environment",
        "date": "2023-03-30",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-2-150",
        "bill_number": "H.R. 3935",
        "bill_title": "FAA Reauthorization Act of 2024",
        "category": "Infrastructure & Transportation",
        "date": "2024-05-15",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-2-290",
        "bill_number": "H.R. 8070",
        "bill_title": "National Defense Authorization Act for Fiscal Year 2025",
        "category": "Defense & National Security",
        "date": "2024-06-14",
        "result": "PASSED"
    },
    {
        "roll_call_id": "H-118-1-400",
        "bill_number": "H.R. 5860",
        "bill_title": "Continuing Appropriations Act, 2024 (Stopgap Funding)",
        "category": "Economy & Taxation",
        "date": "2023-09-30",
        "result": "PASSED"
    }
]

def classify_vote(title: str, description: str = "", bill_type: str = "") -> str:
    """
    Classify a bill or roll call vote into one of the 12 core policy categories.
    """
    combined_text = f"{title} {description} {bill_type}".lower()
    
    # Check for direct matches in landmark votes
    for lv in LANDMARK_VOTES:
        if lv["bill_title"].lower() in combined_text or (lv.get("bill_number") and lv["bill_number"].lower() in combined_text):
            return lv["category"]
            
    # Calculate scores for each category
    scores: Dict[str, int] = {cat: 0 for cat in POLICY_CATEGORIES}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            # Word boundary regex search
            matches = len(re.findall(r'\b' + re.escape(kw) + r'\b', combined_text))
            scores[category] += matches * (3 if len(kw) > 5 else 1)
            
    # Return highest scoring category, fallback to Economy & Taxation if tied at 0
    best_cat = max(scores, key=lambda k: scores[k])
    if scores[best_cat] == 0:
        return "Government Ethics & Spending"
    return best_cat
