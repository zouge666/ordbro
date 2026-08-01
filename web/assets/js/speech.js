// Browser speech: text to speech for model audio, and speech recognition.
// Both use the Web Speech API. Recognition is not available in every browser,
// so every feature that uses it also works by typing.

let danishVoice = null;

function pickVoice() {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  danishVoice = voices.find((v) => v.lang === "da-DK") || voices.find((v) => v.lang.startsWith("da")) || null;
  return danishVoice;
}

if ("speechSynthesis" in window) {
  pickVoice();
  window.speechSynthesis.addEventListener?.("voiceschanged", pickVoice);
}

export function canSpeak() {
  return "speechSynthesis" in window;
}

export function speak(text, rate = 0.9) {
  if (!canSpeak()) return false;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "da-DK";
  utterance.rate = rate;
  const voice = danishVoice || pickVoice();
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
  return true;
}

export function hasDanishVoice() {
  return Boolean(danishVoice || pickVoice());
}

export function canListen() {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export function listen({ onResult, onEnd, onError }) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    onError?.(new Error("Speech recognition is not available in this browser."));
    return null;
  }
  const recognition = new Recognition();
  recognition.lang = "da-DK";
  recognition.interimResults = true;
  recognition.maxAlternatives = 3;
  recognition.addEventListener("result", (event) => {
    const result = event.results[event.results.length - 1];
    const alternatives = Array.from(result, (alt) => alt.transcript.trim());
    onResult?.({ text: alternatives[0], alternatives, final: result.isFinal });
  });
  recognition.addEventListener("error", (event) => onError?.(new Error(event.error)));
  recognition.addEventListener("end", () => onEnd?.());
  recognition.start();
  return recognition;
}
