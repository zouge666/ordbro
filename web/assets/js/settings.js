// Display settings, saved in localStorage when it is available.

const KEY = "ordbro.settings";
const DEFAULTS = { theme: "system", size: "normal", contrast: false, spacing: false, english: true, motion: false };

export function loadSettings() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...DEFAULTS };
  }
}

function save(settings) {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    /* private mode: settings last for this visit only */
  }
}

export function applySettings(settings) {
  const root = document.documentElement;
  if (settings.theme === "system") delete root.dataset.theme;
  else root.dataset.theme = settings.theme;
  root.dataset.size = settings.size;
  root.dataset.contrast = settings.contrast ? "high" : "normal";
  root.dataset.spacing = settings.spacing ? "wide" : "normal";
  root.dataset.motion = settings.motion ? "reduce" : "normal";
  root.dataset.english = settings.english ? "show" : "hide";
}

export function setupSettings() {
  const dialog = document.getElementById("settings");
  const form = dialog.querySelector("form");
  let settings = loadSettings();
  applySettings(settings);

  const fill = () => {
    form.theme.value = settings.theme;
    form.size.value = settings.size;
    for (const name of ["contrast", "spacing", "english", "motion"]) form[name].checked = settings[name];
  };
  form.addEventListener("change", () => {
    settings = {
      theme: form.theme.value,
      size: form.size.value,
      contrast: form.contrast.checked,
      spacing: form.spacing.checked,
      english: form.english.checked,
      motion: form.motion.checked,
    };
    applySettings(settings);
    save(settings);
  });
  document.getElementById("open-settings").addEventListener("click", () => {
    fill();
    dialog.showModal();
  });
}
