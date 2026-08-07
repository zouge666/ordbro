"""Error detection accuracy of the grammar checker on a labelled test set."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ordbro.evaluation.metrics import mean
from ordbro.grammar import GrammarChecker


def load_items(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def run(checker: GrammarChecker, items: list[dict[str, Any]]) -> dict[str, Any]:
    with_error = [item for item in items if item["errors"]]
    clean = [item for item in items if not item["errors"]]
    per_rule: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    misses, false_alarms = [], []
    detected = rule_hits = fixes = 0
    for item in with_error:
        gold = item["errors"][0]
        issues = checker.check(item["text"])
        stats = per_rule[gold["rule"]]
        stats["n"] += 1
        if issues:
            detected += 1
            stats["detected"] += 1
        matching = [i for i in issues if i.rule == gold["rule"]]
        if matching:
            rule_hits += 1
            stats["rule"] += 1
            if any(i.suggestion.lower() == gold["fix"].lower() for i in matching):
                fixes += 1
                stats["fix"] += 1
        else:
            misses.append(
                {"text": item["text"], "rule": gold["rule"], "found": [i.rule for i in issues]}
            )
    for item in clean:
        issues = checker.check(item["text"])
        if issues:
            false_alarms.append({"text": item["text"], "found": [i.rule for i in issues]})
    n_err, n_clean = len(with_error), len(clean)
    true_pos, false_pos = detected, len(false_alarms)
    precision = true_pos / (true_pos + false_pos) if true_pos + false_pos else 0.0
    recall = detected / n_err if n_err else 0.0
    return {
        "sentences": {"with_error": n_err, "correct": n_clean},
        "detection_recall": round(recall, 4),
        "detection_precision": round(precision, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall
        else 0.0,
        "rule_accuracy": round(rule_hits / n_err, 4) if n_err else 0.0,
        "fix_accuracy": round(fixes / n_err, 4) if n_err else 0.0,
        "false_alarm_rate": round(false_pos / n_clean, 4) if n_clean else 0.0,
        "per_rule": {rule: dict(values) for rule, values in sorted(per_rule.items())},
        "misses": misses,
        "false_alarms": false_alarms,
        "mean_issues_per_error_sentence": round(
            mean([len(checker.check(i["text"])) for i in with_error]), 3
        ),
    }
