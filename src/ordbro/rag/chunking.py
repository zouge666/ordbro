"""Chunkers.

``RecursiveChunker`` uses the recursive splitter from LinguaPilot with the
same separators and defaults (800 characters, 100 overlap).
``SectionChunker`` makes one chunk per section, so a grammar rule stays
together with its examples.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from ordbro.rag.documents import Document, Section

_SEPARATORS = ("\n```", "\n# ", "\n## ", "\n### ", "\n\n", "\n", " ")


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    text: str
    index_text: str
    start: int
    end: int
    section_ids: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def heading(self) -> str:
        return str(self.metadata.get("heading", ""))


class RecursiveSplitter:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100) -> None:
        self.chunk_size = max(1, int(chunk_size))
        self.chunk_overlap = max(0, int(chunk_overlap))

    def split_text(self, text: str) -> list[str]:
        if not text.strip():
            return []
        return self._recursive_split(text, list(_SEPARATORS))

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            value = text.strip()
            return [value] if value else []
        if not separators:
            return self._hard_split(text)
        parts = _split_keep_separator(text, separators[0])
        if len(parts) <= 1:
            return self._recursive_split(text, separators[1:])
        output: list[str] = []
        buffer = ""
        for part in parts:
            if len(part) > self.chunk_size:
                if buffer.strip():
                    output.append(buffer.strip())
                    buffer = ""
                output.extend(self._recursive_split(part, separators[1:]))
                continue
            if not buffer:
                buffer = part
                continue
            if len(buffer) + len(part) <= self.chunk_size:
                buffer += part
                continue
            output.append(buffer.strip())
            buffer = self._attach_overlap(buffer, part)
        if buffer.strip():
            output.append(buffer.strip())
        return output

    def _hard_split(self, text: str) -> list[str]:
        step = self.chunk_size - self.chunk_overlap
        if step <= 0:
            step = self.chunk_size
        output: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                output.append(chunk)
            if end >= len(text):
                break
            start += step
        return output

    def _attach_overlap(self, current: str, next_part: str) -> str:
        if self.chunk_overlap <= 0:
            return next_part
        return current[-self.chunk_overlap :] + next_part


def _split_keep_separator(text: str, separator: str) -> list[str]:
    parts = text.split(separator)
    if len(parts) <= 1:
        return [text]
    output = [parts[0]] if parts[0] else []
    output.extend(separator + value for value in parts[1:])
    return output


class RecursiveChunker:
    name = "recursive"

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100) -> None:
        self.splitter = RecursiveSplitter(chunk_size, chunk_overlap)

    def chunk(self, document: Document, metadata_prefix: bool = False) -> list[Chunk]:
        chunks: list[Chunk] = []
        search_start = 0
        for index, piece in enumerate(self.splitter.split_text(document.text)):
            start = document.text.find(piece, search_start)
            if start < 0:
                start = document.text.find(piece)
            if start < 0:
                start = min(search_start, len(document.text))
            end = min(start + len(piece), len(document.text))
            search_start = max(search_start + 1, end)
            sections = _overlapping(document.sections, start, end)
            heading = sections[0].heading if sections else ""
            chunks.append(
                _make_chunk(
                    document,
                    f"{document.id}:{index:03d}",
                    piece,
                    start,
                    end,
                    sections,
                    heading,
                    metadata_prefix,
                )
            )
        return chunks


class SectionChunker:
    name = "sections"

    def __init__(self, max_chars: int = 1200, overlap: int = 100) -> None:
        self.max_chars = max_chars
        self.splitter = RecursiveSplitter(max_chars, overlap)

    def chunk(self, document: Document, metadata_prefix: bool = True) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in document.sections:
            text = document.text[section.start : section.end]
            pieces = (
                [text.strip()] if len(text) <= self.max_chars else self.splitter.split_text(text)
            )
            offset = section.start
            for piece in pieces:
                if not piece:
                    continue
                start = document.text.find(piece, offset)
                start = start if start >= 0 else section.start
                end = start + len(piece)
                offset = start + 1
                chunk_id = f"{document.id}:{len(chunks):03d}"
                chunks.append(
                    _make_chunk(
                        document,
                        chunk_id,
                        piece,
                        start,
                        end,
                        (section,),
                        section.heading,
                        metadata_prefix,
                    )
                )
        return chunks


def _overlapping(sections: Sequence[Section], start: int, end: int) -> tuple[Section, ...]:
    return tuple(s for s in sections if s.start < end and start < s.end)


def _make_chunk(
    document: Document,
    chunk_id: str,
    text: str,
    start: int,
    end: int,
    sections: Sequence[Section],
    heading: str,
    metadata_prefix: bool,
) -> Chunk:
    meta = document.metadata
    metadata = {
        "doc_id": document.id,
        "title": document.title,
        "title_en": meta.get("title_en", ""),
        "heading": heading,
        "level": meta.get("level", ""),
        "kind": meta.get("kind", "note"),
        "collection": meta.get("collection", "default"),
    }
    index_text = text
    if metadata_prefix:
        parts = [document.title, str(meta.get("title_en", "")), heading]
        prefix = " | ".join(part for part in parts if part)
        summary = str(meta.get("summary_en", ""))
        index_text = f"{prefix}\n{summary}\n{text}" if summary else f"{prefix}\n{text}"
    return Chunk(
        id=chunk_id,
        doc_id=document.id,
        text=text,
        index_text=index_text,
        start=start,
        end=end,
        section_ids=tuple(s.id for s in sections),
        metadata=metadata,
    )
