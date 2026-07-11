"""
VerifiLens - Chrome Extension Backend
FastAPI server that the Chrome extension talks to
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Create temp audio dir
Path(os.getenv("TEMP_AUDIO_DIR", "./temp_audio")).mkdir(parents=True, exist_ok=True)

from routers import health, analyze, factcheck, bias, transcribe
#import health, analyze, factcheck, bias, transcribe

app = FastAPI(
    title="VerifiLens API",
    description="Chrome Extension Backend - Real-time fact & bias checking for short videos",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - allow Chrome extension to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extensions use chrome-extension:// origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,     prefix="/api", tags=["Health"])
app.include_router(transcribe.router, prefix="/api", tags=["Transcription"])
app.include_router(factcheck.router,  prefix="/api", tags=["Fact Check"])
app.include_router(bias.router,       prefix="/api", tags=["Bias Detection"])
app.include_router(analyze.router,    prefix="/api", tags=["Full Analysis"])

@app.get("/")
def root():
    return {
        "app": "VerifiLens",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "extension": "Chrome Extension Backend"
    }

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  VerifiLens Backend Starting...")
    print("  API Docs: http://localhost:8000/docs")
    print("  Chrome Extension will connect here")
    print("="*50 + "\n")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
