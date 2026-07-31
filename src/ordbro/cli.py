"""Command line interface: ``ordbro serve``, ``ordbro ask`` and more."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from ordbro.config import load_settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ordbro", description="Ordbro, a Danish learning assistant."
    )
    parser.add_argument("--config", help="path to a settings file")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="start the web app")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--reload", action="store_true")

    ask = sub.add_parser("ask", help="ask the course notes a question")
    ask.add_argument("question")
    ask.add_argument("--preset", help="retrieval preset, for example c0 or ordbro")
    ask.add_argument("--top-k", type=int, default=3)
    ask.add_argument("--trace", action="store_true", help="print the query trace")

    check = sub.add_parser("check", help="check a Danish sentence")
    check.add_argument("text")

    kb = sub.add_parser("kb", help="show knowledge base statistics")
    kb.add_argument("--preset")

    args = parser.parse_args(argv)
    settings = load_settings(args.config)

    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "ordbro.api.app:create_app",
            factory=True,
            host=args.host or settings.app.host,
            port=args.port or settings.app.port,
            reload=args.reload,
        )
        return 0

    if args.command in {"ask", "kb"}:
        from ordbro.content import load_content
        from ordbro.rag import Answerer, KnowledgeBase

        content = load_content(settings.data_path)
        preset = getattr(args, "preset", None) or settings.rag.preset
        kb_obj = KnowledgeBase(content.documents, preset, glossary=content.glossary)
        if args.command == "kb":
            _print(kb_obj.stats())
            return 0
        answer = Answerer(kb_obj, settings.rag.abstain_below).answer(args.question, args.top_k)
        if answer.abstained:
            print(f"No good answer in the notes (confidence {answer.confidence:.2f}).")
        else:
            print(f"{answer.source['title']} > {answer.source['heading']}")
            print("\n".join(f"  {line}" for line in answer.lines))
        for hit in answer.hits:
            print(f"- {hit.chunk.id:22} {hit.score:.4f}  {hit.ranks}")
        if args.trace:
            _print(answer.trace)
        return 0

    if args.command == "check":
        from ordbro.service import Ordbro

        result = Ordbro(settings).check_text(args.text)
        for issue in result["issues"]:
            change = f"'{issue['original']}' -> '{issue['suggestion']}'"
            print(f"[{issue['rule']}] {change}: {issue['message']}")
        print(result["corrected"])
        return 0
    return 1


def _print(data: object) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    raise SystemExit(main())
