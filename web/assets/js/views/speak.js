import { placeholder } from "./placeholder.js";

export async function render(root) {
  root.append(placeholder("Speak", "This part of the app is not ready yet."));
}
