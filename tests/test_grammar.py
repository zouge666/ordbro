import pytest

from ordbro.config import load_settings
from ordbro.content import load_content
from ordbro.grammar import GrammarChecker, apply_suggestions


@pytest.fixture(scope="module")
def checker():
    return GrammarChecker(load_content(load_settings().data_path).lexicon)


@pytest.mark.parametrize(
    ("text", "rule", "fixed"),
    [
        ("Jeg har en Hund.", "capital-noun", "Jeg har en hund."),
        ("Vi ses på Mandag.", "capital-word", "Vi ses på mandag."),
        ("Vi bor i en hus.", "article-gender", "Vi bor i et hus."),
        ("Det er et stor hus.", "adjective-agreement", "Det er et stort hus."),
        ("Jeg har to stor biler.", "adjective-agreement", "Jeg har to store biler."),
        ("Den bilen er rød.", "double-definite", "Bilen er rød."),
        ("Jeg kan taler dansk.", "modal-infinitive", "Jeg kan tale dansk."),
        (
            "Jeg kan godt lide at spiser fisk.",
            "modal-infinitive",
            "Jeg kan godt lide at spise fisk.",
        ),
        ("Jeg spise morgenmad.", "present-r", "Jeg spiser morgenmad."),
        ("I dag jeg går i skole.", "v2-inversion", "I dag går jeg i skole."),
        ("Når jeg kommer hjem, jeg spiser.", "v2-inversion", "Når jeg kommer hjem, spiser jeg."),
        (
            "Jeg bliver hjemme, fordi jeg har ikke tid.",
            "negation-placement",
            "Jeg bliver hjemme, fordi jeg ikke har tid.",
        ),
        ("I går gåede jeg til arbejde.", "past-irregular", "I går gik jeg til arbejde."),
        ("Jeg har en bil and en cykel.", "english-word", "Jeg har en bil og en cykel."),
    ],
)
def test_rule_finds_and_fixes(checker, text, rule, fixed):
    issues = checker.check(text)
    assert rule in {issue.rule for issue in issues}, issues
    target = [issue for issue in issues if issue.rule == rule]
    assert apply_suggestions(text, target) == fixed


@pytest.mark.parametrize(
    "text",
    [
        "Jeg hedder Anna, og jeg bor i Brøndby.",
        "I dag går jeg i skole.",
        "Kan du hjælpe mig?",
        "Når jeg kommer hjem, spiser jeg.",
        "Jeg bliver hjemme, fordi jeg ikke har tid.",
        "Han har et stort hus og to små biler.",
        "Den store bil er rød.",
        "Jeg vil gerne have en kop kaffe.",
        "Hvor bor I?",
        "Peter kysser sin kone.",
        "I går spiste vi fisk.",
    ],
)
def test_correct_sentences_give_no_issues(checker, text):
    assert checker.check(text) == []


def test_issue_links_to_a_skill(checker):
    issue = checker.check("Vi bor i en hus.")[0]
    assert issue.skill == "noun_gender"
    assert issue.original == "en" and issue.suggestion == "et"
