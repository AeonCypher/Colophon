"""Markdown rendering and reading-time analysis.

Markdown source flows into HTML plus table-of-contents metadata that content
loading merges into page data for templates.
"""

from __future__ import annotations

import re
from typing import Any

import mistune
import readability
import syntok.segmenter as segmenter
from bs4 import BeautifulSoup
from slugify import slugify


MARKDOWN_PLUGINS = [
    "strikethrough",
    "table",
    "url",
    "task_lists",
    "def_list",
]


class TocRenderer(mistune.HTMLRenderer):
    def __init__(self) -> None:
        super().__init__(escape=False)
        self.toc: list[dict[str, str]] = []
        self._seen_ids: set[str] = set()

    def _unique_id(self, text: str) -> str:
        base = slugify(text) or "section"
        anchor = base
        index = 2

        while anchor in self._seen_ids:
            anchor = f"{base}-{index}"
            index += 1

        self._seen_ids.add(anchor)
        return anchor

    def heading(self, text: str, level: int, **attrs: Any) -> str:
        if level == 2:
            label = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
            anchor = attrs.get("id") or self._unique_id(label)
            attrs["id"] = anchor
            self._seen_ids.add(anchor)
            self.toc.append({"id": anchor, "text": label})

        return super().heading(text, level, **attrs)


def render_markdown(markdown_text: str) -> tuple[str, list[dict[str, str]]]:
    renderer = TocRenderer()
    markdown = mistune.create_markdown(
        escape=False,
        plugins=MARKDOWN_PLUGINS,
        renderer=renderer,
    )

    return markdown(markdown_text), renderer.toc


def text_stats(text: str) -> dict[str, Any] | None:
    try:
        tokenized = "\n\n".join(
            "\n".join(
                " ".join(token.value for token in sentence)
                for sentence in paragraph
            )
            for paragraph in segmenter.analyze(text)
        )
        return readability.getmeasures(tokenized, lang="en")
    except Exception:
        return None


def wpm_from_kincaid_grade(grade: float) -> int:
    return max(120, int(330 - 7.67 * grade))


def estimate_reading_minutes(html: str) -> int:
    plain_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    stats = text_stats(plain_text)

    if stats:
        kincaid = stats["readability grades"]["Kincaid"]
        word_count = stats["sentence info"]["words"]
        return max(1, round(word_count / wpm_from_kincaid_grade(kincaid)))

    word_count = len(re.findall(r"\w+", plain_text))
    return max(1, round(word_count / 225))
