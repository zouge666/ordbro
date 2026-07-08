"""Markdown documents with a small front matter block and sections."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)
_LIST_KEYS = {"tags", "skills"}


@dataclass(frozen=True)
class Section:
    id: str
    heading: str
    level: int
    start: int
    end: int


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: tuple[Section, ...] = ()

    @property
    def title(self) -> str:
        return str(self.metadata.get("title", self.id))

    def section(self, section_id: str) -> Section | None:
        return next((s for s in self.sections if s.id == section_id), None)

    def section_text(self, section: Section) -> str:
        return self.text[section.start : section.end].strip()


def parse_markdown(doc_id: str, raw: str, **extra: Any) -> Document:
    """Parse a note. Front matter is ``key: value`` lines between ``---``."""
    metadata: dict[str, Any] = {}
    body = raw
    match = _FRONT_MATTER.match(raw)
    if match:
        for line in match.group(1).splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if key in _LIST_KEYS:
                metadata[key] = [item.strip() for item in value.split(",") if item.strip()]
            else:
                metadata[key] = value
        body = raw[match.end() :]
    metadata.update(extra)
    metadata.setdefault("doc_id", doc_id)
    return Document(id=doc_id, text=body, metadata=metadata, sections=_sections(doc_id, body))


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w]+", "-", text.lower()).strip("-")
    return slug or "section"


def _sections(doc_id: str, body: str) -> tuple[Section, ...]:
    headings = [(m.start(), len(m.group(1)), m.group(2)) for m in _HEADING.finditer(body)]
    sections: list[Section] = []
    seen: dict[str, int] = {}
    first_h2 = next((pos for pos, level, _ in headings if level == 2), len(body))
    has_title = bool(headings) and headings[0][1] == 1
    intro_start = headings[0][0] if has_title else 0
    intro = body[intro_start:first_h2]
    if has_title:
        intro = intro.split("\n", 1)[1] if "\n" in intro else ""
    if intro.strip():
        title = headings[0][2] if has_title else "Intro"
        sections.append(Section(f"{doc_id}#intro", title, 1, intro_start, first_h2))
    h2 = [(pos, text) for pos, level, text in headings if level <= 2 and pos >= first_h2]
    for index, (pos, text) in enumerate(h2):
        end = h2[index + 1][0] if index + 1 < len(h2) else len(body)
        slug = slugify(text)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        sections.append(Section(f"{doc_id}#{slug}", text, 2, pos, end))
    return tuple(sections)
