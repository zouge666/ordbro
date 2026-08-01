import assert from "node:assert/strict";
import test from "node:test";

import { danishDate, greeting, highlight, insertLetter, percent, splitGap } from "../assets/js/lib/format.js";

test("danish date and greeting", () => {
  const date = new Date(2026, 2, 2, 8, 30);
  assert.equal(danishDate(date), "mandag 2. marts");
  assert.equal(greeting(date), "Godmorgen");
  assert.equal(greeting(new Date(2026, 2, 2, 20)), "Godaften");
});

test("percent is clamped", () => {
  assert.equal(percent(0.456), "46%");
  assert.equal(percent(2), "100%");
  assert.equal(percent(undefined), "0%");
});

test("gap splitting", () => {
  assert.deepEqual(splitGap("Jeg ___ fra Syrien."), ["Jeg ", null, " fra Syrien."]);
  assert.deepEqual(splitGap("no gap"), ["no gap"]);
});

test("inserting a Danish letter at the caret", () => {
  assert.deepEqual(insertLetter("gr", 1, 1, "å"), { value: "går", caret: 2 });
  assert.deepEqual(insertLetter("abc", 0, 3, "ø"), { value: "ø", caret: 1 });
});

test("highlight marks words that start with a term", () => {
  const parts = highlight("Verbet står på plads 2.", ["verb", "plad"]);
  assert.deepEqual(parts.filter(([, hit]) => hit).map(([t]) => t), ["Verbet", "plads"]);
});
