"""Tokenising shared by document retrieval and metric matching."""
from __future__ import annotations

import re

STOPWORDS = frozenset("""
a an the and or of to in on for with by is are was were be been it its this that these those what which who whom
how do does did can could should would will i we you our your my me us at as from than then there their they them
about into over any all each per vs versus if when where why get gets got has have had not no yes so up out
""".split())

_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def stem(word: str) -> str:
    for suffix in ("ations", "ation", "ions", "ion", "ings", "ing", "ies", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def tokenize(text: str) -> list[str]:
    return [stem(w) for w in _WORD.findall(text.lower()) if w not in STOPWORDS]
