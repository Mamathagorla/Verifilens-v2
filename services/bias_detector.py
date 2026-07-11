"""
Bias & Manipulation Detection Service
Detects psychological manipulation patterns in video transcripts
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama3-70b-8192"

BIAS_PATTERNS = {
    "FOMO":            ["limited time", "don't miss", "last chance", "before it's too late", "everyone is doing", "act now", "hurry", "miss out", "running out", "closing soon"],
    "fear":            ["dangerous", "deadly", "lose everything", "they don't want you to know", "government hiding", "cover up", "toxic", "poisoning", "collapse", "bankrupt"],
    "hype":            ["guaranteed", "miracle", "revolutionary", "never seen before", "shocking", "incredible", "insane returns", "skyrocket", "breakthrough", "secret formula"],
    "false_authority": ["doctors don't want", "rbi approved", "sebi certified", "who recommended", "clinically proven", "studies show", "harvard says", "government approved"],
    "scarcity":        ["only available", "exclusive", "rare opportunity", "limited spots", "once in a lifetime", "today only", "flash sale", "invite only"],
    "conspiracy":      ["they don't want you", "hidden truth", "mainstream media", "fake news", "deep state", "elites", "suppressed", "banned information", "censored"]
}


def detect_keywords(transcript: str) -> dict:
    tl = transcript.lower()
    results = {}
    for bias_type, keywords in BIAS_PATTERNS.items():
        found = [k for k in keywords if k in tl]
        score = min(len(found) / 3, 1.0)
        results[bias_type] = {"score": round(score, 2), "examples": found[:3]}
    return results


def analyze_bias_with_llm(transcript: str, keyword_results: dict) -> dict:
    detected = {k: v for k, v in keyword_results.items() if v["score"] > 0.1}
    kw_summary = json.dumps(detected, indent=2) if detected else "None"

    prompt = f"""You are a media literacy expert. Analyze this transcript for psychological manipulation.

Transcript: {transcript[:2500]}

Keyword scan found: {kw_summary}

Respond ONLY with JSON:
{{
  "signals": [
    {{"type": "FOMO", "score": 0.85, "examples": ["phrase from transcript"]}},
    {{"type": "fear", "score": 0.6, "examples": ["fear phrase"]}}
  ],
  "overall_manipulation_score": 75,
  "risk_level": "HIGH",
  "flagged_phrases": ["phrase1", "phrase2", "phrase3"],
  "tone_analysis": "2-sentence plain English explanation of manipulation strategy"
}}

Only include signals with score > 0.1. risk_level: LOW/MEDIUM/HIGH."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=600
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
        return json.loads(raw)
    except Exception as e:
        print(f"[BiasDetector] LLM failed, using keywords: {e}")
        signals = [{"type": k, "score": v["score"], "examples": v["examples"]}
                   for k, v in keyword_results.items() if v["score"] > 0.05]
        overall = min(int(sum(s["score"] for s in signals) / max(len(signals), 1) * 100), 100)
        return {
            "signals": signals,
            "overall_manipulation_score": overall,
            "risk_level": "HIGH" if overall >= 60 else ("MEDIUM" if overall >= 30 else "LOW"),
            "flagged_phrases": [e for s in signals for e in s["examples"]][:5],
            "tone_analysis": f"Detected {len(signals)} manipulation pattern(s). Manual review recommended."
        }


def run_bias_analysis(transcript: str) -> dict:
    print("[BiasDetector] Keyword scan...")
    kw = detect_keywords(transcript)
    print("[BiasDetector] LLM deep analysis...")
    return analyze_bias_with_llm(transcript, kw)
