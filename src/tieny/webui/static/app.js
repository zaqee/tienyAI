const $ = (id) => document.getElementById(id);
const ui = {
  body: $("modelsBody"), empty: $("emptyState"), loadedName: $("loadedName"), unload: $("unloadButton"),
  status: $("serverStatus"), toast: $("toast"), chatHistory: $("chatHistory"), input: $("chatInput"),
  context: $("contextMenu"), developerConsole: $("developerConsole"), developerMenu: $("developerModeMenu"),
  logOutput: $("logOutput"), logLevel: $("logLevel"), autoScroll: $("autoScroll")
};

const settings = {
  developerMode: localStorage.getItem("tieny.developerMode") === "true",
  logLevel: localStorage.getItem("tieny.logLevel") || "ALL",
  autoScroll: localStorage.getItem("tieny.autoScroll") !== "false"
};
let models = [];
let loaded = null;
let toastTimer = null;
let logTimer = null;

function saveSettings() {
  localStorage.setItem("tieny.developerMode", String(settings.developerMode));
  localStorage.setItem("tieny.logLevel", settings.logLevel);
  localStorage.setItem("tieny.autoScroll", String(settings.autoScroll));
}

async function api(path, options = {}) {
  const opts = { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } };
  const response = await fetch(path, opts);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `${response.status} ${response.statusText}`);
  return data;
}

function notify(message, error = false) {
  clearTimeout(toastTimer);
  ui.toast.textContent = message;
  ui.toast.classList.toggle("error", error);
  ui.toast.classList.remove("hidden");
  toastTimer = setTimeout(() => ui.toast.classList.add("hidden"), 3500);
}

function bytes(value) {
  if (value == null) return "missing";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = Number(value), i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(1)} ${units[i]}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
}

function renderModels() {
  ui.body.innerHTML = "";
  ui.empty.classList.toggle("hidden", models.length !== 0);
  loaded = models.find(m => m.loaded) || null;
  ui.loadedName.textContent = loaded ? `${loaded.name} · ${loaded.id}` : "None";
  ui.unload.disabled = !loaded;

  for (const model of models) {
    const tr = document.createElement("tr");
    if (model.loaded) tr.classList.add("loaded");
    tr.innerHTML = `
      <td><strong>${escapeHtml(model.name)}</strong></td>
      <td><code>${escapeHtml(model.id)}</code></td>
      <td>${escapeHtml(model.type.toUpperCase())}</td>
      <td>${escapeHtml(model.runtime)}</td>
      <td>${bytes(model.size_bytes)}</td>
      <td class="path" title="${escapeHtml(model.path)}">${escapeHtml(model.path)}</td>
      <td><div class="row-actions">
        <button data-act="load" data-id="${model.id}" ${model.loaded ? "disabled" : ""}>Load</button>
        <button data-act="name" data-id="${model.id}">Name</button>
        <button data-act="reset" data-id="${model.id}">Reset</button>
        <button data-act="remove" data-id="${model.id}">Remove</button>
        <button data-act="delete" data-id="${model.id}" class="danger">Delete file</button>
      </div></td>`;
    ui.body.appendChild(tr);
  }
}

async function refresh() {
  try {
    models = await api("/api/models");
    renderModels();
    ui.status.className = "status ok";
    ui.status.innerHTML = '<span class="dot"></span> local server online';
  } catch (err) {
    ui.status.className = "status bad";
    ui.status.innerHTML = '<span class="dot"></span> server error';
    notify(err.message, true);
  }
}

$("addButton").addEventListener("click", async () => {
  try {
    const picked = await api("/api/system/select-model-file", { method: "POST" });
    if (!picked.path) return;
    const model = await api("/api/models/add", { method: "POST", body: JSON.stringify({ path: picked.path }) });
    notify(`Added ${model.name}. Tieny stored the path only.`);
    await refresh();
  } catch (err) { notify(err.message, true); }
});

$("refreshButton").addEventListener("click", refresh);
ui.unload.addEventListener("click", async () => {
  try {
    await api("/api/models/unload", { method: "POST" });
    notify("Model unloaded.");
    await refresh();
  } catch (err) { notify(err.message, true); }
});

