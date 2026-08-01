// Small pure helpers. They are tested with `node --test web/tests`.

const DAYS = ["søndag", "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag"];
const MONTHS = ["januar", "februar", "marts", "april", "maj", "juni", "juli", "august", "september", "oktober", "november", "december"];

export function danishDate(date) {
  return `${DAYS[date.getDay()]} ${date.getDate()}. ${MONTHS[date.getMonth()]}`;
}

export function greeting(date) {
  const hour = date.getHours();
  if (hour < 10) return "Godmorgen";
  if (hour < 18) return "Goddag";
  return "Godaften";
}

export function percent(value) {
  return `${Math.round(Math.max(0, Math.min(1, value || 0)) * 100)}%`;
}

export function modeLabel(mode) {
  return { recognize: "Recognize", recall: "Recall", produce: "Build" }[mode] || mode;
}

export function splitGap(text) {
  const index = text.indexOf("___");
  if (index < 0) return [text];
  return [text.slice(0, index), null, text.slice(index + 3)];
}

export function insertLetter(value, start, end, letter) {
  const from = Math.max(0, Math.min(start, value.length));
  const to = Math.max(from, Math.min(end, value.length));
  return { value: value.slice(0, from) + letter + value.slice(to), caret: from + letter.length };
}

export function highlight(text, terms) {
  // Returns [text, isMatch] pairs for words that start with one of the terms.
  const stems = (terms || []).filter((t) => t && t.length >= 3).map((t) => t.toLowerCase());
  if (!stems.length) return [[text, false]];
  const parts = [];
  const re = /[\p{L}\p{N}]+|[^\p{L}\p{N}]+/gu;
  for (const match of text.matchAll(re)) {
    const word = match[0];
    const lower = word.toLowerCase();
    const hit = /[\p{L}\p{N}]/u.test(word) && stems.some((s) => lower.startsWith(s));
    const last = parts[parts.length - 1];
    if (last && last[1] === hit) last[0] += word;
    else parts.push([word, hit]);
  }
  return parts;
}
