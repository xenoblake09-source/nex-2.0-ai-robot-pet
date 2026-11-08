"""NEX — FastAPI backend for the NEX AI robot pet (Android).

Run locally:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .errors import NexError
from .gemini_client import health_snapshot
from .personality import ANIMALS, CREATOR_LINE, CREATORS
from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    SchoolAnswerResponse,
    SchoolAskRequest,
    VisionRequest,
    VisionResponse,
    WeatherResponse,
)
from .chat_service import handle_chat
from .school import school_knowledge
from .vision_service import describe_image
from .weather import get_weather

load_dotenv()

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
logger = logging.getLogger("nex")

settings = get_settings()
START_TIME = time.time()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Backend brain for NEX, the AI robot pet. Powered exclusively by Google Gemini.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NexError)
async def nex_error_handler(_request, exc: NexError):  # noqa: ANN001
    logger.warning("Handled error %s: %s", exc.code, exc.detail)
    return JSONResponse(status_code=exc.http_status, content=exc.to_payload())


@app.exception_handler(Exception)
async def unhandled_error_handler(_request, exc: Exception):  # noqa: ANN001
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "NEX had an internal hiccup. Please try again.",
                "detail": type(exc).__name__,
            }
        },
    )


# --------------------------------------------------------------------------
# System endpoints
# --------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Liveness + readiness probe (also used by Render)."""
    snapshot = health_snapshot()
    return HealthResponse(
        status="ok",
        version=settings.version,
        gemini_configured=snapshot["gemini_configured"],
        model=snapshot["model"],
        uptime_seconds=round(time.time() - START_TIME, 2),
    )


@app.get("/api/config", tags=["system"])
async def public_config() -> dict:
    """Public, non-secret configuration consumed by the Android app."""
    return {
        "app": settings.app_name,
        "version": settings.version,
        "model": settings.gemini_model,
        "model_chain": health_snapshot()["model_chain"],
        "gemini_configured": settings.gemini_configured,
        "creators": list(CREATORS),
        "creator_line": CREATOR_LINE,
        "animals": ANIMALS,
        "school_url": settings.school_url,
        "features": {
            "chat": True,
            "vision": True,
            "weather": settings.weather_enabled,
            "school": True,
            "animal_sounds": len(ANIMALS),
        },
    }


@app.get("/api/animals", tags=["system"])
async def animals() -> dict:
    """List of animal sounds NEX can perform."""
    return {"count": len(ANIMALS), "animals": ANIMALS}


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat(payload: ChatRequest) -> ChatResponse:
    """Main conversation endpoint. Returns the reply plus eye expression/action."""
    return await handle_chat(payload)


# --------------------------------------------------------------------------
# Vision
# --------------------------------------------------------------------------
@app.post("/api/vision", response_model=VisionResponse, tags=["vision"])
async def vision(payload: VisionRequest) -> VisionResponse:
    """Gemini Vision: describe what the camera is pointing at."""
    result = await describe_image(
        image_base64=payload.image_base64,
        mime_type=payload.mime_type,
        question=payload.question,
        language=payload.language,
    )
    return VisionResponse(
        reply=result["reply"],
        expression="curious",
        object_name=result.get("object_name"),
        face_present=result.get("face_present"),
        model=result.get("model"),
        latency_ms=result.get("latency_ms", 0),
        language=payload.language if payload.language != "auto" else "en",
    )


# --------------------------------------------------------------------------
# School knowledge
# --------------------------------------------------------------------------
@app.get("/api/school", tags=["school"])
async def school_snapshot() -> dict:
    """Status of the cached school website knowledge."""
    await school_knowledge.ensure_loaded()
    return school_knowledge.snapshot()


@app.post("/api/school/ask", response_model=SchoolAnswerResponse, tags=["school"])
async def school_ask(payload: SchoolAskRequest) -> SchoolAnswerResponse:
    """Ask a grounded question about Montfort Bagaha school."""
    from .gemini_client import generate
    from .personality import school_context_block

    started = time.perf_counter()
    await school_knowledge.ensure_loaded()
    facts = school_knowledge.context()
    prompt = (
        f"{school_context_block()}\n\n{facts}\n\n"
        "Answer the user's question in 1-2 short spoken sentences. "
        "If the facts do not contain the answer, say plainly that you do not have "
        "that information confirmed yet. Never invent details.\n\n"
        f"User question: {payload.question}"
    )
    text, model_used = await generate(
        prompt,
        system_instruction="You are NEX, a friendly robot pet. You speak briefly and warmly.",
        temperature=0.4,
        max_output_tokens=280,
        response_mime_type="text/plain",
        thinking_level="LOW",
    )
    grounded = school_knowledge.is_loaded
    return SchoolAnswerResponse(
        reply=text.strip(),
        grounded=grounded,
        source_url=settings.school_url if grounded else None,
        model=model_used,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


# --------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------
@app.get("/api/weather", response_model=WeatherResponse, tags=["fun"])
async def weather(city: str = Query(default="Patna", min_length=1, max_length=120)) -> WeatherResponse:
    """Live weather from Open-Meteo (no API key required)."""
    data = await get_weather(city)
    return WeatherResponse(**data)


# --------------------------------------------------------------------------
# Optional: serve the built frontend for quick browser previews
# --------------------------------------------------------------------------
_WEB_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")
if os.path.isdir(_WEB_DIST):
    app.mount("/app", StaticFiles(directory=_WEB_DIST, html=True), name="web")
    logger.info("Serving frontend build from %s at /app", _WEB_DIST)

    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        index = os.path.join(_WEB_DIST, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"error": {"code": "not_found", "message": "Not found"}}, status_code=404)


logger.info(
    "NEX backend ready | model=%s | gemini_configured=%s",
    settings.gemini_model,
    settings.gemini_configured,
)
