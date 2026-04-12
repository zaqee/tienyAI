"""HTML for the settings page.

We keep the page plain and dependency-light so the server remains easy to ship.
"""
from __future__ import annotations


def render_settings_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>local-llm settings</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: #11192f;
      --muted: #97a3c3;
      --text: #eef2ff;
      --accent: #7c9cff;
      --border: rgba(255,255,255,.08);
      --good: #41d38a;
      --bad: #ff6b6b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top, #17203c, var(--bg) 55%);
      color: var(--text);
    }
    .wrap {
      max-width: 1150px;
      margin: 0 auto;
      padding: 32px 18px 48px;
    }
    .hero {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 20px;
    }
    h1 {
      margin: 0;
      font-size: 2rem;
      letter-spacing: -0.03em;
    }
    p {
      margin: 8px 0 0;
      color: var(--muted);
      line-height: 1.55;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
    }
    .card {
      background: rgba(17,25,47,.92);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 18px;
      box-shadow: 0 20px 55px rgba(0,0,0,.24);
      backdrop-filter: blur(10px);
    }
    .span-7 { grid-column: span 7; }
    .span-5 { grid-column: span 5; }
    .span-12 { grid-column: span 12; }
    .row { display: grid; gap: 12px; }
    .two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    label {
      display: block;
      font-size: .88rem;
      color: var(--muted);
      margin-bottom: 6px;
    }
    input, select, textarea, button {
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,.03);
      color: var(--text);
      padding: 12px 14px;
      font: inherit;
      outline: none;
    }
    textarea { min-height: 116px; resize: vertical; }
    button {
      cursor: pointer;
      background: linear-gradient(135deg, #5c79ff, #86a4ff);
      border: none;
      font-weight: 700;
      color: #081226;
    }
    button.secondary {
      background: rgba(255,255,255,.06);
      color: var(--text);
      border: 1px solid var(--border);
    }
    .muted { color: var(--muted); }
    .kpi {
      font-size: 1.4rem;
      font-weight: 800;
      margin-top: 4px;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: .88rem;
      background: rgba(255,255,255,.05);
      border: 1px solid var(--border);
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--bad);
      box-shadow: 0 0 0 4px rgba(255,107,107,.1);
    }
    .dot.good {
      background: var(--good);
      box-shadow: 0 0 0 4px rgba(65,211,138,.12);
    }
    .list {
      display: grid;
      gap: 10px;
    }
    .model-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(255,255,255,.03);
    }
    .pill {
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      background: rgba(124,156,255,.12);
      color: #b9cbff;
      font-size: .76rem;
      margin-left: 8px;
    }
    .small { font-size: .82rem; color: var(--muted); }
    pre {
      overflow: auto;
      background: rgba(0,0,0,.22);
      border-radius: 14px;
      border: 1px solid var(--border);
      padding: 14px;
      margin: 0;
    }
    .flex {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .spacer { height: 6px; }
    @media (max-width: 900px) {
      .span-7, .span-5, .span-12 { grid-column: span 12; }
      .two, .three { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>local-llm settings</h1>
        <p>Local model registry, runtime settings, and API access in one place.</p>
      </div>
      <div class="status"><span id="statusDot" class="dot"></span><span id="statusText">Loading...</span></div>
    </div>

    <div class="grid">
      <section class="card span-7">
        <div class="flex" style="justify-content: space-between;">
          <div>
            <h2 style="margin:0 0 6px;">Current model</h2>
            <div class="small">Choose a registered model and save it as the active runtime model.</div>
          </div>
          <div class="pill" id="modelCount">0 models</div>
        </div>

        <div class="spacer"></div>

        <label for="modelSelect">Registered models</label>
        <select id="modelSelect"></select>

        <div class="spacer"></div>
        <div class="flex">
          <button onclick="setActiveModel()">Load selected model</button>
          <button class="secondary" onclick="refreshAll()">Refresh</button>
        </div>

        <div class="spacer"></div>
        <div id="modelDetails" class="small">No model selected yet.</div>
      </section>

      <section class="card span-5">
        <h2 style="margin:0 0 6px;">Runtime settings</h2>
        <div class="small">These values affect generation immediately after saving.</div>

        <div class="spacer"></div>

        <div class="row two">
          <div>
            <label for="temperature">Temperature</label>
            <input id="temperature" type="number" step="0.05" min="0" max="2" />
          </div>
          <div>
            <label for="maxTokens">Max tokens</label>
            <input id="maxTokens" type="number" step="1" min="1" max="8192" />
          </div>
        </div>

        <div class="spacer"></div>

        <div class="row two">
          <div>
            <label for="topP">Top-p</label>
            <input id="topP" type="number" step="0.01" min="0" max="1" />
          </div>
          <div>
            <label for="repeatPenalty">Repeat penalty</label>
            <input id="repeatPenalty" type="number" step="0.05" min="0.5" max="2.5" />
          </div>
        </div>

        <div class="spacer"></div>
        <div>
          <label for="nCtx">Context window</label>
          <input id="nCtx" type="number" step="1" min="256" max="32768" />
        </div>

        <div class="spacer"></div>
        <button onclick="saveSettings()">Save settings</button>
      </section>

      <section class="card span-12">
        <h2 style="margin:0 0 6px;">Try the API</h2>
        <div class="small">This prototype exposes a normal FastAPI backend, so any frontend can call it.</div>
        <div class="spacer"></div>
        <pre><code>POST /chat
{
  "message": "Hello"
}

POST /v1/chat/completions
{
  "messages": [{"role": "user", "content": "Hello"}]
}</code></pre>
      </section>

      <section class="card span-12">
        <h2 style="margin:0 0 6px;">Registered models</h2>
        <div id="modelList" class="list"></div>
      </section>
    </div>
  </div>

<script>
async function refreshAll() {
  const [stateRes, modelsRes] = await Promise.all([
    fetch('/api/state'),
    fetch('/models')
  ]);
  const state = await stateRes.json();
  const models = await modelsRes.json();

  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const modelCount = document.getElementById('modelCount');
  const modelSelect = document.getElementById('modelSelect');
  const modelList = document.getElementById('modelList');
  const modelDetails = document.getElementById('modelDetails');

  const active = state.active_model;
  if (state.ready) {
    statusDot.classList.add('good');
    statusText.textContent = 'Server ready';
  } else {
    statusDot.classList.remove('good');
    statusText.textContent = 'No model loaded';
  }

  document.getElementById('temperature').value = state.settings.temperature;
  document.getElementById('maxTokens').value = state.settings.max_tokens;
  document.getElementById('topP').value = state.settings.top_p;
  document.getElementById('repeatPenalty').value = state.settings.repeat_penalty;
  document.getElementById('nCtx').value = state.settings.n_ctx;

  modelCount.textContent = `${models.models.length} models`;

  modelSelect.innerHTML = '';
  models.models.forEach(model => {
    const option = document.createElement('option');
    option.value = model.id;
    option.textContent = `${model.name} — ${model.source_type}`;
    if (active && active.id === model.id) option.selected = true;
    modelSelect.appendChild(option);
  });

  if (active) {
    modelDetails.innerHTML = `
      <strong>${active.name}</strong><br/>
      <span class="muted">Path:</span> ${active.local_path}<br/>
      <span class="muted">Source:</span> ${active.source_type} • ${active.source}
    `;
  } else {
    modelDetails.textContent = 'No active model. Load one from the dropdown above.';
  }

  modelList.innerHTML = '';
  if (!models.models.length) {
    modelList.innerHTML = '<div class="small">No models registered yet.</div>';
    return;
  }

  models.models.forEach(model => {
    const item = document.createElement('div');
    item.className = 'model-item';
    item.innerHTML = `
      <div>
        <div><strong>${model.name}</strong>${active && active.id === model.id ? ' <span class="pill">active</span>' : ''}</div>
        <div class="small">${model.source_type} • ${model.local_path}</div>
      </div>
      <div class="small">${model.added_at}</div>
    `;
    modelList.appendChild(item);
  });
}

async function setActiveModel() {
  const modelId = document.getElementById('modelSelect').value;
  const res = await fetch('/models/load', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({model_id: modelId})
  });
  if (!res.ok) {
    alert('Could not load model');
    return;
  }
  await refreshAll();
}

async function saveSettings() {
  const payload = {
    temperature: parseFloat(document.getElementById('temperature').value),
    max_tokens: parseInt(document.getElementById('maxTokens').value, 10),
    top_p: parseFloat(document.getElementById('topP').value),
    repeat_penalty: parseFloat(document.getElementById('repeatPenalty').value),
    n_ctx: parseInt(document.getElementById('nCtx').value, 10),
  };
  const res = await fetch('/settings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    alert('Could not save settings');
    return;
  }
  await refreshAll();
}

refreshAll().catch(() => {
  document.getElementById('statusText').textContent = 'Failed to load state';
});
</script>
</body>
</html>"""
