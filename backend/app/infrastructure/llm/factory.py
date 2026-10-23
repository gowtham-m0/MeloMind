"""Builds a LangChain chat model for a provider name. Only `api/deps.py` decides which to build."""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import SecretStr

# A Groq call gives up after 8 seconds, so it can still be retried once on Gemini. Gemini's API
# refuses deadlines under 10 seconds, and it thinks before answering, so it gets 15.
LLM_CALL_TIMEOUT_SECONDS = 8.0
GEMINI_TIMEOUT_SECONDS = 15.0
# Low, so planning and composing stay steady from run to run.
LLM_TEMPERATURE = 0.2
# Little hidden reasoning: answers come faster and use fewer of the free tier's tokens a minute.
REASONING_EFFORT = "low"

PROVIDERS = ("groq", "gemini")


def build_chat_model(
    provider: str,
    model: str,
    api_key: str,
    *,
    timeout: float | None = None,
    temperature: float = LLM_TEMPERATURE,
) -> BaseChatModel:
    """A chat model for `groq` or `gemini`, with no retries of its own (fallback handles that).
    `timeout` defaults to 8 seconds for Groq and 15 for Gemini."""
    name = provider.strip().lower()
    if name == "groq":
        return ChatGroq(
            model=model,
            api_key=SecretStr(api_key),
            timeout=timeout or LLM_CALL_TIMEOUT_SECONDS,
            max_retries=0,
            temperature=temperature,
            reasoning_effort=REASONING_EFFORT,
        )
    if name == "gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=SecretStr(api_key),
            request_timeout=max(timeout or GEMINI_TIMEOUT_SECONDS, GEMINI_TIMEOUT_SECONDS),
            max_retries=0,
            temperature=temperature,
            reasoning_effort=REASONING_EFFORT,
        )
    raise ValueError(f"Unknown LLM provider {provider!r}. Use one of: {', '.join(PROVIDERS)}.")
