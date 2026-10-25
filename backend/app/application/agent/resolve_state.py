"""What the resolve_favourite and link_journal workflows pass between their nodes, and what
their nodes depend on. The builders inject the ports, so nodes never import an adapter."""

from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from app.application.agent.ladder import Hints, Proposal
from app.application.agent.log import RunLog
from app.application.ports import JournalRepository, LanguageModel, TasteGraph
from app.domain.feedback import Blocklist
from app.domain.journal import JournalNode
from app.domain.models import FavouriteKind


@dataclass(frozen=True)
class ResolveDeps:
    """One resolve run's ports, log and search budget."""

    taste: TasteGraph
    log: RunLog
    profile_id: UUID
    blocklist: Blocklist
    max_searches: int
    language_model: LanguageModel | None = None


class ResolveState(TypedDict, total=False):
    """Written by: `text`, `kind`, `hint` (start: held in memory for this run only, never
    stored or logged), `hints` (interpret), `proposals`, `question`, `text_favourite` (climb)."""

    text: str
    kind: FavouriteKind | None
    hint: str | None
    hints: Hints
    proposals: list[Proposal]
    question: str | None
    text_favourite: dict[str, str | None] | None


@dataclass(frozen=True)
class LinkDeps:
    """One link run's ports, log and search budget. `language_model` is the Groq-only model:
    journal text never goes to a free Gemini key (rule 11)."""

    taste: TasteGraph
    journal: JournalRepository
    log: RunLog
    profile_id: UUID
    blocklist: Blocklist
    max_searches: int
    language_model: LanguageModel | None = None
    known_names: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Mention:
    """Something an entry mentions. `artist` and `film` are a song's singer and film."""

    kind: str
    text: str
    artist: str | None = None
    film: str | None = None
    year: int | None = None


@dataclass(frozen=True)
class LinkTarget:
    """Where a suggested link points: an existing node, or a new one to create."""

    mention: Mention
    node: JournalNode
    is_new: bool
    reason: str


class LinkState(TypedDict, total=False):
    """Written by: `entry` (start: its text is held in memory for this run only, never
    logged), `mentions`, `ai_read` (extract), `resolved` (resolve_mentions: mention → match),
    `targets` (match_nodes), `suggested` (save_suggestions)."""

    entry: JournalNode
    mentions: list[Mention]
    ai_read: bool
    resolved: list[tuple[Mention, Proposal | None]]
    targets: list[LinkTarget]
    suggested: int
