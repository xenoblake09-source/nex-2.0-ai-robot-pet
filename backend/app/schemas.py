"""Pydantic request/response models for the NEX API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Expression = Literal[
    "neutral",
    "happy",
    "sad",
    "angry",
    "sleep",
    "blink",
    "dance",
    "surprised",
    "thinking",
    "listening",
    "speaking",
    "laugh",
    "cry",
    "love",
    "gaming",
    "curious",
    "confused",
    "excited",
]

ActionType = Literal[
    "none",
    "animal_sound",
    "dance",
    "tell_time",
    "tell_date",
    "joke",
    "riddle",
    "game",
    "weather",
    "school",
    "sleep",
    "wake",
]


class Turn(BaseModel):
    role: Literal["user", "nex"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="auto", max_length=32)
    history: list[Turn] = Field(default_factory=list)
    user_name: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=128)
    expression_hint: str | None = Field(default=None, max_length=32)
    local_time: str | None = Field(default=None, max_length=64)
    device_timezone: str | None = Field(default=None, max_length=64)


class Action(BaseModel):
    type: ActionType = "none"
    animal: str | None = None
    payload: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    reply: str
    expression: Expression = "neutral"
    action: Action = Action()
    language: str = "en"
    source: str = "gemini"
    model: str | None = None
    latency_ms: int = 0
    school_used: bool = False
    creator_intro: bool = False


class VisionRequest(BaseModel):
    image_base64: str = Field(min_length=16)
    mime_type: str = Field(default="image/jpeg", max_length=64)
    question: str = Field(default="What is this?", max_length=500)
    language: str = Field(default="auto", max_length=32)
    detect_face: bool = False


class VisionResponse(BaseModel):
    reply: str
    expression: Expression = "curious"
    object_name: str | None = None
    face_present: bool | None = None
    model: str | None = None
    latency_ms: int = 0
    language: str = "en"


class SchoolAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    language: str = Field(default="auto", max_length=32)


class SchoolAnswerResponse(BaseModel):
    reply: str
    grounded: bool = False
    source_url: str | None = None
    model: str | None = None
    latency_ms: int = 0


class WeatherRequest(BaseModel):
    city: str = Field(min_length=1, max_length=120)


class WeatherResponse(BaseModel):
    city: str
    temperature_c: float
    description: str
    humidity: int | None = None
    wind_kph: float | None = None
    source: str = "open-meteo"


class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_configured: bool
    model: str
    uptime_seconds: float


class ErrorPayload(BaseModel):
    code: str
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorPayload
