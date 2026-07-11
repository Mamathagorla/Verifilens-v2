from fastapi import APIRouter, HTTPException
from models.schemas import BiasRequest, BiasResponse, BiasSignal
from services.bias_detector import run_bias_analysis

router = APIRouter()

@router.post("/bias", response_model=BiasResponse)
async def detect_bias(request: BiasRequest):
    """Detect manipulation patterns in transcript."""
    try:
        if len(request.transcript.strip()) < 10:
            raise HTTPException(422, "Transcript too short")
        result = run_bias_analysis(request.transcript)
        signals = [BiasSignal(type=s["type"], score=s["score"], examples=s.get("examples", []))
                   for s in result.get("signals", [])]
        return BiasResponse(
            overall_manipulation_score=result.get("overall_manipulation_score", 0),
            risk_level=result.get("risk_level", "LOW"),
            signals=signals,
            tone_analysis=result.get("tone_analysis", ""),
            flagged_phrases=result.get("flagged_phrases", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
