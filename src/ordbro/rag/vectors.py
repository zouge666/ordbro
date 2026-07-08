"""Vector routes.

Three ways to turn text into a vector:

* ``HashEmbedder`` is the offline fallback from LinguaPilot. It hashes the
  whole text with SHA-256, so two different texts get unrelated vectors.
  It is kept only to measure what it does to fusion.
* ``SubwordVectorizer`` builds TF-IDF vectors over character n-grams (3 to
  5 letters, with word boundaries). Inflected forms such as "hus", "huset"
  and "husene" share most n-grams, which helps a lot in Danish. It runs
  offline and needs no model file.
* ``OllamaEmbedder`` calls a local Ollama server, as LinguaPilot does with
  nomic-embed-text. It is optional.
"""

from __future__ import annotations

import hashlib
import json
import math
import zlib
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from urllib.request import Request, urlopen

from ordbro.nlp.tokenize import WORD_RE

SparseVector = dict[int, float]


class HashEmbedder:
    kind = "dense"

    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions

    def fit(self, texts: Iterable[str]) -> None:
        return None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        rows: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values: list[float] = []
            index = 0
            while len(values) < self.dimensions:
                raw = digest[index % len(digest)] * 256 + digest[(index + 1) % len(digest)]
                values.append(raw / 65535.0 * 2.0 - 1.0)
                index += 2
            rows.append(_unit(values))
        return rows


class OllamaEmbedder:
    kind = "dense"

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
        batch_size: int = 32,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = batch_size

    def fit(self, texts: Iterable[str]) -> None:
        return None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        rows: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            payload = json.dumps({"model": self.model, "input": batch}).encode("utf-8")
            request = Request(
                self.base_url + "/api/embed",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            rows.extend(_unit([float(x) for x in vector]) for vector in data["embeddings"])
        return rows

    def available(self) -> bool:
        try:
            with urlopen(self.base_url + "/api/tags", timeout=2) as response:
                return response.status == 200
        except OSError:
            return False


class SubwordVectorizer:
    kind = "sparse"

    def __init__(self, n_min: int = 3, n_max: int = 5, buckets: int = 1 << 20) -> None:
        self.n_min = n_min
        self.n_max = n_max
        self.buckets = buckets
        self._idf: dict[int, float] = {}
        self._default_idf = 1.0

    def fit(self, texts: Iterable[str]) -> None:
        df: Counter[int] = Counter()
        count = 0
        for text in texts:
            count += 1
            df.update(set(self._features(text)))
        self._idf = {key: math.log((1 + count) / (1 + value)) + 1.0 for key, value in df.items()}
        self._default_idf = math.log(1 + count) + 1.0

    def transform(self, text: str) -> SparseVector:
        counts = Counter(self._features(text))
        vector = {
            key: (1.0 + math.log(tf)) * self._idf.get(key, self._default_idf)
            for key, tf in counts.items()
        }
        norm = math.sqrt(sum(v * v for v in vector.values()))
        return {key: v / norm for key, v in vector.items()} if norm else {}

    def embed(self, texts: Sequence[str]) -> list[SparseVector]:
        return [self.transform(text) for text in texts]

    def _features(self, text: str) -> list[int]:
        features: list[int] = []
        for match in WORD_RE.finditer(text.lower()):
            word = f"<{match.group(0)}>"
            features.append(self._bucket(word))
            for n in range(self.n_min, self.n_max + 1):
                for i in range(len(word) - n + 1):
                    features.append(self._bucket(word[i : i + n]))
        return features

    def _bucket(self, gram: str) -> int:
        return zlib.crc32(gram.encode("utf-8")) % self.buckets


class VectorIndex:
    """Brute force cosine search. Fine for a few thousand chunks."""

    def __init__(self, kind: str) -> None:
        if kind not in {"dense", "sparse"}:
            raise ValueError("kind must be 'dense' or 'sparse'")
        self.kind = kind
        self._ids: list[str] = []
        self._vectors: list = []

    def add(self, ids: Sequence[str], vectors: Sequence) -> None:
        self._ids.extend(ids)
        self._vectors.extend(vectors)

    def search(
        self, query, top_k: int, allowed: Collection[str] | None = None
    ) -> list[tuple[str, float]]:
        dot = _sparse_dot if self.kind == "sparse" else _dense_dot
        scored = [
            (doc_id, dot(query, vector))
            for doc_id, vector in zip(self._ids, self._vectors, strict=True)
            if allowed is None or doc_id in allowed
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]

    def score(self, query, doc_id: str) -> float:
        dot = _sparse_dot if self.kind == "sparse" else _dense_dot
        try:
            return dot(query, self._vectors[self._ids.index(doc_id)])
        except ValueError:
            return 0.0


def cosine(a: SparseVector, b: SparseVector) -> float:
    return _sparse_dot(a, b)


def _unit(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values] if norm else values


def _dense_dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


def _sparse_dot(a: SparseVector, b: SparseVector) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(key, 0.0) for key, value in a.items())