ui.body.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-act]");
  if (!button) return;
  const id = button.dataset.id;
  const model = models.find(m => m.id === id);
  try {
    if (button.dataset.act === "load") {
      await api(`/api/models/load/${encodeURIComponent(id)}`, { method: "POST" });
      notify(`Loaded ${model.name}.`);
    } else if (button.dataset.act === "name") {
      const value = prompt("New model name", model.name);
      if (value == null || value.trim() === "" || value === model.name) return;
      await api(`/api/models/${encodeURIComponent(id)}/name`, {
        method: "POST", body: JSON.stringify({ name: value.trim(), remove: false })
      });
      notify("Model name changed.");
    } else if (button.dataset.act === "reset") {
      await api(`/api/models/${encodeURIComponent(id)}/name`, {
        method: "POST", body: JSON.stringify({ name: null, remove: true })
      });
      notify("Name reset from filename.");
    } else if (button.dataset.act === "remove") {
      if (!confirm(`Remove ${model.name} from Tieny?\n\nThe original file will stay untouched.`)) return;
      await api(`/api/models/${encodeURIComponent(id)}`, { method: "DELETE" });
      notify(`Removed ${model.name} from Tieny. Original file untouched.`);
    } else if (button.dataset.act === "delete") {
      if (!confirm(`DELETE the original model file as well as its Tieny entry?\n\n${model.path}\n\nThis cannot be undone.`)) return;
      await api(`/api/models/${encodeURIComponent(id)}?delete_file=true`, { method: "DELETE" });
      notify(`Deleted ${model.name} and its original file.`);
    }
    await refresh();
  } catch (err) { notify(err.message, true); }
});

$("chatForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = ui.input.value.trim();
  if (!content) return;
  if (!loaded) { notify("Load a model first.", true); return; }
  addBubble("user", content);
  ui.input.value = "";
  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ messages: [{ role: "user", content }], max_tokens: 256, temperature: 0.7 })
    });
    const text = result.choices?.[0]?.message?.content ?? result.choices?.[0]?.text ?? "(no text returned)";
    addBubble("assistant", text);
  } catch (err) { notify(err.message, true); addBubble("assistant", `[error] ${err.message}`); }
});

function addBubble(role, content) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = content;
  ui.chatHistory.appendChild(div);
  ui.chatHistory.scrollTop = ui.chatHistory.scrollHeight;
}

function applyDeveloperMode() {
  ui.developerConsole.classList.toggle("hidden", !settings.developerMode);
  ui.developerMenu.textContent = settings.developerMode ? "Disable Developer Mode" : "Enable Developer Mode";
  ui.logLevel.value = settings.logLevel;
  ui.autoScroll.checked = settings.autoScroll;
  saveSettings();
  if (settings.developerMode) startLogPolling(); else stopLogPolling();
}

document.addEventListener("contextmenu", (event) => {
  event.preventDefault();
  ui.context.style.left = `${Math.min(event.clientX, window.innerWidth - 210)}px`;
  ui.context.style.top = `${Math.min(event.clientY, window.innerHeight - 60)}px`;
  ui.context.classList.remove("hidden");
});
document.addEventListener("click", (event) => {
  if (!ui.context.contains(event.target)) ui.context.classList.add("hidden");
});
ui.developerMenu.addEventListener("click", () => {
  settings.developerMode = !settings.developerMode;
  ui.context.classList.add("hidden");
  applyDeveloperMode();
});
$("closeDev").addEventListener("click", () => {
  settings.developerMode = false;
  applyDeveloperMode();
});
ui.logLevel.addEventListener("change", () => { settings.logLevel = ui.logLevel.value; saveSettings(); pollLogs(); });
ui.autoScroll.addEventListener("change", () => { settings.autoScroll = ui.autoScroll.checked; saveSettings(); });
$("copyLogs").addEventListener("click", async () => {
  await navigator.clipboard.writeText(ui.logOutput.textContent || "");
  notify("Logs copied.");
});
$("clearLogs").addEventListener("click", async () => {
  try { await api("/api/logs/clear", { method: "POST" }); ui.logOutput.textContent = ""; }
  catch (err) { notify(err.message, true); }
});

async function pollLogs() {
  if (!settings.developerMode) return;
  try {
    const data = await api(`/api/logs?limit=500&level=${encodeURIComponent(settings.logLevel)}`);
    ui.logOutput.textContent = data.logs.map(item => item.formatted).join("\n");
    if (settings.autoScroll) ui.logOutput.scrollTop = ui.logOutput.scrollHeight;
  } catch (err) {
    ui.logOutput.textContent = `[developer console error] ${err.message}`;
  }
}
function startLogPolling() { stopLogPolling(); pollLogs(); logTimer = setInterval(pollLogs, 1000); }
function stopLogPolling() { if (logTimer) clearInterval(logTimer); logTimer = null; }

applyDeveloperMode();
refresh();
setInterval(refresh, 5000);
