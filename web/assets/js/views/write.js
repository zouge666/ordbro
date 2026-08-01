import { placeholder } from "./placeholder.js";

export async function render(root) {
  root.append(placeholder("Write", "This part of the app is not ready yet."));
}
