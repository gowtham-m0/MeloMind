"""Comparing names of artists, films and books, the way people type them."""

import re

_NON_WORD = re.compile(r"[\W_]+")


def normalise_name(name: str) -> str:
    """Lower-case, punctuation turned into spaces: "T.M. Soundararajan" → "t m soundararajan"."""
    return _NON_WORD.sub(" ", name.casefold()).strip()


def names_match(a: str, b: str) -> bool:
    """True when two names are the same apart from case, punctuation and spacing around initials."""
    return normalise_name(a).replace(" ", "") == normalise_name(b).replace(" ", "")
