"""
Whisper transcription - runs 100% locally on AMD AI PC
No audio ever leaves the device
"""

import os
import whisper
import torch
from dotenv import load_dotenv

load_dotenv()

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")
_model = None


def get_device():
    if torch.cuda.is_available():
        print("[Whisper] Using CUDA GPU")
        return "cuda"
    print("[Whisper] Using CPU")
    return "cpu"


def load_model():
    global _model
    if _model is None:
        device = get_device()
        print(f"[Whisper] Loading '{WHISPER_MODEL_SIZE}' model...")
        _model = whisper.load_model(WHISPER_MODEL_SIZE, device=device)
        print(f"[Whisper] ✅ Model ready")
    return _model


def transcribe_audio(file_path: str) -> dict:
    """Transcribe audio to text locally using Whisper."""
    model = load_model()
    print(f"[Whisper] Transcribing: {file_path}")

    result = model.transcribe(
        file_path,
        task="transcribe",
        language=None,
        verbose=False,
        fp16=False,
        condition_on_previous_text=True,
        temperature=0.0,
    )

    transcript = result["text"].strip()
    language = result.get("language", "unknown")
    segments = result.get("segments", [])
    duration = segments[-1].get("end", 0.0) if segments else 0.0

    print(f"[Whisper] ✅ {len(transcript.split())} words, language: {language}")
    return {
        "transcript": transcript,
        "language": language,
        "duration_seconds": duration,
        "word_count": len(transcript.split()),
        "segments": segments
    }
