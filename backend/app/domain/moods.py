"""The moods of "Your vibe today", and the tag searches each one stands for."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Mood:
    """One mood chip: its label and the words searched in Qloo's tags."""

    label: str
    tag_queries: tuple[str, ...]


MOODS: dict[str, Mood] = {
    "chill": Mood("Chill", ("chill", "ambient", "slow burn")),
    "happy": Mood("Happy", ("feel-good", "upbeat")),
    "focused": Mood("Focused", ("instrumental", "minimal")),
    "melancholy": Mood("Melancholy", ("melancholic", "bittersweet")),
    "energetic": Mood("Energetic", ("high energy", "action")),
}
