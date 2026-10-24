"""Test doubles: an inline background runner, a scripted chat model for the research agent,
and fakes for media, the language model and the taste graph. None of them touch the network."""

import asyncio
from collections.abc import Callable, Sequence
from typing import Any
from uuid import uuid4

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import BaseModel, PrivateAttr

from app.application.agent.log import RunLog
from app.application.agent.types import FeedContext, SignalRef
from app.application.ports import EntityMatch, InsightsQuery, PlayableMedia, TagMatch, TasteSource
from app.application.services.background import Job
from app.core.errors import UpstreamError
from app.domain.feedback import Blocklist, Exclusion
from app.domain.models import EntityType
from app.domain.runs import AgentRun, RunKind
from app.infrastructure.persistence.memory_runs import InMemoryAgentRunRepository


class InlineRunner:
    """Runs a background job straight away, so it has finished when `spawn` returns."""

    async def spawn(self, job: Job) -> None:
        await job()


def tool_call(name: str, call_id: str, **args: Any) -> ToolCall:
    """One tool call for a scripted turn."""
    return ToolCall(name=name, args=args, id=call_id, type="tool_call")


def turn(*calls: ToolCall, content: str = "") -> AIMessage:
    """One scripted model turn: some tool calls, or a final answer with none."""
    return AIMessage(content=content, tool_calls=list(calls))


class ScriptedChatModel(BaseChatModel):
    """Plays back predefined turns, one per model call, then ends with a plain answer.

    `fail_first` makes the first calls raise, like a model that times out, and `delay_s` slows
    every call from `delay_from` on.
    """

    script: list[AIMessage]
    fail_first: int = 0
    delay_s: float = 0.0
    delay_from: int = 0
    _calls: int = PrivateAttr(default=0)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    @property
    def calls(self) -> int:
        """How many times the model was called."""
        return self._calls

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ScriptedChatModel":  # type: ignore[override]
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        index = self._calls
        self._calls += 1
        if index < self.fail_first:
            raise TimeoutError("scripted model timeout")
        step = index - self.fail_first
        message = self.script[step] if step < len(self.script) else AIMessage(content="Done.")
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.delay_s and self._calls >= self.delay_from:
            await asyncio.sleep(self.delay_s)
        return self._generate(messages, stop, None, **kwargs)


class FakeMedia:
    """Media for every query except those containing a blocked word; records each query."""

    def __init__(self, unplayable: Sequence[str] = (), duration_s: int = 180) -> None:
        self.unplayable = [word.casefold() for word in unplayable]
        self.duration_s = duration_s
        self.queries: list[str] = []

    async def resolve(self, query: str) -> PlayableMedia | None:
        self.queries.append(query)
        if any(word in query.casefold() for word in self.unplayable):
            return None
        return PlayableMedia(
            video_id=f"vid-{len(self.queries)}", title=query, duration_s=self.duration_s
        )


class FakeLanguageModel:
    """Answers `structured` with whatever `answer` builds from the schema, or raises."""

    def __init__(self, answer: Callable[[type[BaseModel], str], BaseModel] | None = None) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def structured[SchemaT: BaseModel](
        self, system: str, prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        self.prompts.append(prompt)
        if self.answer is None:
            raise UpstreamError("The language model didn't give a usable answer.")
        result = self.answer(schema, prompt)
        assert isinstance(result, schema)
        return result


class RecordingTasteGraph:
    """Wraps a taste graph and records every insights query and search, for assertions."""

    def __init__(self, inner: Any, empty_searches: Sequence[str] = ()) -> None:
        self.inner = inner
        self.empty_searches = {name.casefold() for name in empty_searches}
        self.insights_queries: list[InsightsQuery] = []
        self.searches: list[str] = []

    @property
    def source(self) -> TasteSource:
        return self.inner.source

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        self.searches.append(query)
        if query.casefold() in self.empty_searches:
            return []
        return await self.inner.search(query, types, take)

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        self.insights_queries.append(query)
        return await self.inner.insights(query)

    async def tags(self, query: str, take: int = 5) -> list[TagMatch]:
        return await self.inner.tags(query, take)


class FailingTasteGraph:
    """Every call fails, like Qloo timing out."""

    @property
    def source(self) -> TasteSource:
        return "qloo_live"

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        raise UpstreamError("Qloo didn't respond.")

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        raise UpstreamError("Qloo didn't respond.")

    async def tags(self, query: str, take: int = 5) -> list[TagMatch]:
        raise UpstreamError("Qloo didn't respond.")


async def make_log() -> tuple[RunLog, InMemoryAgentRunRepository]:
    """A run log over an in-memory run, and the repository to read its steps back."""
    runs = InMemoryAgentRunRepository()
    run = AgentRun(profile_id=uuid4(), kind=RunKind.FEED)
    await runs.add(run)
    return RunLog(runs, run.id), runs


async def log_messages(runs: InMemoryAgentRunRepository, log: RunLog) -> list[str]:
    """Every message written to the run, in order."""
    run = await runs.get(log.run_id)
    assert run is not None
    return [step.message for step in run.steps]


def make_context(
    *,
    birth_year: int | None = 1958,
    favourites: Sequence[SignalRef] = (),
    learned: Sequence[SignalRef] = (),
    blocked: Sequence[Exclusion] = (),
    country_code: str | None = "US",
    song_titles: Sequence[str] = (),
    weights: dict[str, float] | None = None,
    previous_refs: frozenset[str] = frozenset(),
) -> FeedContext:
    """A feed context for tests, with sensible defaults (Leo, born 1958, US)."""
    return FeedContext(
        profile_id=uuid4(),
        first_name="Leo",
        birth_year=birth_year,
        country_code=country_code,
        favourite_signals=tuple(favourites),
        learned_signals=tuple(learned),
        text_favourites=(),
        song_titles=tuple(song_titles),
        blocklist=Blocklist.from_exclusions(blocked),
        learned_weights=weights or {},
        previous_refs=previous_refs,
    )


SUPREMES = SignalRef("demo-artist-the-supremes", "The Supremes", EntityType.ARTIST)
TEMPTATIONS = SignalRef("demo-artist-the-temptations", "The Temptations", EntityType.ARTIST)
SOUND_OF_MUSIC = SignalRef("demo-movie-the-sound-of-music", "The Sound of Music", EntityType.MOVIE)
MOCKINGBIRD = SignalRef("demo-book-to-kill-a-mockingbird", "To Kill a Mockingbird", EntityType.BOOK)
LEO_FAVOURITES = (SUPREMES, TEMPTATIONS, SOUND_OF_MUSIC, MOCKINGBIRD)
