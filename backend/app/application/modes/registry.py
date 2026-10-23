"""The `ModeRegistry`: session modes by name."""

from collections.abc import Iterable

from app.application.modes.base import SessionMode
from app.application.modes.standard import StandardMode
from app.application.modes.warmup import WarmupMode
from app.core.errors import InvalidInputError


class ModeRegistry:
    """Looks up a mode by the name the plan endpoint receives."""

    def __init__(self, modes: Iterable[SessionMode]) -> None:
        self._modes = {mode.name: mode for mode in modes}

    @property
    def names(self) -> tuple[str, ...]:
        """Every registered mode's name."""
        return tuple(self._modes)

    def get(self, name: str) -> SessionMode:
        """The mode with this name. Unknown names are invalid input."""
        mode = self._modes.get(name)
        if mode is None:
            raise InvalidInputError(f"Unknown session mode. Use one of: {', '.join(self.names)}.")
        return mode


def default_registry() -> ModeRegistry:
    """The modes available now: `standard` and `warmup`."""
    return ModeRegistry([StandardMode(), WarmupMode()])
