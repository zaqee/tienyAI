
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
    option.textContent = `${model.alias || model.name} — ${model.source_type}`;
    if (active && active.id === model.id) option.selected = true;
    modelSelect.appendChild(option);
  });

  if (active) {
    modelDetails.innerHTML = `
      <strong>${active.alias || active.name}</strong>
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
        <div><strong>${model.alias || model.name}</strong>${active && active.id === model.id ? ' <span class="pill">active</span>' : ''}</div>
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId })
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    alert('Could not save settings');
    return;
  }
  await refreshAll();
}

function openAddModel() {
  document.getElementById("addModal").style.display = "flex";
}

function closeModal() {
  document.getElementById("addModal").style.display = "none";
}

async function submitModel() {
  const file = document.getElementById("modelFile").files[0];
  const url = document.getElementById("modelUrl").value;
  const btn = document.getElementById("addBtn");
  const aliasInput = document.getElementById("modelAlias");

  if (aliasInput.value) {
    formData.append("alias", aliasInput.value);
  }
  const form = new FormData();

  if (file) {
    form.append("file", file);
  } else if (url) {
    form.append("url", url);
  } else {
    alert("Select file or enter URL");
    return;
  }

  btn.disabled = true;
  btn.textContent = "Adding...";

  try {
    const res = await fetch("/models/add", {
      method: "POST",
      body: form
    });

    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Failed");

    alert("Model added: " + data.model);

    closeModal();
    refreshAll();

  } catch (err) {
    alert("Error: " + err.message);
  }

  btn.disabled = false;
  btn.textContent = "Add";
}
window.editAlias = async function (modelId) {
  const newAlias = prompt("New alias:");
  if (!newAlias) return;

  const res = await fetch("/models/alias", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model_id: modelId,
      alias: newAlias
    })
  });

  if (!res.ok) {
    alert("Failed");
    return;
  }

  alert("Updated");
  refreshAll();
};


refreshAll().catch(() => {
  document.getElementById('statusText').textContent = 'Failed to load state';
});
