"""Comparing names of artists, films and books, the way people type them."""

import re

_NON_WORD = re.compile(r"[\W_]+")


def normalise_name(name: str) -> str:
    """Lower-case, punctuation turned into spaces: "T.M. Soundararajan" → "t m soundararajan"."""
    return _NON_WORD.sub(" ", name.casefold()).strip()


def names_match(a: str, b: str) -> bool:
    """True when two names are the same apart from case, punctuation and spacing around initials."""
    return normalise_name(a).replace(" ", "") == normalise_name(b).replace(" ", "")


# Spellings that differ between transliterations of Indian names: "Arijith" for "Arijit",
# "Raheem" for "Rahim", "Shaan"-style double vowels.
_SPELLING_RULES = (
    (re.compile(r"(?<=t)h\b", re.IGNORECASE), ""),
    (re.compile(r"ee", re.IGNORECASE), "i"),
    (re.compile(r"oo", re.IGNORECASE), "u"),
    (re.compile(r"aa", re.IGNORECASE), "a"),
)


def spelling_variants(text: str) -> list[str]:
    """Other likely spellings of a typed name, each rule on its own and then all together.
    Never includes `text` itself. Used only when the name as typed finds nothing."""
    variants: list[str] = []
    everything = text
    for pattern, replacement in _SPELLING_RULES:
        changed = pattern.sub(replacement, text)
        everything = pattern.sub(replacement, everything)
        for candidate in (changed, everything):
            if candidate != text and candidate not in variants:
                variants.append(candidate)
    return variants


_LEADING_ARTICLE = re.compile(r"^(the|a|an) ")


def _initials(name: str) -> str:
    return "".join(word[0] for word in normalise_name(name).split())


def name_fits(found: str, wanted: str) -> bool:
    """True when a search result's name is the name the user meant: the same apart from case,
    punctuation, spacing and a leading "The"; the initials of it ("TMS" for "T. M.
    Soundararajan"); or another spelling of it ("Arijith" for "Arijit")."""
    if names_match(found, wanted):
        return True
    bare_found = _LEADING_ARTICLE.sub("", normalise_name(found))
    bare_wanted = _LEADING_ARTICLE.sub("", normalise_name(wanted))
    if bare_found and names_match(bare_found, bare_wanted):
        return True
    compact = normalise_name(wanted).replace(" ", "")
    if len(compact) >= 2 and " " not in normalise_name(wanted) and _initials(found) == compact:
        return True
    return any(names_match(found, variant) for variant in spelling_variants(wanted)) or any(
        names_match(variant, wanted) for variant in spelling_variants(found)
    )


def mentioned_in(name: str, text: str) -> bool:
    """True when the name appears in the text as whole words, ignoring case and punctuation."""
    needle = normalise_name(name)
    return bool(needle) and f" {needle} " in f" {normalise_name(text)} "
