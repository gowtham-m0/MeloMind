"""Step 1, `load_context` (code): the profile, favourites, signals, exclusions and learned
weights. It also says in the log what the user's recent activity changes in this feed."""

from collections.abc import Sequence

from app.application.agent.deps import FeedDeps
from app.application.agent.state import FeedState
from app.application.agent.types import FeedContext, SignalRef
from app.domain.feed import entity_type_of, favourite_ref, is_qloo_ref
from app.domain.feedback import Blocklist, Exclusion, Feedback, Signal
from app.domain.models import Favourite
from app.domain.policies import learned_weights, signal_refs

NODE = "load_context"
LEARNED_SIGNALS_MAX = 5
EXPLAINED_MAX = 4

_WORDS: dict[Signal, str] = {
    Signal.LIKED: "you liked it",
    Signal.SAVED: "you saved it",
    Signal.OPENED: "you opened it",
    Signal.QUIZ_PICK: "you picked it in the taste quiz",
    Signal.JOURNAL_CONFIRMED: "you wrote about it",
    Signal.DISLIKED: "you weren't keen",
}


async def load_context(state: FeedState, deps: FeedDeps) -> FeedState:
    """Build the `FeedContext` and log what was loaded and learned."""
    profile = state["profile"]
    feedback = await deps.feedback.list_for_profile(profile.id)
    exclusions = await deps.exclusions.list_for_profile(profile.id)
    blocklist = Blocklist.from_exclusions(exclusions)
    favourite_signals = _favourite_signals(profile.favourites, blocklist)
    learned = _learned_signals(feedback, blocklist, favourite_signals)
    context = FeedContext(
        profile_id=profile.id,
        first_name=profile.display_name.split()[0],
        birth_year=profile.birth_year,
        country_code=profile.country_code,
        favourite_signals=favourite_signals,
        learned_signals=learned,
        text_favourites=tuple(f.name for f in profile.favourites if not f.verified),
        song_titles=tuple(f.song_title for f in profile.favourites if f.song_title),
        blocklist=blocklist,
        learned_weights=learned_weights(feedback),
        previous_refs=deps.previous_refs,
        previous_tags=deps.previous_tags,
    )
    verified = sum(1 for favourite in profile.favourites if favourite.verified)
    where = f", {profile.country_code}" if profile.country_code else ""
    await deps.log.info(
        NODE,
        f"Loaded {context.first_name}{where}: {len(profile.favourites)} favourites "
        f"({verified} matched in Qloo), {len(learned)} things you've been enjoying lately.",
    )
    for message in _learning_messages(feedback, learned, exclusions):
        await deps.log.info(NODE, message)
    return {"context": context}


def _favourite_signals(
    favourites: Sequence[Favourite], blocklist: Blocklist
) -> tuple[SignalRef, ...]:
    """Verified favourites that aren't excluded, newest first. A song's signal is its singer."""
    signals: dict[str, SignalRef] = {}
    for favourite in sorted(favourites, key=lambda item: item.created_at, reverse=True):
        if favourite.qloo_id is None:
            continue
        if blocklist.blocks(favourite_ref(favourite), favourite.song_title or favourite.name):
            continue
        signals.setdefault(
            favourite.qloo_id,
            SignalRef(
                ref=favourite.qloo_id,
                name=favourite.name,
                entity_type=entity_type_of(favourite.kind),
            ),
        )
    return tuple(signals.values())


def _learned_signals(
    feedback: Sequence[Feedback],
    blocklist: Blocklist,
    favourites: tuple[SignalRef, ...],
) -> tuple[SignalRef, ...]:
    """Items whose weight reached the threshold, newest activity first, if Qloo knows them and
    they aren't excluded."""
    latest = {entry.item_ref: entry for entry in feedback}
    taken = {signal.ref for signal in favourites}
    signals: list[SignalRef] = []
    for ref in signal_refs(feedback):
        entry = latest[ref]
        # Songs aren't Qloo entities; a song's signal reaches the feed through its artist.
        if not is_qloo_ref(ref) or ref in taken or entry.entity_type is None:
            continue
        if blocklist.blocks(ref, entry.title):
            continue
        signals.append(
            SignalRef(ref=ref, name=entry.title, entity_type=entry.entity_type, learned=True)
        )
    return tuple(signals[:LEARNED_SIGNALS_MAX])


def _learning_messages(
    feedback: Sequence[Feedback],
    learned: tuple[SignalRef, ...],
    exclusions: Sequence[Exclusion],
) -> list[str]:
    """Plain-English lines on what recent activity changes in this feed."""
    messages: list[str] = []
    for signal in learned[:EXPLAINED_MAX]:
        kinds = [entry.kind for entry in feedback if entry.item_ref == signal.ref]
        reasons = list(dict.fromkeys(_WORDS[kind] for kind in kinds if kind in _WORDS))
        why = f" ({', '.join(reasons)})" if reasons else ""
        messages.append(f"Steering by {signal.name}{why}.")
    if exclusions:
        titles = [entry.title for entry in exclusions]
        shown = ", ".join(titles[:EXPLAINED_MAX])
        more = len(titles) - EXPLAINED_MAX
        listing = f"{shown} and {more} more" if more > 0 else shown
        messages.append(f"Keeping out what you're not interested in: {listing}.")
    if not feedback and not exclusions:
        messages.append("No likes yet, so this feed starts from your favourites and country.")
    return messages
