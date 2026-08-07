import { api } from "../api.js";
import { h } from "../dom.js";

const pct = (v) => `${Math.round(v * 1000) / 10}%`;
const num = (v) => (typeof v === "number" ? v.toFixed(3) : "–");

export async function render(root) {
  const data = await api.lab();
  const r = data.results;
  root.append(h("div", { class: "page fade-in" },
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, "Lab"),
        h("h1", {}, "How well does it work?"),
        h("p", { class: "lede" }, "Results of the offline studies in eval/. Run ordbro eval to update them. The test sets are small and written for this project, so read the numbers as a first check, not as a final score."))),
    r.retrieval ? retrieval(r.retrieval) : missing("retrieval"),
    r.grammar ? grammar(r.grammar) : missing("grammar"),
    r.speech ? speech(r.speech) : missing("speech"),
    r.tutor ? tutor(r.tutor) : missing("tutor"),
    feedback(data.feedback, data.knowledge_base)));
}

function missing(name) {
  return h("section", { class: "card muted" }, `No ${name} results yet. Run: ordbro eval ${name}`);
}

function retrieval(res) {
  const ladder = res.presets.filter((p) => p.group === "ladder");
  const ablations = res.presets.filter((p) => p.group === "ablation");
  const ab = res.abstention.index_text;
  const c0 = res.presets.find((p) => p.name === "c0");
  const c6 = res.presets.find((p) => p.name === "c6");
  const types = Object.keys(res.by_type.c6 || {});
  return h("section", { class: "card stack" },
    h("div", { class: "card-head" }, h("h2", {}, "Retrieval from the Danish course notes"), h("span", { class: "pill plain" }, `${res.test_questions} test questions`)),
    h("div", { class: "kpis" },
      kpi(`${num(c0["recall@3"])} → ${num(c6["recall@3"])}`, "Recall@3, LinguaPilot → Ordbro"),
      kpi(`${num(c0["note@1"])} → ${num(c6["note@1"])}`, "Right note at rank 1"),
      kpi(`${num(c0["precision@1"])} → ${num(c6["precision@1"])}`, "Share of shown passage that answers"),
      kpi(pct(ab.unanswerable_abstained), "Unanswerable questions declined")),
    h("p", { class: "muted small" }, "Each step on the ladder changes one thing. c1n is LinguaPilot as it is configured, with nomic-embed-text through Ollama."),
    barChart(ladder.map((p) => ({ label: `${p.name} ${p.label}`, value: p["recall@3"], best: p.name === "c6" })), "Recall@3"),
    h("div", { class: "table-wrap" }, table(
      ["Preset", "R@1", "R@3", "R@5", "MRR", "nDCG@5", "Note@1", "P@1", "Chunks"],
      [...ladder, ...ablations].map((p) => ({ hl: p.name === "c6", cells: [`${p.name} · ${p.label}`, num(p["recall@1"]), num(p["recall@3"]), num(p["recall@5"]), num(p.mrr), num(p["ndcg@5"]), num(p["note@1"]), num(p["precision@1"]), String(p.chunks)] })))),
    h("h3", {}, "Recall@3 by question type"),
    h("div", { class: "table-wrap" }, table(
      ["Type", "n", "c0", "c1n", "c6"],
      types.map((t) => ({ cells: [t, String(res.by_type.c6[t].n), num(res.by_type.c0?.[t]?.["recall@3"]), num(res.by_type.c1n?.[t]?.["recall@3"]), num(res.by_type.c6[t]["recall@3"])] })))),
    h("h3", {}, "Saying \"I do not know\""),
    h("p", { class: "muted" }, `Threshold ${ab.threshold} (tuned on ${res.dev_questions} dev questions). ${pct(ab.answerable_answered)} of the answerable questions get an answer. Still answered although the notes do not cover it: ${ab.false_answers.join(" · ") || "none"}.`),
    h("h3", {}, "Where Ordbro still misses at rank 1"),
    h("ul", { class: "fail-list" }, (res.failures.c6 || []).slice(0, 8).map((f) =>
      h("li", {}, `${f.question} — first right passage at rank ${f.rank ?? "–"}${f.right_note ? " (right note, other section)" : ""}`))));
}

function grammar(g) {
  return h("section", { class: "card stack" },
    h("div", { class: "card-head" }, h("h2", {}, "Grammar feedback"), h("span", { class: "pill plain" }, `${g.sentences.with_error} with an error · ${g.sentences.correct} correct`)),
    h("div", { class: "kpis" },
      kpi(pct(g.detection_recall), "Mistakes found"),
      kpi(pct(g.detection_precision), "Flags that were right"),
      kpi(pct(g.fix_accuracy), "Right suggestion"),
      kpi(pct(g.false_alarm_rate), "False alarms on correct text")),
    h("div", { class: "table-wrap" }, table(["Rule", "n", "Found", "Right rule", "Right fix"],
      Object.entries(g.per_rule).map(([rule, s]) => ({ cells: [rule, String(s.n), String(s.detected || 0), String(s.rule || 0), String(s.fix || 0)] })))),
    g.misses.length ? h("p", { class: "muted small" }, `Missed: ${g.misses.map((m) => m.text).join(" · ")}`) : null);
}

