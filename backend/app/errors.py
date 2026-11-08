"""Typed application errors so the API can distinguish failure classes.

The Android client maps each error code to a different on-screen reaction,
so the categories below are part of the public contract.
"""
from __future__ import annotations


class NexError(Exception):
    """Base class for every error NEX reports to the client."""

    code = "nex_error"
    http_status = 500
    user_message = "Something went wrong inside NEX."

    def __init__(self, detail: str | None = None, *, user_message: str | None = None):
        self.detail = detail or self.user_message
        if user_message:
            self.user_message = user_message
        super().__init__(self.detail)

    def to_payload(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.user_message,
                "detail": self.detail,
            }
        }


class ConfigError(NexError):
    code = "config_error"
    http_status = 503
    user_message = "NEX's brain is not connected yet (GEMINI_API_KEY missing on the server)."


class GeminiError(NexError):
    code = "gemini_error"
    http_status = 502
    user_message = "NEX's brain (Gemini) could not answer right now."


class GeminiTimeoutError(GeminiError):
    code = "gemini_timeout"
    http_status = 504
    user_message = "Gemini took too long to answer. Please try again."


class GeminiSafetyError(GeminiError):
    code = "gemini_blocked"
    http_status = 422
    user_message = "Gemini could not answer that request."


class UpstreamError(NexError):
    code = "upstream_error"
    http_status = 502
    user_message = "NEX could not reach the internet service it needed."


class ValidationError(NexError):
    code = "validation_error"
    http_status = 422
    user_message = "That request was not valid."
