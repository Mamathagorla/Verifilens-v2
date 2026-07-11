"""
Full Analysis Pipeline - Main endpoint called by Chrome Extension
POST /api/analyze with {url, platform}
Returns complete fact-check + bias analysis
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import time

from models.schemas import (FullAnalysisResponse, TranscriptResponse,
    FactCheckResponse, BiasResponse, Claim, ClaimVerdict, BiasSignal)
from services.audio_extractor import extract_audio, cleanup_audio
from services.transcriber import transcribe_audio
from services.llm_service import classify_domain, extract_claims, generate_credibility_summary
#from services.llm_service import classify_domain, extract_claims, generate_credibility_summary,calculate_credibility_score
from services.fact_checker import run_fact_check
from services.bias_detector import run_bias_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    url: str
    platform: Optional[str] = "auto"


@router.post("/analyze", response_model=FullAnalysisResponse)
async def full_analysis(request: AnalyzeRequest):
    """
    🔍 MAIN ENDPOINT - Called by Chrome Extension
    Provide video URL → get complete fact-check + bias report
    AMD AI: audio processed locally, only text sent to cloud
    """
    start = time.time()
    audio_file = None

    try:
        print(f"\n{'='*55}")
        print(f"[Pipeline] 🚀 Chrome Extension request: {request.url[:60]}")

        # Step 1: Download audio locally
        audio_result = await extract_audio(request.url)
        audio_file = audio_result["file_path"]
        platform = audio_result["platform"]

        # Step 2: Transcribe on-device (Whisper)
        print("[Pipeline] 🎙️ Transcribing locally...")
        tr = transcribe_audio(audio_file)
        transcript_text = tr["transcript"]

        # Clean up audio immediately - we only need text now
        cleanup_audio(audio_file)
        audio_file = None

        if not transcript_text:
            raise HTTPException(422, "No speech detected in video")

        # Step 3: Domain classification
        print("[Pipeline] 🏷️ Classifying domain...")
        domain = classify_domain(transcript_text)

        # Step 4: Extract claims
        print("[Pipeline] 🧠 Extracting claims...")
        raw_claims = extract_claims(transcript_text, domain)

        # Step 5: Fact check
        print("[Pipeline] ✅ Fact checking...")
        if raw_claims:
            fc_result = run_fact_check(raw_claims, domain, transcript_text)
            #from services.llm_service import calculate_credibility_score
            #fc_result["credibility_score"] = calculate_credibility_score(fc_result["claims"], domain)
        else:
            fc_result = {"claims": [], "domain": domain, "credibility_score": 50,
                        "total_claims": 0, "supported_count": 0, "misleading_count": 0, "unsupported_count": 0}

        # Step 6: Bias analysis
        print("[Pipeline] 👁️ Bias detection...")
        bias_result = run_bias_analysis(transcript_text)

        # Step 7: Summary
        summary = generate_credibility_summary(fc_result["claims"], domain, fc_result["credibility_score"])

        elapsed = round(time.time() - start, 2)
        print(f"[Pipeline] ✅ Done in {elapsed}s")

        # Build response
        claims = [Claim(
            id=c["id"], text=c["text"], verdict=ClaimVerdict(c["verdict"]),
            explanation=c["explanation"], sources=c["sources"],
            confidence=c["confidence"], domain=c["domain"]
        ) for c in fc_result["claims"]]

        bias_signals = [BiasSignal(type=s["type"], score=s["score"], examples=s.get("examples", []))
                       for s in bias_result.get("signals", [])]

        return FullAnalysisResponse(
            transcript=TranscriptResponse(
                transcript=transcript_text, language=tr["language"],
                duration_seconds=tr["duration_seconds"], word_count=tr["word_count"],
                platform_detected=platform
            ),
            fact_check=FactCheckResponse(
                claims=claims, domain=domain,
                credibility_score=fc_result["credibility_score"],
                summary=summary,
                total_claims=fc_result["total_claims"],
                supported_count=fc_result["supported_count"],
                misleading_count=fc_result["misleading_count"],
                unsupported_count=fc_result["unsupported_count"]
            ),
            bias=BiasResponse(
                overall_manipulation_score=bias_result.get("overall_manipulation_score", 0),
                risk_level=bias_result.get("risk_level", "LOW"),
                signals=bias_signals,
                tone_analysis=bias_result.get("tone_analysis", ""),
                flagged_phrases=bias_result.get("flagged_phrases", [])
            ),
            processing_time_seconds=elapsed
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("=== PIPELINE ERROR TRACEBACK ===")
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        if audio_file:
            cleanup_audio(audio_file)
