"""The research agent's tools as LangChain tools. Arguments are validated by their schemas,
and every answer goes back to the agent as compact JSON: every call resends the history, and
the free LLM tiers count tokens a minute."""

import json
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from app.application.agent.tools.context import ToolContext, ToolRefusalError
from app.application.agent.tools.find_tags import find_tags
from app.application.agent.tools.get_insights import (
    SIGNALS_MAX,
    TAKE_MAX,
    TAKE_MIN,
    InsightsRequest,
    get_insights,
)
from app.application.agent.tools.search_entities import NAME_MAX, search_entities
from app.application.agent.tools.submit_candidates import WHY_MAX, submit_candidates
from app.domain.models import EntityType

PICKS_MAX = 40


class SearchEntitiesArgs(BaseModel):
    """Arguments for `search_entities`."""

    name: str = Field(
        max_length=NAME_MAX,
        description="An artist, film, TV show or book name. Never a song title or a lyric.",
    )
    type: EntityType | None = Field(
        default=None, description="artist, movie, tv_show or book. Leave out to search all."
    )


class FindTagsArgs(BaseModel):
    """Arguments for `find_tags`."""

    query: str = Field(max_length=60, description='A genre, region or decade, such as "Tamil".')


class GetInsightsArgs(BaseModel):
    """Arguments for `get_insights`."""

    type: EntityType = Field(description="artist, movie, tv_show or book")
    signal_ids: list[str] = Field(
        default_factory=list,
        max_length=SIGNALS_MAX,
        description="Entity or tag IDs from the brief or from your earlier tool results.",
    )
    year_min: int | None = Field(default=None, description="Films, TV and books only.")
    year_max: int | None = Field(default=None, description="Films, TV and books only.")
    country_code: str | None = Field(
        default=None, description="ISO 3166-1 alpha-2, such as US. Films and TV only."
    )
    popularity_min: float | None = Field(
        default=None, ge=0, le=1, description="A floor for popular picks, such as 0.7."
    )
    take: int = Field(default=12, ge=TAKE_MIN, le=TAKE_MAX)


class Pick(BaseModel):
    """One candidate the agent submits. The explain step writes the card reasons, so `why` is
    optional and short: a long answer is slow and costs tokens."""

    entity_id: str = Field(description="An id that get_insights returned in this run.")
    why: str = Field(default="", max_length=WHY_MAX, description="Optional, at most 8 words.")


class SubmitCandidatesArgs(BaseModel):
    """Arguments for `submit_candidates`."""

    candidates: list[Pick] = Field(max_length=PICKS_MAX)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def research_tools(ctx: ToolContext) -> list[BaseTool]:
    """The four tools the research agent may call, bound to this run's context."""

    async def search(name: str, type: EntityType | None = None) -> str:
        try:
            found = await search_entities(ctx, name, type)
        except ToolRefusalError as refusal:
            return refusal.message
        return _json(
            [
                {
                    "id": ctx.short(candidate.entity_id),
                    "name": candidate.name,
                    "type": candidate.entity_type.value,
                    "year": candidate.release_year,
                }
                for candidate in found
            ]
        )

    async def tags(query: str) -> str:
        try:
            found = await find_tags(ctx, query)
        except ToolRefusalError as refusal:
            return refusal.message
        return _json([{"id": ctx.short(tag.tag_id), "name": tag.name} for tag in found])

    async def insights(
        type: EntityType,
        signal_ids: list[str] | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        country_code: str | None = None,
        popularity_min: float | None = None,
        take: int = 12,
    ) -> str:
        given = tuple(signal_ids or ())
        ids = tuple(ctx.resolve(ref) for ref in given)
        ignored = [alias for alias, ref in zip(given, ids, strict=True) if ctx.name_of(ref) is None]
        request = InsightsRequest(
            entity_type=type,
            signal_ids=ids,
            year_min=year_min,
            year_max=year_max,
            country_code=country_code,
            popularity_min=popularity_min,
            take=take,
        )
        try:
            found = await get_insights(ctx, request)
        except ToolRefusalError as refusal:
            return refusal.message
        answer: dict[str, Any] = {
            "candidates": [
                {
                    "id": ctx.short(candidate.entity_id),
                    "name": candidate.name,
                    "year": candidate.release_year,
                    "affinity": round(candidate.affinity, 2) if candidate.affinity else None,
                }
                for candidate in found
            ]
        }
        if ignored:
            answer["ignored_unknown_ids"] = ignored
        return _json(answer)

    async def submit(candidates: list[Pick]) -> str:
        result = await submit_candidates(
            ctx, [(ctx.resolve(pick.entity_id), pick.why) for pick in candidates]
        )
        return _json(
            {
                "accepted": result.accepted,
                "total_submitted": result.total,
                "refused_unknown_ids": [ctx.short(ref) for ref in result.unknown_ids],
            }
        )

    return [
        StructuredTool.from_function(
            coroutine=search,
            name="search_entities",
            description="Find artists, films, TV shows or books by name. Returns ids and years.",
            args_schema=SearchEntitiesArgs,
        ),
        StructuredTool.from_function(
            coroutine=tags,
            name="find_tags",
            description="Find genre, region or decade tags to use as signals.",
            args_schema=FindTagsArgs,
        ),
        StructuredTool.from_function(
            coroutine=insights,
            name="get_insights",
            description=(
                "Recommendations of one type for some signals. The user's exclusions are always "
                "applied. Years work for films, TV and books; country for films and TV."
            ),
            args_schema=GetInsightsArgs,
        ),
        StructuredTool.from_function(
            coroutine=submit,
            name="submit_candidates",
            description=(
                "Your final answer, called once: your best picks from get_insights results, "
                "each with a short why."
            ),
            args_schema=SubmitCandidatesArgs,
            # The run ends here, so the agent never spends another model call after answering.
            return_direct=True,
        ),
    ]
