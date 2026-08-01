import { placeholder } from "./placeholder.js";

export async function render(root) {
  root.append(placeholder("Ask", "This part of the app is not ready yet."));
}
