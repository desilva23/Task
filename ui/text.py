"""Showing text safely. Everything the page displays — statements, notes, directions — can carry
words the shopper typed or the model wrote, so markdown is escaped: no link, image or emphasis
can be injected (AC-13)."""

import re

_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~])")


def md(text: str) -> str:
    return _SPECIAL.sub(r"\\\1", text)
