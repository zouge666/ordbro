import { api } from "../api.js";
import { h, icon, loading } from "../dom.js";
import { highlight } from "../lib/format.js";

const EXAMPLES = [
  "When does the verb come before the subject?",
  "What is the past tense of gå?",
  "What does halv fire mean?",
  "Hvornår bruger man sin og hans?",
  "How do I make the plural of barn?",
  "Why is the h silent in hvad?",
];

export async function render(root, params) {
  const input = h("input", { class: "input", type: "search", placeholder: "Ask about Danish, in English or Danish", "aria-label": "Your question", maxlength: "300" });
  const output = h("div", { class: "stack" });
  const go = () => ask(input.value);

  root.append(h("div", { class: "page fade-in" },
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, "Ask"),
        h("h1", {}, "Ask your course notes"),
        h("p", { class: "lede" }, "Answers come from your school's notes, with the source. If the notes do not cover it, Ordbro says so instead of guessing."))),
    h("form", { class: "ask-box", onsubmit: (event) => { event.preventDefault(); go(); } },
      input, h("button", { class: "btn primary", type: "submit" }, icon("search"), "Ask")),
    h("div", { class: "examples" }, EXAMPLES.map((text) =>
      h("button", { type: "button", onclick: () => { input.value = text; go(); } }, text))),
    output));

  async function ask(question) {
    if (!question.trim()) return;
    history.replaceState(null, "", `#/ask?q=${encodeURIComponent(question)}`);
    output.replaceChildren(loading());
    const data = await api.ask(question);
    output.replaceChildren(...answerView(data));
  }

  const first = params.get("q");
  if (first) { input.value = first; await ask(first); }
}

function answerView(data) {
  const terms = data.terms || [];
  const nodes = [];
  if (data.abstained) {
    nodes.push(h("section", { class: "card notice amber" },
      h("div", { class: "feedback-title" }, icon("hint"), "I could not find this in your course notes."),
      h("p", {}, "Try other words, ask in Danish, or ask your teacher. The closest passages are listed below."),
      h("p", { class: "faint small" }, `Confidence ${data.confidence.toFixed(2)}`)));
  } else {
    const src = data.source;
    nodes.push(h("section", { class: "card stack" },
      h("div", { class: "source-head" }, icon("book"), h("strong", {}, `${src.title} › ${src.heading}`), h("span", { class: "pill plain" }, src.level), h("span", { class: "spacer" }), h("span", { class: "faint" }, `confidence ${data.confidence.toFixed(2)}`)),
      data.mode === "llm" ? h("p", {}, data.text) : null,
      h("div", { class: "answer-lines", lang: "da" }, data.lines.map((line) => h("p", {}, marked(line, terms)))),
      data.summary_en ? h("p", { class: "muted", "data-english": "" }, data.summary_en) : null,
      helpful(data.question)));
  }
  if (data.word_cards?.length) {
    nodes.push(h("section", { class: "card" },
      h("h2", { style: { marginBottom: "0.8rem" } }, "Words in your question"),
      h("div", { class: "word-cards" }, data.word_cards.map(wordCard))));
  }
  nodes.push(h("section", { class: "card" },
    h("div", { class: "card-head" }, h("h2", {}, "Passages"), h("span", { class: "faint small" }, "ranked by RRF fusion of BM25 and subword vectors")),
    h("div", {}, data.passages.map((p, i) => passage(p, i, terms))),
    trace(data)));
  return nodes;
}

function marked(text, terms) {
  return highlight(text, terms).map(([part, hit]) => (hit ? h("mark", {}, part) : part));
}

function passage(p, index, terms) {
  const routes = Object.entries(p.ranks).map(([route, rank]) => `${route} #${rank}`).join(" · ");
  return h("div", { class: "passage" },
    h("div", { class: "row" }, h("strong", {}, `${index + 1}. ${p.title} › ${p.heading}`), h("span", { class: "pill plain" }, p.level), h("span", { class: "spacer" }), h("span", { class: "route" }, routes)),
    h("div", { class: "text", lang: "da" }, marked(p.text.replace(/^#+ .*\n?/gm, "").trim(), terms)));
}

function trace(data) {
  const rows = data.trace.stages.map((stage) => {
    const d = stage.details;
    let info = "";
    if (stage.stage === "analyze") info = `terms: ${d.terms.join(", ")}${d.expansions.length ? ` · glossary: ${d.expansions.join(", ")} → ${d.added.join(", ")}` : ""}`;
    else if (d.candidates) info = d.candidates.map((c) => `${c.chunk_id} (${c.score})`).join(", ");
    else if (d.results) info = d.results.map((c) => `${c.chunk_id} (${c.score})`).join(", ");
    else if (stage.stage === "confidence") info = String(d.value);
    return h("tr", {}, h("td", {}, stage.stage), h("td", { class: "mono" }, `${stage.ms.toFixed(2)} ms`), h("td", { class: "mono" }, info));
  });
  return h("details", { class: "trace" },
    h("summary", {}, `How I found this (${data.trace.total_ms.toFixed(1)} ms)`),
    h("table", { class: "trace-table" }, h("thead", {}, h("tr", {}, h("th", {}, "Stage"), h("th", {}, "Time"), h("th", {}, "Details"))), h("tbody", {}, rows)));
}

function wordCard(card) {
  const forms = card.pos === "noun"
    ? [card.gender && `${card.gender} ${card.da}`, card.definite, card.plural, card.plural_definite]
    : card.pos === "verb" ? [`at ${card.da}`, card.present, card.past, `${card.aux} ${card.perfect}`]
      : [card.da, card.t_form, card.plural, card.comparative, card.superlative];
  return h("div", { class: "word-mini" },
    h("div", { class: "w", lang: "da" }, card.da), h("div", { class: "muted small" }, card.en),
    h("div", { class: "small da", style: { marginTop: "0.35rem" } }, forms.filter(Boolean).join(" · ")));
}

function helpful(question) {
  const box = h("div", { class: "rate" }, h("span", {}, "Did this answer your question?"));
  for (const [value, text] of [[true, "Yes"], [false, "No"]]) {
    box.append(h("button", {
      class: "chip", type: "button", "aria-pressed": "false",
      onclick: async (event) => {
        for (const chip of box.querySelectorAll(".chip")) chip.setAttribute("aria-pressed", "false");
        event.currentTarget.setAttribute("aria-pressed", "true");
        try { await api.feedback({ kind: "ask", target_id: question.slice(0, 300), helpful: value, comment: question }); } catch { /* optional */ }
      },
    }, text));
  }
  return box;
}
