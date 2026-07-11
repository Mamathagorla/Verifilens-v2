from fastapi import APIRouter, HTTPException
from models.schemas import FactCheckRequest, FactCheckResponse, Claim, ClaimVerdict
from services.llm_service import classify_domain, extract_claims, generate_credibility_summary
from services.fact_checker import run_fact_check

router = APIRouter()

@router.post("/factcheck", response_model=FactCheckResponse)
async def fact_check(request: FactCheckRequest):
    """Extract and verify claims from transcript text."""
    try:
        transcript = request.transcript.strip()
        if len(transcript) < 20:
            raise HTTPException(422, "Transcript too short")

        domain = request.domain or classify_domain(transcript)
        raw_claims = extract_claims(transcript, domain)

        if not raw_claims:
            return FactCheckResponse(
                claims=[], domain=domain, credibility_score=50,
                summary="No verifiable claims detected.",
                total_claims=0, supported_count=0, misleading_count=0, unsupported_count=0
            )

        result = run_fact_check(raw_claims, domain, transcript)
        summary = generate_credibility_summary(result["claims"], domain, result["credibility_score"])

        claims = [Claim(
            id=c["id"], text=c["text"], verdict=ClaimVerdict(c["verdict"]),
            explanation=c["explanation"], sources=c["sources"],
            confidence=c["confidence"], domain=c["domain"]
        ) for c in result["claims"]]

        return FactCheckResponse(
            claims=claims, domain=domain,
            credibility_score=result["credibility_score"],
            summary=summary,
            total_claims=result["total_claims"],
            supported_count=result["supported_count"],
            misleading_count=result["misleading_count"],
            unsupported_count=result["unsupported_count"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
