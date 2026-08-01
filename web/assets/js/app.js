import { api } from "./api.js";
import { hydrateIcons } from "./dom.js";
import { setupSettings } from "./settings.js";

const views = {
  today: () => import("./views/today.js"),
  practice: () => import("./views/practice.js"),
  speak: () => import("./views/speak.js"),
  ask: () => import("./views/ask.js"),
  write: () => import("./views/write.js"),
  progress: () => import("./views/progress.js"),
  lab: () => import("./views/lab.js"),
};

const main = document.getElementById("main");
let current = null;

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "") || "today";
  const [name, query = ""] = raw.split("?");
  return { name: views[name] ? name : "today", params: new URLSearchParams(query) };
}

async function route() {
  const { name, params } = parseHash();
  for (const link of document.querySelectorAll("[data-view]")) {
    if (link.dataset.view === name) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  current?.destroy?.();
  main.replaceChildren();
  try {
    const module = await views[name]();
    current = await module.render(main, params);
  } catch (error) {
    console.error(error);
    main.replaceChildren(errorPage(error));
  }
  hydrateIcons(main);
  main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
  refreshProgress();
}

function errorPage(error) {
  const page = document.createElement("div");
  page.className = "page";
  page.innerHTML = `<div class="card empty"><h2>Something went wrong</h2><p class="muted"></p></div>`;
  page.querySelector("p").textContent = String(error.message || error);
  return page;
}

export async function refreshProgress() {
  try {
    const learner = await api.learner();
    const mastered = learner.skills.filter((s) => s.mastered).length;
    document.getElementById("mini-count").textContent = `${mastered} / ${learner.skills.length}`;
    document.getElementById("mini-meter").style.width = `${(mastered / learner.skills.length) * 100}%`;
  } catch {
    /* the sidebar is optional */
  }
}

setupSettings();
hydrateIcons(document);
window.addEventListener("hashchange", route);
route();
