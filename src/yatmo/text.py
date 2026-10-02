"""Renders the neighbourhood text as HTML, Markdown or plain text.

Sentences carry ``[STRONG]...[/STRONG]`` markers around the key places; ``render_html`` turns them into
``<strong>``. Titles: the first paragraph names the street, the second the city (``titles="street-city"``),
or the city only (``"city"``, for discreet listings), or neither (``"generic"``).
"""

from __future__ import annotations

from html import escape
from typing import Iterable, Optional, Sequence

from .models import SummaryText, TextParagraph

STRONG_OPEN = "[STRONG]"
STRONG_CLOSE = "[/STRONG]"


def strip_markers(text: str) -> str:
    return text.replace(STRONG_OPEN, "").replace(STRONG_CLOSE, "")


def sentence_to_html(sentence: str, strong: bool = True) -> str:
    """Escapes a sentence and turns the markers into ``<strong>``."""
    escaped = escape(sentence.strip(), quote=True)
    return escaped.replace(STRONG_OPEN, "<strong>").replace(STRONG_CLOSE, "</strong>") if strong else strip_markers(escaped)


def _title(paragraph: TextParagraph, index: int, mode: str) -> str:
    if mode == "generic":
        return paragraph.title
    if mode == "city":
        return paragraph.title_city if index == 0 and paragraph.title_city else paragraph.title
    if index == 0 and paragraph.title_street:
        return paragraph.title_street
    if index == 1 and paragraph.title_city:
        return paragraph.title_city
    return paragraph.title


def _select(text: SummaryText, paragraphs: Optional[Iterable[str]]) -> Sequence[TextParagraph]:
    wanted = [p.lower() for p in paragraphs] if paragraphs else None
    return [p for p in text.paragraphs if not wanted or p.icon_id.lower() in wanted]


def render_html(text: SummaryText, heading: Optional[str] = "h3", titles: str = "street-city", paragraphs: Optional[Iterable[str]] = None, strong: bool = True, css_class: str = "") -> str:
    """``<div class="yatmo-text">`` with a heading and a paragraph (and a list, rarely) per paragraph."""
    parts = []
    for index, paragraph in enumerate(_select(text, paragraphs)):
        html = ""
        if heading:
            html += f"<{heading}>{escape(_title(paragraph, index, titles), quote=True)}</{heading}>"
        if paragraph.sentences:
            html += "<p>" + " ".join(sentence_to_html(s, strong) for s in paragraph.sentences) + "</p>"
        if paragraph.items:
            html += "<ul>" + "".join("<li>" + sentence_to_html(s, strong) + "</li>" for s in paragraph.items) + "</ul>"
        parts.append(html)
    classes = ("yatmo-text " + css_class).strip()
    return f'<div class="{escape(classes, quote=True)}">' + "".join(parts) + "</div>"


def render_markdown(text: SummaryText, titles: str = "street-city", paragraphs: Optional[Iterable[str]] = None, strong: bool = True) -> str:
    blocks = []
    for index, paragraph in enumerate(_select(text, paragraphs)):
        to_md = (lambda s: s.strip().replace(STRONG_OPEN, "**").replace(STRONG_CLOSE, "**")) if strong else (lambda s: strip_markers(s.strip()))
        lines = ["### " + _title(paragraph, index, titles), ""]
        if paragraph.sentences:
            lines.append(" ".join(to_md(s) for s in paragraph.sentences))
        lines.extend("- " + to_md(i) for i in paragraph.items)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_plain(text: SummaryText, titles: str = "street-city", paragraphs: Optional[Iterable[str]] = None) -> str:
    blocks = []
    for index, paragraph in enumerate(_select(text, paragraphs)):
        lines = [_title(paragraph, index, titles)]
        lines.extend(strip_markers(s) for s in paragraph.sentences)
        lines.extend("- " + strip_markers(i) for i in paragraph.items)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
