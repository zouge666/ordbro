import { api } from "../api.js";
import { h, icon, loading } from "../dom.js";
import { insertLetter } from "../lib/format.js";

const EXAMPLE = "Jeg hedder Omar. I dag jeg går på arbejde. Jeg har en hus og to stor biler. Jeg kan taler lidt dansk, fordi jeg har ikke tid til at øve.";

const RULE_NAMES = {
  "capital-noun": "Small letter",
  "capital-word": "Small letter",
  "article-gender": "En or et",
  "adjective-agreement": "Adjective ending",
  "double-definite": "Definite form",
  "modal-infinitive": "Infinitive",
  "present-r": "Present tense",
  "v2-inversion": "Word order",
  "negation-placement": "Place of ikke",
  "past-irregular": "Past tense",
  "english-word": "English word",
};

export async function render(root) {
  const text = h("textarea", { class: "textarea", lang: "da", spellcheck: "false", placeholder: "Skriv et par sætninger på dansk ...", "aria-label": "Your Danish text", maxlength: "2000" });
  const output = h("div", { class: "stack" });

  root.append(h("div", { class: "page fade-in" },
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, "Write"),
        h("h1", {}, "Check your Danish"),
        h("p", { class: "lede" }, "Write a few sentences. Ordbro looks for common beginner mistakes and links each one to the rule in your course notes."))),
    h("section", { class: "card stack" },
      text,
      h("div", { class: "row" },
        h("div", { class: "letters" }, ["æ", "ø", "å"].map((letter) => h("button", {
          type: "button", "aria-label": `Type ${letter}`,
          onclick: () => {
            const { value, caret } = insertLetter(text.value, text.selectionStart, text.selectionEnd, letter);
            text.value = value; text.focus(); text.setSelectionRange(caret, caret);
          },
        }, letter))),
        h("span", { class: "spacer" }),
        h("button", { class: "btn ghost", type: "button", onclick: () => { text.value = EXAMPLE; check(); } }, "Try an example"),
        h("button", { class: "btn primary", type: "button", onclick: () => check() }, icon("check"), "Check"))),
    output));

  async function check() {
    if (!text.value.trim()) return;
    output.replaceChildren(loading());
    const data = await api.check(text.value);
    output.replaceChildren(...resultView(data));
  }
}

function resultView(data) {
  if (!data.issues.length) {
    return [h("section", { class: "card notice moss" },
      h("div", { class: "feedback-title" }, icon("check"), "I found no common mistakes."),
      h("p", { class: "muted" }, "This checker only knows some typical beginner mistakes, so a teacher may still find something."))];
  }
  return [
    h("section", { class: "card stack" },
      h("div", { class: "card-head" }, h("h2", {}, `${data.issues.length} thing${data.issues.length === 1 ? "" : "s"} to look at`)),
      h("p", { class: "marked", lang: "da" }, markText(data.text, data.issues)),
      h("div", {}, data.issues.map(issueRow))),
    h("section", { class: "card stack" },
      h("h2", {}, "Suggested text"),
      h("p", { class: "marked", lang: "da" }, data.corrected),
      h("p", { class: "faint small" }, "Read it out loud. Does it sound right to you?")),
  ];
}

function markText(text, issues) {
  const parts = [];
  let at = 0;
  issues.forEach((issue, i) => {
    if (issue.start < at) return;
    parts.push(text.slice(at, issue.start));
    parts.push(h("span", { class: "err", title: issue.message }, text.slice(issue.start, issue.end), h("sup", {}, String(i + 1))));
    at = issue.end;
  });
  parts.push(text.slice(at));
  return parts;
}

function issueRow(issue, index) {
  const noteBox = h("div", { class: "note-box" });
  return h("div", { class: "issue" },
    h("span", { class: "issue-num" }, String(index + 1)),
    h("div", { class: "stack", style: { gap: "0.3rem", flex: "1" } },
      h("div", { class: "row" }, h("strong", {}, RULE_NAMES[issue.rule] || issue.rule),
        issue.skill_name && issue.skill_name !== RULE_NAMES[issue.rule] ? h("span", { class: "pill plain" }, issue.skill_name) : null),
      h("p", { class: "change", lang: "da" }, h("del", {}, issue.original), "  →  ", h("ins", {}, issue.suggestion)),
      h("p", { class: "muted" }, issue.message),
      issue.note ? h("button", { class: "btn ghost small", type: "button", style: { alignSelf: "flex-start" }, onclick: () => openNote(issue.note, noteBox) }, icon("book"), "Read the rule") : null,
      noteBox));
}

async function openNote(docId, box) {
  if (box.childElementCount) { box.replaceChildren(); return; }
  const note = await api.note(docId);
  box.replaceChildren(h("div", { class: "source" },
    h("div", { class: "source-head" }, icon("book"), h("strong", {}, note.title), h("span", { class: "pill plain" }, note.level)),
    ...note.sections.map((s) => h("div", { class: "stack", style: { gap: "0.2rem", marginBottom: "0.6rem" } },
      h("strong", { class: "small" }, s.heading),
      h("div", { class: "source-text", lang: "da" }, s.text.replace(/^#+ .*\n?/gm, "").trim())))));
}