function speech(sp) {
  const clean = sp.rows.filter((row) => row.lm_fix === 0);
  const lm = sp.rows.filter((row) => row.lm_fix > 0);
  return h("section", { class: "card stack" },
    h("div", { class: "card-head" }, h("h2", {}, "Speech feedback under recognition errors"), h("span", { class: "pill plain" }, "simulation")),
    h("p", { class: "muted" }, "A speaker says every word right, but the recognizer makes mistakes. Every flagged word is then a false alarm. Using the best of three alternatives removes most of them."),
    lineChart(clean),
    h("div", { class: "legend" }, h("span", { style: { "--swatch": "var(--clay)" } }, "first transcript only"), h("span", { style: { "--swatch": "var(--fjord)" } }, "best of 3 alternatives")),
    h("div", { class: "table-wrap" }, table(["Noise", "n-best", "False flags / word", "Real mistake found (recognizer may auto-correct)"],
      lm.map((row) => ({ cells: [pct(row.rate), String(row.n_best), pct(row.false_flags_per_word), pct(row.mistake_found)] })))),
    h("p", { class: "muted small" }, "The price: when the recognizer sometimes auto-corrects a learner's mistake to the expected word, the best alternative can hide the mistake. Ordbro accepts this trade-off because a wrong warning discourages a learner who spoke well."));
}

function tutor(t) {
  const names = { adaptive: "Adaptive (Ordbro)", fixed: "Book order", random: "Random" };
  const rows = Object.entries(t.policies);
  return h("section", { class: "card stack" },
    h("div", { class: "card-head" }, h("h2", {}, "Adaptive tutoring"), h("span", { class: "pill plain" }, `${t.learners} simulated learners · ${t.steps} items`)),
    barChart(rows.map(([name, d]) => ({ label: names[name], value: d.all.skills_known / t.skills, text: `${d.all.skills_known} skills`, best: name === "adaptive" })), "Skills known at the end (share of 18)"),
    h("div", { class: "table-wrap" }, table(["Policy", "Known, fast", "Known, slow", "Reached 10 skills, slow", "Practice on known skills"],
      rows.map(([name, d]) => ({ hl: name === "adaptive", cells: [names[name], d.fast.skills_known.toFixed(2), d.slow.skills_known.toFixed(2), pct(d.slow.reached_10_share), pct(d.all.wasted_share)] })))),
    h("p", { class: "muted small" }, "Assumed learning rates and slips. The adaptive tutor keeps practicing until it has evidence, so it spends a bit more time on skills that are already learned, but it unlocks skills in a better order."));
}

function feedback(fb, kb) {
  return h("section", { class: "card stack" },
    h("div", { class: "card-head" }, h("h2", {}, "Learner feedback on this computer"), h("span", { class: "pill plain" }, `${fb.total} ratings`)),
    fb.suggestions.length ? h("ul", { class: "fail-list" }, fb.suggestions.map((s) => h("li", {}, s))) : h("p", { class: "muted" }, "No suggestions yet. Ratings from the practice and ask pages show up here."),
    h("p", { class: "faint small" }, `Knowledge base: ${kb.documents} documents, ${kb.chunks} chunks, preset ${kb.preset} (${kb.routes.join(" + ")}), ${kb.glossary_entries} glossary entries.`));
}

function kpi(value, label) {
  return h("div", { class: "kpi" }, h("div", { class: "value" }, value), h("div", { class: "label" }, label));
}

function table(head, rows) {
  return h("table", { class: "data-table" },
    h("thead", {}, h("tr", {}, head.map((cell) => h("th", {}, cell)))),
    h("tbody", {}, rows.map((row) => h("tr", { class: row.hl ? "hl" : "" }, row.cells.map((cell) => h("td", {}, cell))))));
}

function barChart(items, title) {
  const width = 640;
  const rowH = 26;
  const labelW = 230;
  const height = items.length * rowH + 28;
  const bars = items.map((item, i) => {
    const y = 18 + i * rowH;
    const w = Math.max(2, (width - labelW - 60) * Math.min(1, item.value));
    return `<text x="0" y="${y + 13}">${escape(item.label)}</text>
      <rect class="bar ${item.best ? "best" : ""}" x="${labelW}" y="${y}" width="${w}" height="16" rx="4"/>
      <text x="${labelW + w + 6}" y="${y + 13}">${escape(item.text || item.value.toFixed(3))}</text>`;
  }).join("");
  const wrap = h("div", {});
  wrap.innerHTML = `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(title)}"><text x="0" y="10">${escape(title)}</text>${bars}</svg>`;
  return wrap.firstElementChild;
}

function lineChart(rows) {
  const width = 640;
  const height = 220;
  const pad = { l: 44, r: 16, t: 14, b: 34 };
  const rates = [...new Set(rows.map((r) => r.rate))];
  const maxY = Math.max(0.05, ...rows.map((r) => r.false_flags_per_word));
  const x = (rate) => pad.l + ((width - pad.l - pad.r) * rates.indexOf(rate)) / (rates.length - 1);
  const y = (v) => height - pad.b - ((height - pad.t - pad.b) * v) / maxY;
  const line = (n) => rows.filter((r) => r.n_best === n).map((r) => `${x(r.rate)},${y(r.false_flags_per_word)}`).join(" ");
  const grid = [0, 0.5, 1].map((f) => `<line class="grid" x1="${pad.l}" x2="${width - pad.r}" y1="${y(maxY * f)}" y2="${y(maxY * f)}"/><text x="4" y="${y(maxY * f) + 4}">${Math.round(maxY * f * 100)}%</text>`).join("");
  const ticks = rates.map((rate) => `<text x="${x(rate) - 10}" y="${height - 12}">${Math.round(rate * 100)}%</text>`).join("");
  const wrap = h("div", {});
  wrap.innerHTML = `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="False flags by recognition noise">
    ${grid}${ticks}<text x="${width / 2 - 60}" y="${height - 1}">recognition noise per word</text>
    <polyline class="line one" points="${line(1)}"/><polyline class="line three" points="${line(3)}"/></svg>`;
  return wrap.firstElementChild;
}

function escape(text) {
  return String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}
