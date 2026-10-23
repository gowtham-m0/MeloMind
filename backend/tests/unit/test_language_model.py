"""Tests for the LLM adapter: structured output, the fallback model, and failing cleanly."""

import pytest
from pydantic import BaseModel

from app.core.errors import UpstreamError
from app.infrastructure.llm.factory import build_chat_model
from app.infrastructure.llm.language_model import LangChainLanguageModel
from tests.fakes import ScriptedChatModel, tool_call, turn

pytestmark = pytest.mark.anyio


class Answer(BaseModel):
    text: str


def answering(text: str) -> ScriptedChatModel:
    return ScriptedChatModel(script=[turn(tool_call("Answer", "1", text=text))])


async def test_the_main_model_answers_in_the_schema() -> None:
    model = LangChainLanguageModel([answering("from groq"), answering("from gemini")])

    answer = await model.structured("system", "prompt", Answer)

    assert answer == Answer(text="from groq")


async def test_a_failing_main_model_falls_back_once() -> None:
    primary = ScriptedChatModel(script=[], fail_first=1)
    fallback = answering("from gemini")

    answer = await LangChainLanguageModel([primary, fallback]).structured("s", "p", Answer)

    assert answer.text == "from gemini"
    assert (primary.calls, fallback.calls) == (1, 1)


async def test_invalid_output_counts_as_a_failure() -> None:
    invalid = ScriptedChatModel(script=[turn(tool_call("Answer", "1", wrong="field"))])

    with pytest.raises(UpstreamError):
        await LangChainLanguageModel([invalid]).structured("s", "p", Answer)


async def test_a_slow_model_times_out() -> None:
    slow = ScriptedChatModel(script=[turn(tool_call("Answer", "1", text="late"))], delay_s=1)

    with pytest.raises(UpstreamError):
        await LangChainLanguageModel([slow], call_timeout=0.05).structured("s", "p", Answer)


def test_the_factory_knows_groq_and_gemini_only() -> None:
    assert type(build_chat_model("groq", "openai/gpt-oss-120b", "key")).__name__ == "ChatGroq"
    assert type(build_chat_model("Gemini", "gemini-3.8-flash", "key")).__name__ == (
        "ChatGoogleGenerativeAI"
    )
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_chat_model("other", "model", "key")
