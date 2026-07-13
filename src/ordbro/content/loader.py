"""Load course content from the data folder."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ordbro.content.lexicon import Lexicon, VocabEntry
from ordbro.rag.documents import Document, parse_markdown

COLLECTION = "da-course"
REQUIRED_KEYS = ("title", "title_en", "level", "kind", "summary_en")


@dataclass(frozen=True)
class Content:
    documents: list[Document]
    vocab: list[VocabEntry]
    glossary: dict[str, list[str]]
    lexicon: Lexicon

    def document(self, doc_id: str) -> Document | None:
        return next((doc for doc in self.documents if doc.id == doc_id), None)

    def documents_for_skill(self, skill: str) -> list[Document]:
        return [doc for doc in self.documents if doc.metadata.get("skill") == skill]


def load_documents(corpus_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(corpus_dir.glob("*/*.md")):
        doc = parse_markdown(path.stem, path.read_text(encoding="utf-8"), collection=COLLECTION)
        missing = [key for key in REQUIRED_KEYS if not doc.metadata.get(key)]
        if missing:
            raise ValueError(f"{path.name} is missing front matter keys: {missing}")
        documents.append(doc)
    if not documents:
        raise ValueError(f"no course documents found in {corpus_dir}")
    return documents


def load_vocab(path: Path) -> list[VocabEntry]:
    with path.open(encoding="utf-8") as handle:
        return [VocabEntry.from_dict(item) for item in json.load(handle)]


def load_glossary(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {key.lower(): list(values) for key, values in data.items()}


@lru_cache(maxsize=4)
def load_content(data_dir: str | Path) -> Content:
    root = Path(data_dir)
    vocab = load_vocab(root / "vocab.json")
    return Content(
        documents=load_documents(root / "corpus"),
        vocab=vocab,
        glossary=load_glossary(root / "glossary.json"),
        lexicon=Lexicon(vocab),
    )
