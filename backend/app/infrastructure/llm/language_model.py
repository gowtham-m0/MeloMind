"""`LanguageModel` over LangChain chat models: the main model first, then the fallback."""

import asyncio
import logging
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

from app.core.errors import UpstreamError
from app.infrastructure.llm.factory import GEMINI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class LangChainLanguageModel:
    """Tries each model once, in order, and returns the first answer that fits the schema.

    Pass only the main model where a prompt must never reach the fallback (memory notes and a
    free Gemini key).
    """

    def __init__(
        self, models: Sequence[BaseChatModel], call_timeout: float = GEMINI_TIMEOUT_SECONDS
    ) -> None:
        if not models:
            raise ValueError("At least one chat model is needed.")
        self._models = tuple(models)
        self._call_timeout = call_timeout

    async def structured[SchemaT: BaseModel](
        self, system: str, prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        """The first valid structured answer. Raises `UpstreamError` when every model fails."""
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        for position, model in enumerate(self._models, start=1):
            try:
                answer = await asyncio.wait_for(
                    model.with_structured_output(schema).ainvoke(messages), self._call_timeout
                )
                return answer if isinstance(answer, schema) else schema.model_validate(answer)
            except (TimeoutError, ValidationError) as exc:
                logger.warning("LLM %d gave no usable answer: %s", position, type(exc).__name__)
            except Exception as exc:
                logger.warning("LLM %d failed: %s", position, type(exc).__name__)
        raise UpstreamError("The language model didn't give a usable answer.")
