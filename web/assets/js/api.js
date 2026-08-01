// Thin client for the Ordbro HTTP API.

const LEARNER = "local";

async function request(method, path, body) {
  const options = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* keep the status text */
    }
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

export const api = {
  overview: () => request("GET", "/api/overview"),
  learner: () => request("GET", `/api/learner?learner=${LEARNER}`),
  reset: () => request("POST", "/api/learner/reset", { learner: LEARNER }),
  next: (focus) => request("POST", "/api/practice/next", { learner: LEARNER, focus: focus || null }),
  answer: (exerciseId, answer, attempt) =>
    request("POST", "/api/practice/answer", { learner: LEARNER, exercise_id: exerciseId, answer, attempt }),
  ask: (question) => request("POST", "/api/ask", { question }),
  note: (docId) => request("GET", `/api/notes/${encodeURIComponent(docId)}`),
  check: (text) => request("POST", "/api/write/check", { text }),
  sentences: () => request("GET", "/api/speak/sentences"),
  assess: (sentenceId, target, transcript) =>
    request("POST", "/api/speak/assess", { learner: LEARNER, sentence_id: sentenceId, target, transcript }),
  feedback: (event) => request("POST", "/api/feedback", { learner: LEARNER, ...event }),
  feedbackSummary: () => request("GET", "/api/feedback/summary"),
  lab: () => request("GET", "/api/lab"),
};
