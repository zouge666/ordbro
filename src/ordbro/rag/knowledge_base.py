"""The knowledge base: ingestion and hybrid search over course material."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from ordbro.nlp.analyzers import DanishAnalyzer, LegacyAnalyzer, guess_language
from ordbro.nlp.danish import ENGLISH_STOPWORDS
from ordbro.nlp.tokenize import WORD_RE
from ordbro.rag.chunking import Chunk, RecursiveChunker, SectionChunker
from ordbro.rag.documents import Document
from ordbro.rag.expansion import GlossaryExpander
from ordbro.rag.fusion import rrf
from ordbro.rag.presets import Preset, get_preset
from ordbro.rag.sparse import BM25Index
from ordbro.rag.trace import Trace
from ordbro.rag.vectors import (
    HashEmbedder,
    OllamaEmbedder,
    SubwordVectorizer,
    VectorIndex,
    cosine,
)


@dataclass
class Hit:
    chunk: Chunk
    score: float
    ranks: dict[str, int] = field(default_factory=dict)
    route_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk.id,
            "doc_id": self.chunk.doc_id,
            "title": self.chunk.metadata.get("title"),
            "title_en": self.chunk.metadata.get("title_en"),
            "heading": self.chunk.heading,
            "level": self.chunk.metadata.get("level"),
            "section_ids": list(self.chunk.section_ids),
            "text": self.chunk.text,
            "score": round(self.score, 6),
            "ranks": self.ranks,
            "route_scores": {k: round(v, 6) for k, v in self.route_scores.items()},
        }


@dataclass
class SearchResult:
    query: str
    preset: str
    hits: list[Hit]
    terms: list[str]
    expansions: list[str]
    confidence: float
    trace: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "preset": self.preset,
            "terms": self.terms,
            "expansions": self.expansions,
            "confidence": round(self.confidence, 4),
            "hits": [hit.to_dict() for hit in self.hits],
            "trace": self.trace,
        }


class KnowledgeBase:
    def __init__(
        self,
        documents: Sequence[Document],
        preset: Preset | str = "ordbro",
        glossary: Mapping[str, Sequence[str]] | None = None,
        rrf_k: int = 60,
        ollama: OllamaEmbedder | None = None,
        confidence_on: str = "index_text",
    ) -> None:
        if confidence_on not in {"index_text", "text"}:
            raise ValueError("confidence_on must be 'index_text' or 'text'")
        self.confidence_on = confidence_on
        self.preset = get_preset(preset)
        self.documents = {doc.id: doc for doc in documents}
        self.rrf_k = rrf_k
        self.expander = GlossaryExpander(glossary or {})
        if self.preset.analyzer == "legacy":
            self.analyzer: DanishAnalyzer | LegacyAnalyzer = LegacyAnalyzer()
        else:
            self.analyzer = DanishAnalyzer(
                stem=self.preset.stem, split_compounds=self.preset.compounds
            )
        self._ollama = ollama
        self.chunks: list[Chunk] = []
        self._by_id: dict[str, Chunk] = {}
        self.bm25 = BM25Index(idf=self.preset.idf)
        self._routes: dict[str, tuple[Any, VectorIndex]] = {}
        self._confidence = SubwordVectorizer()
        self._confidence_vectors: dict[str, dict[int, float]] = {}
        self.ingestion_trace: dict[str, Any] = {}
        self._ingest()

    # ingestion --------------------------------------------------------------

    def _ingest(self) -> None:
        trace = Trace("ingestion", preset=self.preset.name, documents=len(self.documents))
        chunker = SectionChunker() if self.preset.chunker == "sections" else RecursiveChunker()
        for doc in self.documents.values():
            self.chunks.extend(chunker.chunk(doc, metadata_prefix=self.preset.metadata_prefix))
        self._by_id = {chunk.id: chunk for chunk in self.chunks}
        trace.stage("chunk", chunker=chunker.name, chunks=len(self.chunks))

        texts = [chunk.index_text for chunk in self.chunks]
        self.analyzer.fit(texts)
        self.bm25.build({c.id: self.analyzer.index_terms(c.index_text) for c in self.chunks})
        trace.stage("bm25", analyzer=self.analyzer.name, idf=self.preset.idf)

        for route in self.preset.routes:
            if route == "bm25":
                continue
            encoder = self._encoder(route)
            encoder.fit(texts)
            index = VectorIndex(encoder.kind)
            index.add([c.id for c in self.chunks], encoder.embed(texts))
            self._routes[route] = (encoder, index)
            trace.stage(f"vectors:{route}", kind=encoder.kind)

        # The confidence vectors use the same text as the indexes by default, so
        # an English question can match the English title and summary.
        field = self.confidence_on
        self._confidence.fit(getattr(chunk, field) for chunk in self.chunks)
        self._confidence_vectors = {
            c.id: self._confidence.transform(getattr(c, field)) for c in self.chunks
        }
        trace.stage("confidence_vectors")
        self.ingestion_trace = trace.to_dict()

    def _encoder(self, route: str):
        if route == "hash":
            return HashEmbedder()
        if route == "subword":
            return SubwordVectorizer()
        if route == "ollama":
            return self._ollama or OllamaEmbedder()
        raise ValueError(f"unknown route: {route}")

    # query ------------------------------------------------------------------

    def chunk(self, chunk_id: str) -> Chunk:
        return self._by_id[chunk_id]

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> SearchResult:
        trace = Trace("query", query=query, preset=self.preset.name, top_k=top_k)
        terms = self.analyzer.query_terms(query)
        added: list[str] = []
        matched: list[str] = []
        if self.preset.expansion and len(self.expander):
            added, matched = self.expander.expand(query)
            for term in added:
                terms.extend(self.analyzer.index_terms(term))
        vector_query = self._vector_query(query, added)
        trace.stage("analyze", terms=terms, expansions=matched, added=added)

        allowed = self._allowed(filters) if filters and self.preset.filter_first else None
        rankings: dict[str, list[tuple[str, float]]] = {}
        rankings["bm25"] = self.bm25.search(terms, top_k, allowed)
        trace.stage("bm25", candidates=_preview(rankings["bm25"]))
        for route, (encoder, index) in self._routes.items():
            query_vector = encoder.embed([vector_query])[0]
            rankings[route] = index.search(query_vector, top_k, allowed)
            trace.stage(route, candidates=_preview(rankings[route]))

        fused = rrf(rankings, k=self.rrf_k, top_k=top_k)
        trace.stage("fusion", method="rrf", k=self.rrf_k, results=_preview(fused))
        if filters and not self.preset.filter_first:
            before = len(fused)
            fused = [item for item in fused if _matches(self._by_id[item[0]], filters)]
            trace.stage("filter", before=before, after=len(fused))

        hits = []
        for chunk_id, score in fused:
            ranks = {}
            route_scores = {}
            for route, ranking in rankings.items():
                for rank, (cid, route_score) in enumerate(ranking, start=1):
                    if cid == chunk_id:
                        ranks[route] = rank
                        route_scores[route] = route_score
                        break
            hits.append(Hit(self._by_id[chunk_id], score, ranks, route_scores))

        confidence = 0.0
        if hits:
            query_vector = self._confidence.transform(vector_query)
            confidence = max(
                cosine(query_vector, self._confidence_vectors[hit.chunk.id]) for hit in hits[:3]
            )
        trace.stage("confidence", value=round(confidence, 4))
        return SearchResult(
            query, self.preset.name, hits, terms, matched, confidence, trace.to_dict()
        )

    def stats(self) -> dict[str, Any]:
        kinds: dict[str, int] = {}
        for doc in self.documents.values():
            kind = str(doc.metadata.get("kind", "note"))
            kinds[kind] = kinds.get(kind, 0) + 1
        return {
            "preset": self.preset.name,
            "label": self.preset.label,
            "documents": len(self.documents),
            "kinds": kinds,
            "chunks": len(self.chunks),
            "routes": list(self.preset.routes),
            "analyzer": self.analyzer.name,
            "glossary_entries": len(self.expander),
        }

    def _vector_query(self, query: str, added: Sequence[str]) -> str:
        tokens = [m.group(0) for m in WORD_RE.finditer(query)]
        if guess_language(tokens) == "en":
            tokens = [t for t in tokens if t != "I" and t.lower() not in ENGLISH_STOPWORDS]
        if isinstance(self.analyzer, DanishAnalyzer):
            tokens = [self.analyzer.fix_ascii(t.lower()) for t in tokens]
        return " ".join([*tokens, *added]) or query

    def _allowed(self, filters: Mapping[str, Any]) -> set[str]:
        return {chunk.id for chunk in self.chunks if _matches(chunk, filters)}


def _matches(chunk: Chunk, filters: Mapping[str, Any]) -> bool:
    for key, value in filters.items():
        actual = chunk.metadata.get(key)
        if isinstance(value, (list, tuple, set)):
            if actual not in value:
                return False
        elif actual != value:
            return False
    return True


def _preview(ranking: Sequence[tuple[str, float]], size: int = 5) -> list[dict[str, Any]]:
    return [{"chunk_id": cid, "score": round(score, 4)} for cid, score in ranking[:size]]
