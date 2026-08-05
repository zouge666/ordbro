import { api } from "../api.js";
import { h, icon, meter } from "../dom.js";
import { percent } from "../lib/format.js";
import { refreshProgress } from "../app.js";

export async function render(root) {
  const learner = await api.learner();
  const byLevel = { A1: [], A2: [] };
  for (const skill of learner.skills) byLevel[skill.level]?.push(skill);
  const names = Object.fromEntries(learner.skills.map((s) => [s.id, s.name]));
  const seen = learner.skills.reduce((sum, s) => sum + s.seen, 0);
  const correct = learner.skills.reduce((sum, s) => sum + s.correct, 0);

  root.append(h("div", { class: "page fade-in" },
    h("div", { class: "page-head" },
      h("div", {},
        h("p", { class: "eyebrow" }, "Progress"),
        h("h1", {}, "What you know"),
        h("p", { class: "lede" }, "Mastery is the tutor's estimate that you know a skill. It goes up when you answer without help and is used to choose your next task.")),
      h("button", { class: "btn ghost small", type: "button", onclick: reset }, icon("redo"), "Start over")),
    h("section", { class: "card stats" },
      stat(`${learner.skills.filter((s) => s.mastered).length}/${learner.skills.length}`, "skills mastered"),
      stat(seen ? percent(correct / seen) : "–", "answers right without help"),
      stat(`${learner.cards.due}/${learner.cards.total}`, "words due / in review")),
    ...["A1", "A2"].map((level) => h("section", { class: "stack" },
      h("h2", {}, `Level ${level}`),
      h("div", { class: "skill-grid" }, byLevel[level].map((skill) => skillCard(skill, names))))),
    h("section", { class: "card" },
      h("h2", { style: { marginBottom: "0.6rem" } }, "Recent activity"),
      learner.history.length
        ? h("div", { class: "history" }, [...learner.history].reverse().map((event) => historyRow(event, names)))
        : h("p", { class: "muted" }, "Nothing yet. Start with a short practice."))));

  async function reset() {
    if (!window.confirm("Delete all progress on this computer?")) return;
    await api.reset();
    refreshProgress();
    root.replaceChildren();
    await render(root);
  }
}

function stat(value, label) {
  return h("div", { class: "stat" }, h("span", { class: "value" }, value), h("span", { class: "label" }, label));
}

function skillCard(skill, names) {
  const locked = !skill.unlocked;
  return h("a", { class: `card skill-card${locked ? " locked" : ""}`, href: `#/practice?focus=${skill.id}`, style: { color: "inherit", textDecoration: "none" } },
    h("div", { class: "top" }, h("strong", {}, skill.name), skill.mastered ? h("span", { class: "pill moss" }, "Mastered") : locked ? h("span", { class: "pill plain" }, "Later") : null),
    h("span", { class: "name-da" }, skill.name_da),
    meter(skill.mastery, skill.mastered ? "moss" : ""),
    h("div", { class: "row small muted" }, h("span", {}, percent(skill.mastery)), h("span", { class: "spacer" }), h("span", {}, `${skill.correct}/${skill.seen} right`)),
    locked ? h("p", { class: "faint small" }, `Comes after: ${skill.requires.map((id) => names[id]).join(", ")}`) : h("p", { class: "faint small" }, skill.about));
}

function historyRow(event, names) {
  const when = new Date(event.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const what = event.type === "speak" ? `Speaking, score ${event.score}` : `${names[event.skill] || "Word review"} · ${event.type}${event.attempt > 1 ? " (second try)" : ""}`;
  const mark = event.type === "speak" ? "" : event.correct ? "yes" : "no";
  return h("div", { class: "history-row" }, h("span", { class: `mark ${mark}` }), h("span", {}, what), h("span", { class: "faint" }, when));
}
