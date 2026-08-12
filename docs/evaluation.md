# Evaluation

```bash
ordbro eval all          # or: retrieval, grammar, speech, tutor
ordbro eval --no-ollama  # skip the presets that need a local Ollama server
```

Results are written to `eval/results/*.json` and shown on the Lab page.
All test data was written for this project. The sets are small, so differences of a few points are not meaningful.

## Retrieval

`eval/retrieval_test.jsonl` has 73 learner-style questions (61 answerable, 12 not covered by the notes).
Each answerable question has one or more gold sections. A retrieved chunk is relevant when it overlaps a gold
section. `eval/retrieval_dev.jsonl` (16 questions) is used only to choose the abstention threshold.

| Preset | What changes | R@1 | R@3 | R@5 | MRR | nDCG@5 | Right note @1 | P@1 | Chunks |
|---|---|---|---|---|---|---|---|---|---|
| `c0` | LinguaPilot, sparse only | 0.361 | 0.557 | 0.607 | 0.457 | 0.486 | 0.377 | 0.127 | 30 |
| `c1` | LinguaPilot, hash fallback | 0.213 | 0.426 | 0.574 | 0.361 | 0.374 | 0.213 | 0.073 | 30 |
| `c1n` | LinguaPilot, nomic-embed-text | 0.475 | 0.672 | 0.754 | 0.594 | 0.615 | 0.492 | 0.188 | 30 |
| `c2` | + Danish analyzer | 0.541 | 0.705 | 0.770 | 0.627 | 0.647 | 0.557 | 0.190 | 30 |
| `c3` | + section chunks | 0.344 | 0.574 | 0.672 | 0.479 | 0.500 | 0.525 | 0.344 | 97 |
| `c4` | + metadata prefix | 0.443 | 0.754 | 0.885 | 0.612 | 0.663 | 0.754 | 0.443 | 97 |
| `c5` | + subword vectors | 0.459 | 0.787 | 0.885 | 0.622 | 0.675 | 0.787 | 0.459 | 97 |
| `c6` | + glossary expansion | 0.541 | 0.853 | 0.918 | 0.688 | 0.728 | 0.853 | 0.541 | 97 |
| `c6-no-stem` | Ordbro without stemming | 0.574 | 0.803 | 0.902 | 0.704 | 0.738 | 0.869 | 0.574 | 97 |
| `c6-no-compounds` | Ordbro without compound split | 0.525 | 0.885 | 0.918 | 0.689 | 0.724 | 0.853 | 0.525 | 97 |
| `c6-no-prefix` | Ordbro without metadata prefix | 0.443 | 0.738 | 0.836 | 0.609 | 0.613 | 0.689 | 0.443 | 97 |
| `c6-bm25-only` | Ordbro without vector route | 0.541 | 0.836 | 0.918 | 0.693 | 0.735 | 0.836 | 0.541 | 97 |
| `c6-ollama` | Ordbro + nomic-embed-text | 0.557 | 0.820 | 0.885 | 0.700 | 0.722 | 0.853 | 0.557 | 97 |

P@1 is the share of the first passage that lies inside a gold section. It matters because the 800 character
chunks of `c0` to `c2` cover several sections. They count as relevant more easily, but the learner then reads
mostly other text (P@1 0.13 for `c0`).

Recall@3 by question type:

| Type | n | `c0` | `c1n` | `c6` |
|---|---|---|---|---|
| rule question in English | 15 | 0.200 | 0.400 | 0.933 |
| rule question in Danish | 10 | 1.000 | 1.000 | 0.900 |
| word form | 12 | 0.667 | 0.833 | 1.000 |
| example request | 8 | 0.750 | 0.750 | 1.000 |
| Danish typed without æ ø å | 8 | 0.750 | 0.875 | 0.625 |
| English words not in the glossary | 8 | 0.125 | 0.250 | 0.500 |

**Parity check.** On all 89 questions, preset `c0` gives the same top-10 ranking as the BM25 code of
linguapilot-rag-infrastructure run on the same chunks.

**Saying "I do not know".** The confidence is the subword cosine between the query and the best passages.
With the confidence computed on the indexed text (with the English summary), the threshold chosen on the dev
set is 0.095. On the test set 96.7 % of the answerable questions get an answer and 58.3 % (7 of 12) of the
uncovered questions are declined. With the confidence on the plain passage text, 13 answerable questions were
declined instead of 2.

**Known weak spots**

* Questions close to a topic in the notes but not answered by it get a wrong answer: the future perfect,
  noun cases, the s-passive, Finnish verbs.
* Danish typed with o for ø ("blodt") is not fixed; only ae, oe and aa are.
* Danish questions lose a little at rank 1, because a section chunk holds fewer words than an 800 character
  chunk.
* The right note but a neighbouring section is the most common miss.

## Grammar feedback

`eval/grammar_test.jsonl` has 56 sentences with one typical mistake and 40 correct sentences.

| | Value |
|---|---|
| Mistakes found | 94.6 % (53 of 56) |
| Flags that were right | 100 % |
| Right rule and right suggestion | 94.6 % |
| False alarms on correct sentences | 0 % |

The three misses show the limits of the rules: a verb that is not in the vocabulary ("ryger"), a fronted
phrase that is not in the list ("Efter skolen jeg spiser") and a noun subject in a subordinate clause
("at Peter kommer ikke"). The same person wrote the rules and the test sentences, so these numbers are
optimistic. Real learner texts with several mistakes per sentence will be harder.

## Speech feedback (simulation)

There is no recorded learner speech in this project. The study simulates a recognizer that changes each word
with probability *noise*: a near miss ("hedder" to "heder"), a dropped word or another word.

| Noise | Alternatives | Words wrongly flagged (correct speaker) | Real mistake found, recognizer may auto-correct |
|---|---|---|---|
| 5 % | 1 | 5.0 % | 75.8 % |
| 5 % | 3 | 0.2 % | 49.4 % |
| 10 % | 1 | 9.8 % | 75.4 % |
| 10 % | 3 | 1.4 % | 53.7 % |
| 20 % | 1 | 20.3 % | 80.0 % |
| 20 % | 3 | 5.8 % | 61.5 % |

Using the best of three alternatives removes most false warnings. The price shows up when the recognizer's
language model sometimes "hears" the word the learner meant (25 % in the study): the best alternative then
hides more real mistakes. Ordbro uses the alternatives, shows the transcript, and does not grade with the score.

## Tutoring policy (simulation)

300 simulated learners (half fast, half slow, 30 % already know some A1 skills), 60 items each.

| Policy | Skills known | Fast learners | Slow learners | Slow learners with 10 skills | Practice on known skills |
|---|---|---|---|---|---|
| Adaptive (Ordbro) | 9.30 | 12.05 | 6.56 | 12.0 % | 30.4 % |
| Book order | 8.09 | 10.73 | 5.45 | 8.0 % | 28.8 % |
| Random | 7.22 | 9.47 | 4.97 | 5.3 % | 24.1 % |

The adaptive policy helps both groups, but it does not close the gap between them. It also spends a little more
time on skills that are already learned, because it waits for evidence before it moves on. The learning rates are
assumptions, so this shows how the policy behaves, not how much real learners would gain.
