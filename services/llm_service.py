"""
Groq LLM Service - Claim extraction and domain classification
Only TEXT is sent to Groq - no audio/video ever leaves device
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


def classify_domain(transcript: str) -> str:
    prompt = f"""You are an expert content classifier for video transcripts. Classify into EXACTLY ONE domain from: finance, health, politics, climate, general.

Examples:
- "Invest in XYZ crypto for 500% returns" → finance
- "This herb cures diabetes in 3 days" → health  
- "Election fraud proven by new evidence" → politics
- "Global temps rise 3°C by 2030" → climate
- Casual chat, no specifics → general

Look for: finance (stocks/investments/ROI), health (cures/treatments/doctors), politics (govt/elections/policies), climate (weather disasters/CO2), else general.

Transcript: {transcript[:2000]}  # Increased chars for Shorts context

Respond ONLY with JSON: {{"domain": "finance", "confidence": 0.95}}"""

#Claude code
    '''
    prompt = f"""Classify this video transcript into ONE domain.
Domains: finance, health, politics, climate, general

Transcript: {transcript[:1500]}

Respond ONLY with JSON: {{"domain": "finance", "confidence": 0.95}}"""
'''


    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=80
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
        return json.loads(raw).get("domain", "general")
    except Exception:
        return "general"


def extract_claims(transcript: str, domain: str) -> list:
    domain_focus = {
        "finance": "investment returns, guarantees, fund names, approval claims, percentages",
        "health": "cures, remedies, timelines, medical claims, drug names",
        "politics": "policy changes, election claims, government decisions",
        "climate": "temperature statistics, disaster predictions, environmental claims",
        "general": "verifiable facts, statistics, named entities"
    }

    prompt = f"""Extract 2-5 specific verifiable factual claims from this {domain} transcript.
Focus on: {domain_focus.get(domain, domain_focus['general'])}
Only extract claims that can be TRUE or FALSE - not opinions.

Transcript: {transcript[:3000]}

Respond ONLY with JSON array:
[{{"id": 1, "text": "exact claim", "domain": "{domain}", "contains_numbers": true}}]"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2, max_tokens=800
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
        claims = json.loads(raw)
        if not claims or not isinstance(claims, list):
            print(f"[LLM] Empty claims fallback for domain {domain}")
            return [{"id": 1, "text": transcript[:300].strip(), "domain": domain, "contains_numbers": any(c.isdigit() for c in transcript[:300])}]
        return claims
    except Exception as e:
        print(f"[LLM] Claim extraction error: {e}")
        return []
    '''
#Perplexity code to find the dynamic score
def calculate_credibility_score(claims: list, domain: str) -> int:
    # Start neutral
    score = 50

    for claim in claims:
        text = (claim.get("text") or "").lower()
        verdict = (claim.get("verdict") or "").lower()
        has_numbers = claim.get("contains_numbers", False)

        # Positive signals
        if verdict in ["supported", "true"]:
            score += 20
        if has_numbers:
            score += 5
        if any(w in text for w in ["study", "research", "doctor", "official", "guideline"]):
            score += 10

        # Red flags / negatives
        if any(w in text for w in ["cure", "guarantee", "100%", "instantly", "overnight", "no risk"]):
            score -= 20
        if len(text.split()) < 5:
            score -= 5

    # Extra caution for some domains
    if domain == "health" and any("cure" in (c.get("text") or "").lower() for c in claims):
        score -= 10
    if domain == "finance" and any(w in (c.get("text") or "").lower() for c in claims for w in ["return", "%", "crore", "lakh"]):
        score -= 10

    # Clamp between 0 and 100
    return max(0, min(100, score))

'''

def generate_credibility_summary(claims: list, domain: str, score: int) -> str:
    if not claims:
        return "No specific verifiable claims found in this video."

    claims_text = "\n".join([f"- [{c.get('verdict','?').upper()}] {c.get('text','')}" for c in claims])
    prompt = f"""You are an assistant that ALWAYS responds in English, even if the input is in another language.

Write a 2-sentence summary of these {domain} fact-check results in clear, simple English.
Score: {score}/100. Be direct about what viewers should watch out for. No markdown.

Claims:
{claims_text}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"Credibility score: {score}/100. Review the claims carefully before acting on this content."
