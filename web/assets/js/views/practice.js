import { api } from "../api.js";
import { announce, fill, h, icon, loading, meter } from "../dom.js";
import { insertLetter, percent, splitGap } from "../lib/format.js";
import { canSpeak, speak } from "../speech.js";

const REASONS = {
  adaptive: "Chosen for you: not too easy and not too hard.",
  "words due for review": "These words are due for review.",
  "new words": "A new word for your review list.",
  "chosen skill": "You chose this skill.",
  review: "Word review with spaced repetition.",
  "all skills mastered": "All skills are mastered. Time to review words.",
};

export async function render(root, params) {
  const learner = await api.learner();
  let focus = params.get("focus") || "";
  let exercise = null;
  let attempt = 1;
  let built = [];
  let locked = false;
  let onKey = null;

  const title = h("h1", {}, "Practice");
  const reason = h("p", { class: "lede" });
  const masteryBox = h("div", { class: "practice-top" });
  const body = h("div", {});
  const select = h("select", { class: "select", "aria-label": "What to practice" },
    h("option", { value: "" }, "Mixed practice"),
    h("option", { value: "review" }, "Review words"),
    learner.skills.map((s) => h("option", { value: s.id }, `${s.name} (${s.level})`)));
  select.value = focus;
  select.addEventListener("change", () => {
    focus = select.value;
    history.replaceState(null, "", focus ? `#/practice?focus=${focus}` : "#/practice");
    load();
  });

  root.append(h("div", { class: "page fade-in" },
    h("div", { class: "page-head" },
      h("div", {}, h("p", { class: "eyebrow" }, "Practice"), title, reason),
      select),
    masteryBox,
    body));

  async function load() {
    fill(body, loading());
    const data = await api.next(focus || null);
    exercise = data.exercise;
    attempt = 1;
    built = [];
    locked = false;
    reason.textContent = REASONS[data.reason] || "";
    if (!exercise) {
      title.textContent = "Nothing to practice";
      fill(masteryBox);
      fill(body, h("div", { class: "card empty" }, "You have seen every word. Come back later for reviews."));
      return;
    }
    title.textContent = data.skill ? data.skill.name : "Word review";
    showMastery(data.skill ? data.skill.mastery : null, data.skill?.name_da);
    fill(body, card());
  }

  function showMastery(value, nameDa) {
    if (value === null || value === undefined) {
      fill(masteryBox, h("span", { class: "pill" }, "Spaced repetition"));
      return;
    }
    fill(masteryBox, 
      nameDa ? h("span", { class: "pill plain da" }, nameDa) : null,
      h("span", { class: "muted small" }, "Mastery"),
      meter(value),
      h("span", { class: "small" }, percent(value)));
  }

  function card() {
    const feedback = h("div", { class: "feedback", "aria-live": "polite" });
    const inline = !exercise.text && exercise.prompt.includes("___");
    const sentence = exercise.text || (inline ? exercise.prompt : "");
    const parts = [
      h("p", { class: "prompt" }, inline ? "Choose the right answer." : exercise.prompt),
      sentence ? target(sentence) : null,
    ];
    let input = null;
    if (exercise.options.length) {
      parts.push(h("div", { class: "options", role: "group", "aria-label": "Answers" },
        exercise.options.map((option, index) =>
          h("button", { class: "option", type: "button", "data-value": option, onclick: () => submit(option) },
            h("span", { class: "key" }, String(index + 1)),
            h("span", { class: "label" }, option)))));
    } else if (exercise.type === "order") {
      parts.push(orderInput());
    } else {
      input = h("input", { class: "input", type: "text", autocomplete: "off", autocapitalize: "off", spellcheck: "false", lang: "da", "aria-label": "Your answer" });
      parts.push(h("div", { class: "stack" },
        h("div", { class: "answer-row" }, input,
          h("button", { class: "btn primary", type: "button", onclick: () => submit(input.value) }, "Check")),
        letters(input)));
    }
    const controls = h("div", { class: "row" },
      exercise.type === "flashcard" && canSpeak()
        ? h("button", { class: "btn ghost small", type: "button", onclick: () => speak(exercise.speak) }, icon("listen"), "Listen")
        : null,
      h("span", { class: "spacer" }),
      h("span", { class: "kbd-hint" }, exercise.options.length ? "Press 1 to " + exercise.options.length : "Press ", exercise.options.length ? "" : h("kbd", {}, "Enter"), exercise.options.length ? "" : " to check"));
    const node = h("section", { class: "card practice-card fade-in" }, parts, controls, feedback);

    onKey && document.removeEventListener("keydown", onKey);
    onKey = (event) => {
      if (event.target instanceof HTMLSelectElement) return;
      if (locked && event.key === "Enter") { event.preventDefault(); load(); return; }
      if (locked) return;
      if (exercise.options.length && /^[1-9]$/.test(event.key)) {
        const option = exercise.options[Number(event.key) - 1];
        if (option) submit(option);
      } else if (event.key === "Enter" && input && document.activeElement === input) {
        submit(input.value);
      } else if (event.key === "Enter" && exercise.type === "order" && built.length) {
        submit(built.join(" "));
      }
    };
    document.addEventListener("keydown", onKey);
    window.setTimeout(() => input?.focus(), 0);
    node.feedback = feedback;
    node.input = input;
    return node;
  }

  function target(text) {
    const [before, gap, after] = splitGap(text);
    if (gap === undefined) return h("p", { class: "target", lang: "da" }, before);
    return h("p", { class: "target", lang: "da" }, before, h("span", { class: "gap" }, " "), after);
  }

  function letters(input) {
    return h("div", { class: "letters", "aria-label": "Danish letters" },
      ["æ", "ø", "å"].map((letter) => h("button", {
        type: "button",
        "aria-label": `Type ${letter}`,
        onclick: () => {
          const { value, caret } = insertLetter(input.value, input.selectionStart ?? input.value.length, input.selectionEnd ?? input.value.length, letter);
          input.value = value;
          input.focus();
          input.setSelectionRange(caret, caret);
        },
      }, letter)));
  }

  function orderInput() {
    const tokens = shuffled(exercise.tokens, exercise.id);
    const pool = h("div", { class: "tokens" });
    const line = h("div", { class: "built tokens", "aria-label": "Your sentence" });
    const draw = () => {
      fill(line, ...built.map((word, index) =>
        h("button", { class: "token", type: "button", onclick: () => { if (!locked) { built.splice(index, 1); draw(); } } }, word)));
      const counts = {};
      for (const word of built) counts[word] = (counts[word] || 0) + 1;
      fill(pool, ...tokens.map((word) => {
        const used = (counts[word] || 0) > 0;
        if (used) counts[word] -= 1;
        return h("button", { class: `token${used ? " used" : ""}`, type: "button", disabled: used || locked, onclick: () => { built.push(word); draw(); } }, word);
      }));
    };
    draw();
    return h("div", { class: "stack" }, line, pool,
      h("div", { class: "row" },
        h("button", { class: "btn primary", type: "button", onclick: () => built.length && submit(built.join(" ")) }, "Check"),
        h("button", { class: "btn ghost", type: "button", onclick: () => { if (!locked) { built = []; draw(); } } }, icon("redo"), "Start again")));
  }

  async function submit(answer) {
    if (locked || !exercise) return;
    const node = body.querySelector(".practice-card");
    for (const button of node.querySelectorAll(".option")) button.classList.toggle("picked", button.dataset.value === answer);
    const result = await api.answer(exercise.id, answer, attempt);
    if (result.mastery_after !== null && result.mastery_after !== undefined && result.correct) {
      showMastery(result.mastery_after, null);
    }
    showFeedback(node, result, answer);
  }

  function showFeedback(node, result, answer) {
    const box = node.querySelector(".feedback");
    const tone = result.correct ? "moss" : result.final ? "clay" : "amber";
    const symbol = result.correct ? "check" : result.final ? "cross" : "hint";
    box.className = `feedback notice ${tone} fade-in`;
    fill(box, 
      h("div", { class: "feedback-title" }, icon(symbol), result.message),
      result.note ? h("p", {}, result.note) : null,
      result.hint ? h("p", {}, result.hint) : null,
      result.answer ? h("p", { class: "answer-shown", lang: "da" }, result.answer) : null,
      result.explanation ? h("p", { class: "muted" }, result.explanation) : null,
      result.source ? source(result.source) : null);
    announce(`${result.message} ${result.hint || ""} ${result.answer || ""}`);

    if (!result.final) {
      attempt = 2;
      for (const button of node.querySelectorAll(".option")) {
        if (button.dataset.value === answer) { button.classList.add("wrong"); button.disabled = true; }
      }
      node.input?.select();
      return;
    }
    locked = true;
    for (const button of node.querySelectorAll(".option")) {
      button.disabled = true;
      if (button.dataset.value === answer) button.classList.add(result.correct ? "right" : "wrong");
      if (!result.correct && button.dataset.value === result.answer) button.classList.add("right");
    }
    if (node.input) node.input.disabled = true;
    const speakText = exercise.speak;
    box.append(
      rating(exercise.id),
      h("div", { class: "row" },
        speakText && canSpeak() ? h("button", { class: "btn ghost small", type: "button", onclick: () => speak(speakText) }, icon("listen"), "Listen") : null,
        h("span", { class: "spacer" }),
        h("button", { class: "btn primary", type: "button", onclick: load }, "Next", icon("arrow"))));
    box.querySelector(".btn.primary").focus();
  }

  root.cleanup = () => onKey && document.removeEventListener("keydown", onKey);
  await load();
  return { destroy: () => onKey && document.removeEventListener("keydown", onKey) };
}

