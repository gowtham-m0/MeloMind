"""Step 1, `load_context` (code): the profile, favourites, feedback, exclusions and learned
weights. It also explains in the log what earlier reactions change in this plan."""

from collections import defaultdict
from collections.abc import Sequence

from app.application.agent.deps import PlanDeps
from app.application.agent.state import PlanState
from app.application.agent.types import PlanContext, SignalRef
from app.domain.feedback import Actor, Blocklist, Exclusion, ExclusionKind, Feedback
from app.domain.models import Favourite, search_type_for
from app.domain.policies import SIGNAL_THRESHOLD, learned_weights, signal_refs
from app.domain.sessions import favourite_ref, is_favourite_ref

NODE = "load_context"
LEARNED_SIGNALS_MAX = 5
EXPLAINED_MAX = 4

_WORDS: dict[tuple[Actor, str], str] = {
    (Actor.CAREGIVER, "sang_along"): "the caregiver noted they sang along",
    (Actor.CAREGIVER, "smiled"): "the caregiver noted a smile",
    (Actor.CAREGIVER, "calm"): "the caregiver noted they were calm",
    (Actor.CAREGIVER, "neutral"): "the caregiver noted no reaction",
    (Actor.PERSON, "chose"): "picked in Person mode",
    (Actor.PERSON, "loved"): "♥ in Person mode",
    (Actor.PERSON, "replayed"): "played again in Person mode",
    (Actor.PERSON, "skipped"): "skipped quickly in Person mode",
}


async def load_context(state: PlanState, deps: PlanDeps) -> PlanState:
    """Build the `PlanContext` and log what was loaded and learned."""
    profile = state["profile"]
    feedback = await deps.feedback.list_for_profile(profile.id)
    exclusions = await deps.exclusions.list_for_profile(profile.id)
    blocklist = Blocklist.from_exclusions(exclusions)
    weights = learned_weights(feedback)
    favourite_signals = _favourite_signals(profile.favourites, blocklist)
    learned = _learned_signals(weights, feedback, blocklist, favourite_signals)
    context = PlanContext(
        profile_id=profile.id,
        first_name=profile.display_name.split()[0],
        birth_year=profile.birth_year,
        country_code=profile.country_code,
        places=tuple(profile.places_lived),
        languages=tuple(profile.languages),
        favourite_signals=favourite_signals,
        learned_signals=learned,
        text_favourites=tuple(f.name for f in profile.favourites if not f.verified),
        song_titles=tuple(f.song_title for f in profile.favourites if f.song_title),
        blocklist=blocklist,
        learned_weights=weights,
        target_minutes=deps.target_minutes,
    )
    hometown = f", {context.places[0]}" if context.places else ""
    verified = sum(1 for favourite in profile.favourites if favourite.verified)
    await deps.log.info(
        NODE,
        f"Loaded {context.first_name}: born {context.birth_year}{hometown}, "
        f"{len(profile.favourites)} favourites ({verified} matched in Qloo).",
    )
    for message in _learning_messages(feedback, weights, exclusions):
        await deps.log.info(NODE, message)
    return {"context": context}


def _favourite_signals(
    favourites: Sequence[Favourite], blocklist: Blocklist
) -> tuple[SignalRef, ...]:
    """Verified, unblocked favourites. A song's signal is its singer."""
    signals: dict[str, SignalRef] = {}
    for favourite in favourites:
        if favourite.qloo_id is None or favourite.qloo_id in blocklist.refs:
            continue
        if blocklist.blocks(favourite_ref(favourite), favourite.song_title or favourite.name):
            continue
        signals.setdefault(
            favourite.qloo_id,
            SignalRef(
                ref=favourite.qloo_id,
                name=favourite.name,
                entity_type=search_type_for(favourite.kind),
            ),
        )
    return tuple(signals.values())


def _learned_signals(
    weights: dict[str, float],
    feedback: Sequence[Feedback],
    blocklist: Blocklist,
    favourites: tuple[SignalRef, ...],
) -> tuple[SignalRef, ...]:
    """Items whose weight reached the threshold, if Qloo knows them and they aren't blocked."""
    latest = {entry.item_ref: entry for entry in feedback}
    taken = {signal.ref for signal in favourites}
    signals: list[SignalRef] = []
    for ref in signal_refs(weights):
        entry = latest[ref]
        if is_favourite_ref(ref) or ref in taken or entry.entity_type is None:
            continue
        if blocklist.blocks(ref, entry.title):
            continue
        signals.append(
            SignalRef(ref=ref, name=entry.title, entity_type=entry.entity_type, learned=True)
        )
    return tuple(signals[:LEARNED_SIGNALS_MAX])


def _learning_messages(
    feedback: Sequence[Feedback], weights: dict[str, float], exclusions: Sequence[Exclusion]
) -> list[str]:
    """Plain-English lines on what the caregiver's reactions and the person's taps change."""
    titles: dict[str, str] = {}
    words: defaultdict[str, list[str]] = defaultdict(list)
    for entry in feedback:
        titles[entry.item_ref] = entry.title
        label = _WORDS.get((entry.actor, entry.kind))
        if label and label not in words[entry.item_ref]:
            words[entry.item_ref].append(label)
    messages: list[str] = []
    ordered = sorted(weights.items(), key=lambda pair: -abs(pair[1]))
    for ref, weight in ordered[:EXPLAINED_MAX]:
        if weight == 0 or ref not in words:
            continue
        if weight >= SIGNAL_THRESHOLD:
            effect = "used as a signal for this plan"
        elif weight > 0:
            effect = "ranked a little higher"
        else:
            effect = "ranked lower"
        messages.append(f"{titles[ref]}: {'; '.join(words[ref])} → {effect}.")
    rejected = [entry.title for entry in exclusions if entry.kind is ExclusionKind.REJECTED]
    hidden = [entry.title for entry in exclusions if entry.kind is ExclusionKind.HIDDEN]
    if rejected:
        messages.append(f"Keeping out what the caregiver rejected: {_list(rejected)}.")
    if hidden:
        messages.append(f"Keeping out what upset them, until reviewed: {_list(hidden)}.")
    if not feedback and not exclusions:
        messages.append("No reactions yet, so this plan starts from the profile and favourites.")
    return messages


def _list(titles: list[str]) -> str:
    shown = ", ".join(titles[:EXPLAINED_MAX])
    more = len(titles) - EXPLAINED_MAX
    return f"{shown} and {more} more" if more > 0 else shown
