from pydantic import BaseModel
from typing import List, Optional, Literal
from enum import Enum


class VideoRequest(BaseModel):
    url: str
    platform: Optional[str] = "auto"


class TranscriptResponse(BaseModel):
    transcript: str
    language: str
    duration_seconds: float
    word_count: int
    platform_detected: str


class ClaimVerdict(str, Enum):
    SUPPORTED = "supported"
    MISLEADING = "misleading"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"


class Claim(BaseModel):
    id: int
    text: str
    verdict: ClaimVerdict
    explanation: str
    sources: List[str]
    confidence: float
    domain: str


class FactCheckRequest(BaseModel):
    transcript: str
    domain: Optional[str] = None


class FactCheckResponse(BaseModel):
    claims: List[Claim]
    domain: str
    credibility_score: int
    summary: str
    total_claims: int
    supported_count: int
    misleading_count: int
    unsupported_count: int


class BiasSignal(BaseModel):
    type: str
    score: float
    examples: List[str]


class BiasRequest(BaseModel):
    transcript: str


class BiasResponse(BaseModel):
    overall_manipulation_score: int
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    signals: List[BiasSignal]
    tone_analysis: str
    flagged_phrases: List[str]


class FullAnalysisResponse(BaseModel):
    transcript: TranscriptResponse
    fact_check: FactCheckResponse
    bias: BiasResponse
    processing_time_seconds: float
