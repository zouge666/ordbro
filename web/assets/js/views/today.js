import { api } from "../api.js";
import { h, icon, ring } from "../dom.js";
import { danishDate, greeting, modeLabel } from "../lib/format.js";
import { canSpeak, speak } from "../speech.js";

const MODE_TEXT = {
  recognize: "Choose the right form",
  recall: "Fill in the gap",
  produce: "Build it yourself",
};

export async function render(root) {
  const [learner, sentences] = await Promise.all([api.learner(), api.sentences()]);
  const now = new Date();
  const plan = learner.plan;
  const mastered = learner.skills.filter((s) => s.mastered).length;
  const practiced = learner.skills.filter((s) => s.seen > 0).length;
  const sentence = sentences[(now.getDate() + now.getMonth() * 31) % sentences.length];

  const review = plan.due_reviews
    ? `Review ${plan.due_reviews} word${plan.due_reviews === 1 ? "" : "s"}`
    : "Learn new words";

  const page = h("div", { class: "page fade-in" },
    h("section", { class: "today-hero" },
      h("div", {},
        h("p", { class: "date" }, danishDate(now)),
        h("h1", {}, `${greeting(now)}!`),
        h("p", { class: "lede" }, `Here is a short plan for today. It takes about ${plan.minutes} minutes.`),
        h("div", { class: "row", style: { marginTop: "1.3rem" } },
          h("a", { class: "btn primary", href: "#/practice" }, icon("practice"), "Start practice"),
          h("a", { class: "btn", href: "#/practice?focus=review" }, icon("layers"), review))),
      heroArt()),

    h("div", { class: "grid two" },
      h("section", { class: "card" },
        h("div", { class: "card-head" },
          h("h2", {}, "Today's focus"),
          h("span", { class: "pill plain" }, "Chosen for you")),
        plan.focus.length
          ? h("div", { class: "focus-list" }, plan.focus.map(focusItem))
          : h("p", { class: "muted" }, "Every skill is mastered. Well done! Keep your words fresh with a review.")),

      h("div", { class: "stack" },
        h("section", { class: "card" },
          h("div", { class: "card-head" },
            h("h2", {}, "Say it out loud"),
            canSpeak() ? h("button", { class: "icon-button", type: "button", "aria-label": "Listen", onclick: () => speak(sentence.text) }, icon("listen")) : null),
          h("p", { class: "da", style: { fontSize: "1.45rem", lineHeight: "1.3" } }, sentence.text),
          h("p", { class: "muted small", "data-english": "" }, sentence.en),
          h("a", { class: "btn small", href: "#/speak", style: { marginTop: "0.9rem", alignSelf: "flex-start" } }, icon("speak"), "Practice speaking")),
        h("section", { class: "card stats" },
          stat(`${mastered}/${learner.skills.length}`, "skills mastered"),
          stat(`${practiced}`, "skills practiced"),
          stat(`${learner.cards.total}`, "words to review")))));

  root.append(page);
}

function focusItem(skill) {
  return h("a", { class: "focus-item", href: `#/practice?focus=${skill.id}`, style: { color: "inherit", textDecoration: "none" } },
    ring(skill.mastery),
    h("div", { class: "text" },
      h("div", { class: "name" }, skill.name, h("span", { class: "da" }, skill.name_da)),
      h("div", { class: "muted small" }, skill.about)),
    h("span", { class: "pill", title: MODE_TEXT[skill.mode] }, modeLabel(skill.mode)));
}

function stat(value, label) {
  return h("div", { class: "stat" }, h("span", { class: "value" }, value), h("span", { class: "label" }, label));
}

function heroArt() {
  const wrap = h("div", { class: "hero-art", "aria-hidden": "true" });
  wrap.innerHTML = `<svg viewBox="0 0 200 130" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
    <circle cx="150" cy="34" r="13" stroke-width="1.6"/>
    <path d="M14 86c26-46 146-46 172 0" />
    <path d="M8 87h184" />
    <path d="M52 64v23M76 55v32M100 52v35M124 55v32M148 64v23" stroke-width="1.4"/>
    <path d="M20 103c10-5 20-5 30 0s20 5 30 0 20-5 30 0 20 5 30 0 20-5 30 0" stroke-width="1.4" opacity=".7"/>
    <path d="M38 116c10-5 20-5 30 0s20 5 30 0 20-5 30 0 20 5 30 0" stroke-width="1.4" opacity=".45"/>
  </svg>`;
  return wrap;
}
