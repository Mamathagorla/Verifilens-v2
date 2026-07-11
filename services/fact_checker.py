"""
Fact Checking Service
Verifies claims against domain-specific trusted sources and rules
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
#MODEL = "llama3-70b-8192"
MODEL = "llama-3.3-70b-versatile"  # NEW - Recommended replacement

TRUSTED_SOURCES = {
    "finance": {"SEBI": "https://sebi.gov.in", "RBI": "https://rbi.org.in", "IRDAI": "https://irdai.gov.in"},
    "health":  {"WHO": "https://who.int", "ICMR": "https://icmr.gov.in", "NIH": "https://nih.gov", "CDC": "https://cdc.gov"},
    "politics":{"PIB": "https://pib.gov.in", "ECI": "https://eci.gov.in"},
    "climate": {"IPCC": "https://ipcc.ch", "NASA": "https://climate.nasa.gov"},
    "general": {"Snopes": "https://snopes.com", "FactCheck": "https://factcheck.org"}
}

DOMAIN_RULES = {
    "finance": [
        "No SEBI-registered product can legally 'guarantee' returns - this is illegal",
        "RBI does not approve or certify specific investment products",
        "Fixed deposits offer ~7-8% max; any 'guaranteed' higher return is a red flag",
        "Promises of 2x-3x returns in short periods are hallmarks of Ponzi schemes",
        "All mutual fund ads must include 'subject to market risk' by SEBI rules",
    ],
    "health": [
        "WHO: There is no cure for Type 1 diabetes; Type 2 is manageable, not curable",
        "No remedy can cure chronic diseases in days - this requires years of clinical trials",
        "ICMR requires peer-reviewed evidence for all health claims",
        "Cancer cannot be cured by diet or simple remedies alone",
        "Any 'cure in days' claim for chronic disease is medically false",
    ],
    "politics": [
        "Government policy changes must be officially gazetted",
        "PIB is the only official source for Indian government announcements",
        "Election results are certified exclusively by the Election Commission of India",
    ],
    "climate": [
        "97% of climate scientists agree on human-caused climate change (NASA/IPCC)",
        "Individual weather events cannot be directly attributed to climate change",
    ]
}


def verify_claim_with_llm(claim_text: str, domain: str) -> dict:
    rules = "\n".join([f"- {r}" for r in DOMAIN_RULES.get(domain, [])])
    sources = "\n".join([f"- {k}: {v}" for k, v in TRUSTED_SOURCES.get(domain, TRUSTED_SOURCES["general"]).items()])

    prompt = f"""You are a professional fact-checker for {domain} content in India.
     Always respond in English, even if the claim is in another language.
CLAIM: "{claim_text}"

VERIFIED FACTS:
{rules}

TRUSTED SOURCES:
{sources}

Using ONLY the facts and sources above, classify the claim.

Respond ONLY with JSON:
{{
  "verdict": "supported|misleading|unsupported|unverifiable",
  "confidence": 0.85,
  "explanation": "One clear sentence explaining the verdict",
  "sources": ["Source: URL"]
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=300
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
        result = json.loads(raw)
        if not isinstance(result.get("sources"), list):
            result["sources"] = list(TRUSTED_SOURCES.get(domain, TRUSTED_SOURCES["general"]).values())[:2]
        return result
    except Exception as e:
        print(f"[FactChecker] Error: {e}")
        return {
            "verdict": "unverifiable",
            "confidence": 0.3,
            "explanation": "Automated verification failed. Please check trusted sources manually.",
            "sources": list(TRUSTED_SOURCES.get(domain, TRUSTED_SOURCES["general"]).values())[:2]
        }


def calculate_credibility_score(verified_claims: list) -> int:
    
    """Simple scoring for demo:
    - supported → up
    - unsupported/misleading → down
    - all unverifiable → stay at 50
    """

    if not verified_claims:
        return 50
    
    #Perplexity code
    supported = sum(1 for c in verified_claims if c.get("verdict") == "supported")
    misleading = sum(1 for c in verified_claims if c.get("verdict") == "misleading")
    unsupported = sum(1 for c in verified_claims if c.get("verdict") == "unsupported")
    unverifiable = sum(1 for c in verified_claims if c.get("verdict") == "unverifiable")
    total = len(verified_claims)

    # Start neutral
    score = 50

    # Each supported claim adds points
    score += supported * 10

    # Each unsupported/misleading claim subtracts points
    score -= unsupported * 15
    score -= misleading * 10

    # If everything is unverifiable, stay neutral
    if unverifiable == total:
        score = 50

    # Clamp 0–100
    return max(0, min(100, score))


    '''
    weights = {"supported": 100, "misleading": 30, "unsupported": 0, "unverifiable": 50}
    total, weight_sum = 0, 0
    for c in verified_claims:
        conf = c.get("confidence", 0.5)
        w = 0.5 + conf * 0.5
        total += weights.get(c.get("verdict", "unverifiable"), 50) * w
        weight_sum += w
    return round(total / weight_sum) if weight_sum else 50
'''

def run_fact_check(claims: list, domain: str, transcript: str) -> dict:
    print(f"[FactChecker] Checking {len(claims)} claims in domain: {domain}")
    verified = []
    for i, claim in enumerate(claims):
        text = claim.get("text", "")
        if not text:
            continue
        print(f"[FactChecker] Claim {i+1}/{len(claims)}: {text[:60]}...")
        result = verify_claim_with_llm(text, domain)
        verified.append({
            "id": claim.get("id", i+1),
            "text": text,
            "verdict": result.get("verdict", "unverifiable"),
            "explanation": result.get("explanation", ""),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0.5),
            "domain": domain
        })

    return {
        "claims": verified,
        "domain": domain,
        "credibility_score": calculate_credibility_score(verified),
        "total_claims": len(verified),
        "supported_count": sum(1 for c in verified if c["verdict"] == "supported"),
        "misleading_count": sum(1 for c in verified if c["verdict"] == "misleading"),
        "unsupported_count": sum(1 for c in verified if c["verdict"] == "unsupported"),
    }
