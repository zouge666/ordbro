"""Retrieval for Ordbro.

The design follows the LinguaPilot RAG infrastructure
(github.com/EU-ABPLA/linguapilot-rag-infrastructure): ingestion and query
are separate steps, there is a sparse route and a vector route, results are
merged with Reciprocal Rank Fusion, and every query leaves a trace.

What changes for Danish (analyzer, chunking, metadata prefix, subword
vectors and query expansion) is switched on one step at a time through
presets. The evaluation uses the same presets.
"""

from ordbro.rag.answer import Answer, Answerer
from ordbro.rag.documents import Document, Section, parse_markdown
from ordbro.rag.knowledge_base import Hit, KnowledgeBase, SearchResult
from ordbro.rag.presets import PRESETS, Preset, get_preset

__all__ = [
    "PRESETS",
    "Answer",
    "Answerer",
    "Document",
    "Hit",
    "KnowledgeBase",
    "Preset",
    "SearchResult",
    "Section",
    "get_preset",
    "parse_markdown",
]
