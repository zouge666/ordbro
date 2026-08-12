// Tiny helpers for building DOM nodes, plus the icon set.

export function h(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "html") node.innerHTML = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2), value);
    else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  append(node, children);
  return node;
}

// Like replaceChildren, but skips null, undefined and false like h() does.
export function fill(node, ...children) {
  node.replaceChildren();
  append(node, children);
  return node;
}

function append(node, children) {
  for (const child of children.flat()) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

const PATHS = {
  today: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>',
  practice: '<rect x="4" y="5" width="13" height="15" rx="2.5"/><path d="M8 3.5h9.5A2.5 2.5 0 0 1 20 6v11"/><path d="M8 10h5M8 14h3"/>',
  speak: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0"/><path d="M12 18v2.5"/>',
  ask: '<path d="M4.5 6.5A2.5 2.5 0 0 1 7 4h10a2.5 2.5 0 0 1 2.5 2.5v7A2.5 2.5 0 0 1 17 16h-6l-4.5 4v-4h0A2.5 2.5 0 0 1 4.5 13.5z"/><path d="M10 8.6a2 2 0 1 1 2.6 1.9c-.4.2-.6.5-.6.9v.3"/><path d="M12 13.6h.01"/>',
  write: '<path d="M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z"/><path d="M14 8l3 3"/>',
  progress: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  lab: '<path d="M9 3.5h6M10 3.5v5.2L4.6 18a1.6 1.6 0 0 0 1.4 2.5h12a1.6 1.6 0 0 0 1.4-2.5L14 8.7V3.5"/><path d="M7.4 14h9.2"/>',
  settings: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  listen: '<path d="M5 9.5v5h3.5L13 18.5v-13L8.5 9.5z"/><path d="M16.5 9a4 4 0 0 1 0 6M18.8 6.6a7.5 7.5 0 0 1 0 10.8"/>',
  check: '<path d="M5 12.5 10 17.5 19.5 7"/>',
  hint: '<path d="M9 17.5h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1.1 1 1.8v.3h5v-.3c0-.7.4-1.4 1-1.8A6 6 0 0 0 12 3z"/>',
  cross: '<circle cx="12" cy="12" r="8.5"/><path d="M9 9l6 6M15 9l-6 6"/>',
  book: '<path d="M4.5 5.5A2 2 0 0 1 6.5 3.5H19v14H6.5a2 2 0 0 0-2 2z"/><path d="M4.5 19.5a2 2 0 0 0 2 2H19v-4"/>',
  up: '<path d="M7 20.5H4.5v-9H7zM7 11.5l4-8a2.2 2.2 0 0 1 2.2 2.6l-.6 3.4h5.6a2 2 0 0 1 2 2.3l-1.2 6.6a2 2 0 0 1-2 1.6H7"/>',
  down: '<path d="M7 3.5H4.5v9H7zM7 12.5l4 8a2.2 2.2 0 0 0 2.2-2.6l-.6-3.4h5.6a2 2 0 0 0 2-2.3l-1.2-6.6a2 2 0 0 0-2-1.6H7"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  redo: '<path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.5"/><path d="M4 4v4.5h4.5"/>',
  mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0"/><path d="M12 18v2.5"/>',
  stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
  layers: '<path d="M12 3.5 21 8.5 12 13.5 3 8.5z"/><path d="M3 12.5l9 5 9-5M3 16.5l9 5 9-5"/>',
  bridge: '<path d="M2.5 16.5c3.4-7.2 15.6-7.2 19 0" stroke-width="2"/><path d="M1.5 17h21" stroke-width="2"/><path d="M8 12.6V17M12 11.3V17M16 12.6V17" stroke-width="1.6"/>',
};

export function icon(name, label) {
  const span = document.createElement("span");
  span.className = "icon";
  span.innerHTML = svg(name);
  if (label) span.setAttribute("aria-label", label);
  else span.setAttribute("aria-hidden", "true");
  return span;
}

export function svg(name) {
  const path = PATHS[name] || "";
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

export function hydrateIcons(root = document) {
  for (const node of root.querySelectorAll("[data-icon]")) {
    if (!node.firstChild) node.innerHTML = svg(node.dataset.icon);
  }
}

export function ring(value, size = 54) {
  const radius = 22;
  const circumference = 2 * Math.PI * radius;
  const shown = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const wrap = document.createElement("span");
  wrap.innerHTML = `<svg class="ring" width="${size}" height="${size}" viewBox="0 0 54 54" role="img" aria-label="${shown}% mastered">
    <circle class="track" cx="27" cy="27" r="${radius}"/>
    <circle class="value" cx="27" cy="27" r="${radius}" stroke-dasharray="${(circumference * shown) / 100} ${circumference}"/>
    <text x="27" y="27">${shown}</text></svg>`;
  return wrap.firstElementChild;
}

export function meter(value, extra = "") {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return h("div", { class: `meter ${extra}`, role: "meter", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(pct) },
    h("span", { style: { width: `${pct}%` } }));
}

export function announce(text) {
  const live = document.getElementById("live");
  if (!live) return;
  live.textContent = "";
  window.setTimeout(() => { live.textContent = text; }, 30);
}

export function toast(text) {
  const node = h("div", { class: "toast fade-in", role: "status" }, text);
  document.body.append(node);
  window.setTimeout(() => node.remove(), 2200);
}

export function loading() {
  return h("div", { class: "empty" }, h("div", { class: "spinner", style: { margin: "0 auto" } }));
}
