import { h } from "../dom.js";

export function placeholder(title, text) {
  return h("div", { class: "page" },
    h("div", { class: "page-head" }, h("div", {}, h("p", { class: "eyebrow" }, "Ordbro"), h("h1", {}, title))),
    h("div", { class: "card empty" }, h("p", {}, text)));
}
