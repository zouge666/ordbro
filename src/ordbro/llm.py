"""Optional answer composer that calls an OpenAI-compatible chat API.

It is off by default (``provider = "none"``). When it is on, the model only
sees the retrieved passages and has to cite them. If the call fails, the
extractive answer is used instead.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.request import Request, urlopen

from ordbro.config import LLMSettings
from ordbro.rag.answer import Composer
from ordbro.rag.knowledge_base import Hit

SYSTEM_PROMPT = (
    "You are a patient Danish teacher for adult beginners. Answer in simple English "
    "in at most four sentences. Use only the course notes below and cite them like [1]. "
    "Give one Danish example from the notes. If the notes do not answer the question, "
    "say that you do not know."
)


def build_messages(question: str, hits: Sequence[Hit]) -> list[dict[str, str]]:
    notes = "\n\n".join(
        f"[{i}] {hit.chunk.metadata.get('title')} - {hit.chunk.heading}\n{hit.chunk.text}"
        for i, hit in enumerate(hits, start=1)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {question}\n\nCourse notes:\n{notes}"},
    ]


def make_composer(settings: LLMSettings) -> Composer | None:
    if not settings.enabled:
        return None
    if not settings.base_url or not settings.model:
        raise ValueError("[llm] base_url and model are needed when the provider is not 'none'")

    def compose(question: str, hits: Sequence[Hit]) -> str:
        payload = {
            "model": settings.model,
            "messages": build_messages(question, hits),
            "temperature": 0,
        }
        request = Request(
            settings.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.api_key}",
            },
            method="POST",
        )
        with urlopen(request, timeout=settings.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()

    return compose
