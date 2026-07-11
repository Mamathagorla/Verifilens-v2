from fastapi import APIRouter
import torch, os

router = APIRouter()

@router.get("/health")
def health():
    key = os.getenv("GROQ_API_KEY", "")
    return {
        "status": "ok",
        "groq_configured": bool(key and key != "your_groq_api_key_here"),
        "cuda_available": torch.cuda.is_available(),
        "whisper_model": os.getenv("WHISPER_MODEL", "base"),
        "amd_on_device": True,
        "audio_stays_local": True
    }
