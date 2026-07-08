"""Retrieval presets.

The presets form a ladder. Each step changes one thing compared with the
step before it, so the evaluation can show what each change is worth.

c0  LinguaPilot sparse route, as configured (Ollama not running)
c1  LinguaPilot with its offline hash embedding and RRF
c1n LinguaPilot with nomic-embed-text through Ollama (needs Ollama)
c2  + Danish analyzer (Unicode tokens, stems, compounds, safe IDF)
c3  + one chunk per section
c4  + metadata prefix (title, English title, heading, English summary)
c5  + subword vector route fused with RRF
c6  + English to Danish glossary expansion  (= "ordbro")
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Preset:
    name: str
    label: str
    analyzer: str = "danish"
    stem: bool = True
    compounds: bool = True
    idf: str = "robertson"
    chunker: str = "sections"
    metadata_prefix: bool = True
    routes: tuple[str, ...] = ("bm25", "subword")
    expansion: bool = True
    filter_first: bool = True

    @property
    def needs_ollama(self) -> bool:
        return "ollama" in self.routes


_C0 = Preset(
    name="c0",
    label="LinguaPilot, sparse only",
    analyzer="legacy",
    idf="legacy",
    chunker="recursive",
    metadata_prefix=False,
    routes=("bm25",),
    expansion=False,
    filter_first=False,
)
_C1 = replace(_C0, name="c1", label="LinguaPilot, hash fallback", routes=("bm25", "hash"))
_C1N = replace(_C0, name="c1n", label="LinguaPilot, nomic-embed-text", routes=("bm25", "ollama"))
_C2 = replace(
    _C0,
    name="c2",
    label="+ Danish analyzer",
    analyzer="danish",
    idf="robertson",
    filter_first=True,
)
_C3 = replace(_C2, name="c3", label="+ section chunks", chunker="sections")
_C4 = replace(_C3, name="c4", label="+ metadata prefix", metadata_prefix=True)
_C5 = replace(_C4, name="c5", label="+ subword vectors", routes=("bm25", "subword"))
_C6 = replace(_C5, name="c6", label="+ glossary expansion", expansion=True)

LADDER = (_C0, _C1, _C1N, _C2, _C3, _C4, _C5, _C6)

ABLATIONS = (
    replace(_C6, name="c6-no-stem", label="Ordbro without stemming", stem=False),
    replace(_C6, name="c6-no-compounds", label="Ordbro without compound split", compounds=False),
    replace(
        _C6, name="c6-no-prefix", label="Ordbro without metadata prefix", metadata_prefix=False
    ),
    replace(_C6, name="c6-bm25-only", label="Ordbro without vector route", routes=("bm25",)),
    replace(
        _C6,
        name="c6-ollama",
        label="Ordbro + nomic-embed-text",
        routes=("bm25", "subword", "ollama"),
    ),
)

PRESETS: dict[str, Preset] = {preset.name: preset for preset in LADDER + ABLATIONS}
PRESETS["legacy"] = replace(_C1, name="legacy")
PRESETS["ordbro"] = replace(_C6, name="ordbro", label="Ordbro")


def get_preset(name: str | Preset) -> Preset:
    if isinstance(name, Preset):
        return name
    try:
        return PRESETS[name]
    except KeyError:
        known = ", ".join(sorted(PRESETS))
        raise ValueError(f"unknown retrieval preset '{name}' (known: {known})") from None
