import { api } from "../api.js";
import { announce, fill, h, icon, ring } from "../dom.js";
import { canListen, canSpeak, hasDanishVoice, listen, speak } from "../speech.js";

export async function render(root, params) {
  const sentences = await api.sentences();
  let index = Math.max(0, sentences.findIndex((s) => s.id === params.get("id")));
  let recognition = null;
  let alternatives = [];

  const list = h("div", { class: "sentence-list", role: "list" });
  const target = h("p", { class: "speak-target", lang: "da" });
  const english = h("p", { class: "muted", "data-english": "" });
  const heard = h("p", { class: "heard", "aria-live": "polite" });
  const typed = h("input", { class: "input", type: "text", lang: "da", placeholder: "Or type what you said", "aria-label": "What you said" });
  const result = h("div", { class: "stack" });
  const record = h("button", { class: "btn primary record", type: "button" }, icon("mic"), "Record");

  const noAsr = !canListen()
    ? h("p", { class: "notice amber small" }, "Speech recognition is not available in this browser. Try Chrome or Edge, or type what you said. The feedback works the same way.")
    : null;

  root.append(h("div", { class: "page fade-in" },
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, "Speak"),
        h("h1", {}, "Say it out loud"),
        h("p", { class: "lede" }, "Listen to the sentence, then say it. Ordbro shows which words the computer understood and gives tips for the sounds that are often hard."))),
    h("div", { class: "speak-layout" },
      h("section", { class: "card speak-card" },
        h("div", { class: "row" }, h("span", { class: "pill", id: "level" }), h("span", { class: "spacer" }),
          h("button", { class: "btn ghost small", type: "button", onclick: () => move(1) }, "Next sentence", icon("arrow"))),
        target, english,
        h("div", { class: "speak-controls" },
          canSpeak() ? h("button", { class: "btn", type: "button", onclick: () => speak(sentences[index].text, 0.9) }, icon("listen"), "Listen") : null,
          canSpeak() ? h("button", { class: "btn ghost", type: "button", onclick: () => speak(sentences[index].text, 0.65) }, "Slowly") : null,
          record),
        canSpeak() && !hasDanishVoice() ? h("p", { class: "faint small" }, "No Danish voice was found on this computer, so the model audio may sound English.") : null,
        noAsr,
        heard,
        h("div", { class: "answer-row" }, typed,
          h("button", { class: "btn", type: "button", onclick: () => check(typed.value, [typed.value]) }, "Check")),
        result,
        h("p", { class: "faint small" }, "The score shows how well the computer understood you. It is not a grade. Speech recognition also makes mistakes, more often with accents, so trust your teacher's ear more than the number.")),
      h("aside", { class: "card" }, h("h2", { style: { marginBottom: "0.8rem" } }, "Sentences"), list))));

  record.addEventListener("click", () => {
    if (recognition) { recognition.stop(); return; }
    alternatives = [];
    heard.textContent = "Listening ...";
    record.classList.add("on");
    record.lastChild.textContent = "Stop";
    recognition = listen({
      onResult: ({ text, alternatives: alts, final }) => {
        heard.textContent = text;
        if (final) { alternatives = alts; }
      },
      onError: (error) => { heard.textContent = `Could not listen: ${error.message}`; },
      onEnd: () => {
        recognition = null;
        record.classList.remove("on");
        record.lastChild.textContent = "Record";
        if (alternatives.length) check(alternatives[0], alternatives);
      },
    });
  });
  typed.addEventListener("keydown", (event) => { if (event.key === "Enter") check(typed.value, [typed.value]); });

  function draw() {
    const sentence = sentences[index];
    target.textContent = sentence.text;
    english.textContent = sentence.en;
    root.querySelector("#level").textContent = sentence.level;
    heard.textContent = "";
    typed.value = "";
    fill(result);
    fill(list, ...sentences.map((s, i) =>
      h("button", { type: "button", "aria-current": i === index ? "true" : "false", onclick: () => { index = i; draw(); } }, s.text)));
  }

  function move(step) {
    index = (index + step + sentences.length) % sentences.length;
    draw();
  }

  async function check(transcript, alts) {
    if (!transcript.trim()) return;
    const sentence = sentences[index];
    const data = await api.assess(sentence.id, sentence.text, transcript, alts);
    heard.textContent = `We heard: "${data.transcript}"`;
    fill(result, 
      h("div", { class: "score" }, scoreRing(data.score),
        h("div", {},
          h("strong", {}, data.score >= 90 ? "Very clear!" : data.score >= 60 ? "Good. A few words were hard to understand." : "Let us try that again."),
          h("p", { class: "muted small" }, summary(data.words)))),
      h("div", { class: "word-chips" }, data.words.map(wordChip)),
      data.tips.length ? h("div", { class: "grid two" }, data.tips.map(tipCard)) : null,
      h("div", { class: "row" },
        h("button", { class: "btn", type: "button", onclick: () => { fill(result); heard.textContent = ""; } }, icon("redo"), "Try again"),
        h("button", { class: "btn ghost", type: "button", onclick: () => move(1) }, "Next sentence", icon("arrow"))));
    announce(`Score ${data.score}.`);
  }

  draw();
  return { destroy: () => recognition?.abort?.() };
}

function summary(words) {
  const targets = words.filter((w) => w.target);
  const ok = targets.filter((w) => w.status === "ok").length;
  const close = targets.filter((w) => w.status === "close").length;
  const parts = [`${ok} of ${targets.length} words matched exactly`];
  if (close) parts.push(`${close} ${close === 1 ? "was" : "were"} close`);
  return `${parts.join(", ")}.`;
}

function scoreRing(score) {
  const node = ring(score / 100, 72);
  node.querySelector("text").textContent = String(score);
  return node;
}

function wordChip(word) {
  const label = { ok: "", close: "almost", missed: "not heard", extra: "extra" }[word.status];
  return h("span", { class: `word-chip ${word.status}`, title: word.heard ? `heard: ${word.heard}` : "" },
    word.target || word.heard, label ? h("small", {}, word.status === "close" ? `heard "${word.heard}"` : label) : null);
}

function tipCard(tip) {
  return h("div", { class: "notice tip" },
    h("h3", {}, tip.title),
    h("p", {}, tip.tip),
    h("p", { class: "muted small da" }, `Examples: ${tip.examples}`));
}
