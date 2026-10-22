"""Composition root: the only place that chooses adapters and wires dependencies."""

from typing import Annotated, Literal

from fastapi import Depends

from app.core.settings import Settings, get_settings

QlooMode = Literal["live", "demo_fixtures"]

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_qloo_mode(settings: SettingsDep) -> QlooMode:
    """Use live Qloo when an API key is set, and the hand-written demo fixtures otherwise."""
    return "live" if settings.qloo_api_key.get_secret_value().strip() else "demo_fixtures"


QlooModeDep = Annotated[QlooMode, Depends(get_qloo_mode)]
