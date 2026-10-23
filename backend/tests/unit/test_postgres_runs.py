"""Tests for reading agent-run logs stored in Postgres, including rows written before a fix."""

import json

from app.infrastructure.persistence.postgres_runs import steps_to_domain

STEP = {
    "node": "research",
    "message": "Asked Qloo → 10 found.",
    "level": "info",
    "at": "2026-10-24T02:49:19+00:00",
}


def test_steps_are_read_from_json_objects() -> None:
    steps = steps_to_domain([STEP, {**STEP, "node": "compose", "level": "warning"}])

    assert [(step.node, step.level.value) for step in steps] == [
        ("research", "info"),
        ("compose", "warning"),
    ]


def test_steps_written_as_json_strings_by_the_old_code_still_read() -> None:
    legacy = [json.dumps([STEP]), json.dumps([{**STEP, "message": "second"}])]

    assert [step.message for step in steps_to_domain(legacy)] == [
        "Asked Qloo → 10 found.",
        "second",
    ]