export function source(src) {
  const label = [src.title, src.heading].filter(Boolean).join(" › ");
  return h("div", { class: "source" },
    h("div", { class: "source-head" }, icon("book"), "From your course notes: ", h("strong", {}, label), src.level ? h("span", { class: "pill plain" }, src.level) : null),
    h("div", { class: "source-text", lang: "da" }, trimNote(src.text || "")));
}

function trimNote(text) {
  return text.replace(/^#+ .*\n?/gm, "").trim();
}

function rating(exerciseId) {
  const send = async (event, button, group) => {
    for (const other of group.querySelectorAll(".chip")) other.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-pressed", "true");
    try { await api.feedback({ kind: "exercise", target_id: exerciseId, ...event }); } catch { /* feedback is optional */ }
  };
  const helpful = h("span", { class: "row", style: { gap: "0.35rem" } });
  const level = h("span", { class: "row", style: { gap: "0.35rem" } });
  helpful.append(
    h("button", { class: "chip", type: "button", "aria-pressed": "false", "aria-label": "Helpful", onclick: (e) => send({ helpful: true }, e.currentTarget, helpful) }, icon("up")),
    h("button", { class: "chip", type: "button", "aria-pressed": "false", "aria-label": "Not helpful", onclick: (e) => send({ helpful: false }, e.currentTarget, helpful) }, icon("down")));
  for (const [value, text] of [["easy", "Too easy"], ["ok", "OK"], ["hard", "Too hard"]]) {
    level.append(h("button", { class: "chip", type: "button", "aria-pressed": "false", onclick: (e) => send({ difficulty: value }, e.currentTarget, level) }, text));
  }
  return h("div", { class: "rate" }, h("span", {}, "Was this helpful?"), helpful, h("span", { class: "faint" }, "·"), level);
}

function shuffled(tokens, seed) {
  const list = [...tokens];
  let hash = 0;
  for (const ch of seed) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  for (let i = list.length - 1; i > 0; i -= 1) {
    hash = (hash * 1103515245 + 12345) >>> 0;
    const j = hash % (i + 1);
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list;
}
