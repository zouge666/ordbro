import { placeholder } from "./placeholder.js";

export async function render(root) {
  root.append(placeholder("Progress", "This part of the app is not ready yet."));
}
