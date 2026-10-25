"""`SpeechToText` over Groq Whisper. The recording goes to Groq once and is never written to
disk or logged (rule 11)."""

import logging

import httpx

from app.application.ports import Transcript
from app.core.errors import UpstreamError

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
WHISPER_TIMEOUT_SECONDS = 30.0


class GroqWhisperSpeechToText:
    """Transcribes one recording with Groq's Whisper model, using the Groq key."""

    def __init__(self, client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model

    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> Transcript:
        """The words in the recording. `verbose_json` also gives its length."""
        try:
            response = await self._client.post(
                "/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (filename, audio, content_type)},
                data={"model": self._model, "response_format": "verbose_json"},
            )
        except httpx.HTTPError as exc:
            logger.warning("Transcription failed: %s", type(exc).__name__)
            raise UpstreamError("Couldn't transcribe the recording.") from None
        if response.status_code != httpx.codes.OK:
            logger.warning("Transcription failed with status %d", response.status_code)
            raise UpstreamError("Couldn't transcribe the recording.")
        try:
            body = response.json()
            text = str(body.get("text", "")).strip()
            duration = body.get("duration")
        except (ValueError, AttributeError):
            raise UpstreamError("Couldn't transcribe the recording.") from None
        return Transcript(
            text=text, duration_s=float(duration) if isinstance(duration, int | float) else None
        )
