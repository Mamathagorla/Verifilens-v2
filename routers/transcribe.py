from fastapi import APIRouter, HTTPException
from models.schemas import VideoRequest, TranscriptResponse
from services.audio_extractor import extract_audio, cleanup_audio
from services.transcriber import transcribe_audio

router = APIRouter()

@router.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_video(request: VideoRequest):
    """Download & transcribe video audio locally using Whisper."""
    audio_file = None
    try:
        audio_result = await extract_audio(request.url)
        audio_file = audio_result["file_path"]
        result = transcribe_audio(audio_file)
        if not result["transcript"]:
            raise HTTPException(422, "No speech detected")
        return TranscriptResponse(
            transcript=result["transcript"],
            language=result["language"],
            duration_seconds=result["duration_seconds"],
            word_count=result["word_count"],
            platform_detected=audio_result["platform"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        if audio_file:
            cleanup_audio(audio_file)
