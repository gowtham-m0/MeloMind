"""Contract tests for GroqWhisperSpeechToText with httpx.MockTransport. No live calls."""

import httpx
import pytest

from app.core.errors import UpstreamError
from app.infrastructure.llm.whisper import GroqWhisperSpeechToText

pytestmark = pytest.mark.anyio

BASE_URL = "https://groq.test/openai/v1"


def speech(handler: httpx.MockTransport) -> GroqWhisperSpeechToText:
    client = httpx.AsyncClient(base_url=BASE_URL, transport=handler)
    return GroqWhisperSpeechToText(client, "test-key", "whisper-large-v3-turbo")


async def test_sends_the_recording_and_model_and_reads_text_and_duration() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"text": "  Rewatched Interstellar. ", "duration": 4.2})

    transcript = await speech(httpx.MockTransport(handle)).transcribe(
        b"audio-bytes", "entry.webm", "audio/webm"
    )

    assert transcript.text == "Rewatched Interstellar."
    assert transcript.duration_s == 4.2
    request = seen[0]
    assert request.url.path.endswith("/audio/transcriptions")
    assert request.headers["Authorization"] == "Bearer test-key"
    body = request.read()
    assert b"whisper-large-v3-turbo" in body and b"audio-bytes" in body and b"verbose_json" in body


@pytest.mark.parametrize("status", [400, 429, 500])
async def test_an_error_status_is_an_upstream_error(status: int) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json={}))

    with pytest.raises(UpstreamError):
        await speech(transport).transcribe(b"a", "entry.ogg", "audio/ogg")


async def test_a_network_failure_is_an_upstream_error() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow")

    with pytest.raises(UpstreamError):
        await speech(httpx.MockTransport(fail)).transcribe(b"a", "entry.wav", "audio/wav")
