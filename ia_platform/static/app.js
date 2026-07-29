/**
 * Forge Platform — front-end da geração de apps por conversa.
 */
(function () {
  "use strict";

  const state = {
    projects: [],
    current: null,
    files: [],
    selectedFile: null,
    lastReport: "",
    running: false,
    runId: null,
    abortController: null,
    selectedTemplate: "blank",
    models: [],
    modelRecommendations: null,
    recommendedModel: null,
    pullingModel: false,
    devStatus: null,
    previewMode: "static",
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    projectList: $("projectList"),
    emptyView: $("emptyView"),
    workspaceView: $("workspaceView"),
    projectTitle: $("projectTitle"),
    chatMessages: $("chatMessages"),
    promptInput: $("promptInput"),
    btnSend: $("btnSend"),
    btnCancel: $("btnCancel"),
    btnNewProject: $("btnNewProject"),
    btnRefreshFiles: $("btnRefreshFiles"),
    btnDeploy: $("btnDeploy"),
    fileTree: $("fileTree"),
    fileViewer: $("fileViewer"),
    previewFrame: $("previewFrame"),
    previewHint: $("previewHint"),
    previewMode: $("previewMode"),
    btnDevStart: $("btnDevStart"),
    btnDevStop: $("btnDevStop"),
    devStatus: $("devStatus"),
    reportViewer: $("reportViewer"),
    healthStatus: $("healthStatus"),
    newProjectModal: $("newProjectModal"),
    deployModal: $("deployModal"),
    deployLog: $("deployLog"),
    btnCloseDeploy: $("btnCloseDeploy"),
    projectNameInput: $("projectNameInput"),
    btnCreateProject: $("btnCreateProject"),
    btnCancelProject: $("btnCancelProject"),
    templateGrid: $("templateGrid"),
    modeSelect: $("modeSelect"),
    modelSelect: $("modelSelect"),
    modelCustomInput: $("modelCustomInput"),
    modelGroupInstalled: $("modelGroupInstalled"),
    modelGroupRecommended: $("modelGroupRecommended"),
    maxStepsInput: $("maxStepsInput"),
    btnModels: $("btnModels"),
    modelsModal: $("modelsModal"),
    btnCloseModels: $("btnCloseModels"),
    hardwareGrid: $("hardwareGrid"),
    primaryModelCard: $("primaryModelCard"),
    modelsCatalog: $("modelsCatalog"),
    pullProgress: $("pullProgress"),
    pullBarFill: $("pullBarFill"),
    pullStatus: $("pullStatus"),
    modelHint: $("modelHint"),
  };

  function getSelectedModel() {
    const value = els.modelSelect?.value || "__auto__";
    if (value === "__auto__") return null;
    if (value === "__custom__") {
      const custom = els.modelCustomInput?.value.trim();
      return custom || null;
    }
    return value;
  }

  function setModelSelection(model) {
    if (!els.modelSelect) return;
    const options = Array.from(els.modelSelect.options).map((o) => o.value);
    if (!model) {
      els.modelSelect.value = "__auto__";
      els.modelCustomInput?.classList.add("hidden");
      return;
    }
    if (options.includes(model)) {
      els.modelSelect.value = model;
      els.modelCustomInput?.classList.add("hidden");
      return;
    }
    els.modelSelect.value = "__custom__";
    if (els.modelCustomInput) {
      els.modelCustomInput.value = model;
      els.modelCustomInput.classList.remove("hidden");
    }
  }

  function populateModelSelect(installed, catalog, recommended) {
    if (!els.modelSelect) return;

    const installedSet = new Set(installed || []);
    const recommendedNames = new Set();
    (catalog || []).forEach((entry) => {
      if (entry.recommended || entry.ollama_name === recommended) {
        recommendedNames.add(entry.ollama_name);
      }
    });

    if (els.modelGroupInstalled) {
      els.modelGroupInstalled.innerHTML = (installed || [])
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
        .join("");
    }

    if (els.modelGroupRecommended) {
      const recList = (catalog || [])
        .filter((entry) => recommendedNames.has(entry.ollama_name) && !installedSet.has(entry.ollama_name))
        .map((entry) => entry.ollama_name);
      const unique = [...new Set(recList)];
      els.modelGroupRecommended.innerHTML = unique
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
        .join("");
    }
  }

  // ── API helpers ──

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || res.statusText || "Erro na requisição");
      err.data = data;
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function updateModelOptions(models) {
    populateModelSelect(models, state.modelRecommendations?.catalog || [], state.recommendedModel);
  }

  function applyRecommendedModel(recommended, installed) {
    state.recommendedModel = recommended || null;
    populateModelSelect(installed || state.models || [], state.modelRecommendations?.catalog || [], recommended);

    const list = installed || state.models || [];
    const isInstalled = recommended && list.some((m) => m === recommended || m.startsWith(String(recommended).split(":")[0] + ":"));
    const current = getSelectedModel();
    const isAuto = !els.modelSelect || els.modelSelect.value === "__auto__";

    if (isAuto && recommended && isInstalled) {
      setModelSelection(recommended);
    } else if (isAuto && list.length) {
      const coder = list.find((m) => /coder|qwen|deepseek/i.test(m));
      if (coder) setModelSelection(coder);
    }

    if (els.modelHint) {
      if (recommended && !isInstalled) {
        els.modelHint.textContent = `Recomendado: ${recommended} — clique em Modelos IA para baixar.`;
        els.modelHint.classList.remove("hidden");
      } else if (recommended) {
        els.modelHint.textContent = `Modelo recomendado: ${recommended}`;
        els.modelHint.classList.remove("hidden");
      } else {
        els.modelHint.classList.add("hidden");
      }
    }
  }

  // ── Health ──

  async function checkHealth() {
    try {
      const d = await api("/api/health");
      state.models = d.models || [];
      updateModelOptions(state.models);
      applyRecommendedModel(d.recommended_model, state.models);
      const ok = d.ollama && d.agent;
      const modelLabel = getSelectedModel() ? ` · ${getSelectedModel()}` : " · auto";
      els.healthStatus.innerHTML = `<span class="status-dot ${ok ? "ok" : "err"}"></span>${ok ? "Ollama pronto" : "Ollama offline?"}${modelLabel}`;
    } catch {
      els.healthStatus.innerHTML = '<span class="status-dot err"></span>offline';
    }
  }

  // ── Models & hardware ──

  function renderHardware(hw) {
    if (!hw) {
      els.hardwareGrid.textContent = "Não foi possível detectar hardware.";
      return;
    }
    const gpu = hw.gpus?.length ? hw.gpus.map((g) => g.name).join(", ") : "Nenhuma detectada";
    const stats = [
      ["Tier", hw.tier || "?"],
      ["RAM", `${hw.ram_available_gb}/${hw.ram_total_gb} GB`],
      ["VRAM", hw.vram_total_gb ? `${hw.vram_free_gb}/${hw.vram_total_gb} GB` : "—"],
      ["CPU", `${hw.cpu_cores} núcleos`],
      ["Memória útil", `${hw.effective_memory_gb} GB`],
      ["GPU", gpu],
      ["SO", `${hw.os || ""} ${hw.machine || ""}`.trim()],
    ];
    els.hardwareGrid.innerHTML = stats
      .map(
        ([label, value]) =>
          `<div class="hw-stat"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(String(value))}</div></div>`
      )
      .join("");
  }

  function modelCardHtml(entry, featured) {
    const tags = (entry.tags || [])
      .map((t) => `<span class="model-tag">${escapeHtml(t)}</span>`)
      .join("");
    const statusTags = [
      entry.installed ? '<span class="model-tag ok">instalado</span>' : '<span class="model-tag warn">não instalado</span>',
      entry.fits ? '<span class="model-tag ok">compatível</span>' : '<span class="model-tag warn">pode não caber</span>',
      entry.recommended ? '<span class="model-tag accent">recomendado</span>' : "",
    ].join("");
    return `
      <h5>${escapeHtml(entry.name)}</h5>
      <p>${escapeHtml(entry.description || "")}</p>
      <div class="model-meta">${tags}${statusTags}</div>
      <p class="model-meta">Ollama: <code>${escapeHtml(entry.ollama_name)}</code> · ~${entry.size_gb} GB · RAM ${entry.ram_gb} GB · VRAM ${entry.vram_gb} GB</p>
      <div class="model-actions">
        <button type="button" class="btn btn-primary btn-sm" data-action="use" data-model="${escapeHtml(entry.ollama_name)}">Usar</button>
        <button type="button" class="btn btn-ghost btn-sm" data-action="pull" data-model="${escapeHtml(entry.ollama_name)}" ${entry.installed ? "disabled" : ""}>Baixar</button>
      </div>
    `;
  }

  function bindModelCardActions(container) {
    container.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const model = btn.dataset.model;
        if (!model) return;
        if (btn.dataset.action === "use") {
          setModelSelection(model);
          closeModelsModal();
          return;
        }
        if (btn.dataset.action === "pull") pullModel(model);
      });
    });
  }

  async function loadModelRecommendations() {
    const data = await api("/api/models/recommendations");
    state.modelRecommendations = data;
    state.models = (data.catalog || []).filter((e) => e.installed).map((e) => e.ollama_name);
    populateModelSelect(
      data.catalog?.filter((e) => e.installed).map((e) => e.ollama_name) || state.models,
      data.catalog || [],
      data.primary?.ollama_name
    );
    applyRecommendedModel(data.primary?.ollama_name, state.models);
    renderHardware(data.hardware);
    if (data.primary) {
      els.primaryModelCard.innerHTML = modelCardHtml(data.primary, true);
      bindModelCardActions(els.primaryModelCard);
    }
    els.modelsCatalog.innerHTML = (data.catalog || [])
      .map((entry) => `<div class="model-card">${modelCardHtml(entry, false)}</div>`)
      .join("");
    bindModelCardActions(els.modelsCatalog);
  }

  function openModelsModal() {
    els.modelsModal.classList.remove("hidden");
    els.pullProgress.classList.add("hidden");
    loadModelRecommendations().catch((e) => {
      els.hardwareGrid.textContent = "Erro: " + e.message;
    });
  }

  function closeModelsModal() {
    if (state.pullingModel) return;
    els.modelsModal.classList.add("hidden");
  }

  async function pullModel(model) {
    if (state.pullingModel) return;
    state.pullingModel = true;
    els.pullProgress.classList.remove("hidden");
    els.pullBarFill.style.width = "0%";
    els.pullStatus.textContent = `Iniciando download de ${model}...`;

    try {
      const res = await fetch("/api/models/pull/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      if (!res.ok || !res.body) throw new Error("Falha ao iniciar download");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const line = block.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          const ev = JSON.parse(line.slice(6));
          if (ev.type === "progress") {
            if (ev.percent != null) els.pullBarFill.style.width = `${ev.percent}%`;
            els.pullStatus.textContent = ev.status || `Baixando ${model}...`;
          }
          if (ev.type === "done") {
            els.pullBarFill.style.width = "100%";
            els.pullStatus.textContent = ev.ok ? `Modelo ${model} pronto!` : `Falha: ${ev.error || "desconhecido"}`;
          }
          if (ev.type === "error") {
            els.pullStatus.textContent = "Erro: " + (ev.error || "download falhou");
          }
        }
      }
      await checkHealth();
      await loadModelRecommendations();
    } catch (e) {
      els.pullStatus.textContent = "Erro: " + e.message;
    } finally {
      state.pullingModel = false;
    }
  }

  // ── Projects ──

  function formatDate(ts) {
    if (!ts) return "";
    return new Date(ts * 1000).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  }

  function renderProjectList() {
    els.projectList.innerHTML = "";
    if (!state.projects.length) {
      els.projectList.innerHTML = '<p class="sidebar-empty">Nenhum projeto ainda</p>';
      return;
    }
    state.projects.forEach((p) => {
      const item = document.createElement("div");
      item.className = "project-item" + (state.current?.id === p.id ? " active" : "");
      item.dataset.id = p.id;
      item.innerHTML = `<div class="name">${escapeHtml(p.name)}</div><div class="meta">${p.files} arquivos · ${formatDate(p.updated)}</div>`;
      item.addEventListener("click", () => selectProject(p.id));
      els.projectList.appendChild(item);
    });
  }

  async function loadProjects() {
    const d = await api("/api/projects");
    state.projects = d.projects || [];
    renderProjectList();
  }

  async function createProject(name, template) {
    const d = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name, template }),
    });
    await loadProjects();
    await selectProject(d.id);
    await persistMessage("system", "Projeto criado. Descreva o que quer construir ou melhorar.");
  }

  async function selectProject(id) {
    const project = state.projects.find((p) => p.id === id);
    if (!project) return;
    state.current = project;
    state.selectedFile = null;
    state.previewMode = "static";
    els.previewMode.value = "static";
    els.fileViewer.classList.add("hidden");
    els.fileViewer.textContent = "";
    els.projectTitle.textContent = project.name;
    els.emptyView.classList.add("hidden");
    els.workspaceView.classList.remove("hidden");
    renderProjectList();
    await loadChat();
    await loadFiles();
    await refreshDevStatus();
    updatePreview();
  }

  function showEmptyView() {
    state.current = null;
    els.emptyView.classList.remove("hidden");
    els.workspaceView.classList.add("hidden");
    renderProjectList();
  }

  // ── Chat history ──

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderChat(messages) {
    els.chatMessages.innerHTML = "";
    if (!messages.length) {
      addMessage(`Projeto "${state.current.name}" aberto. O agente edita arquivos em projects/${state.current.name}.`, "system", false);
      return;
    }
    messages.forEach((m) => addMessage(m.text, m.role, false));
  }

  async function loadChat() {
    if (!state.current) return;
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/chat`);
      renderChat(d.messages || []);
      const lastAgent = [...(d.messages || [])].reverse().find((m) => m.role === "agent");
      if (lastAgent) {
        state.lastReport = lastAgent.text;
        els.reportViewer.textContent = lastAgent.text;
      }
    } catch {
      renderChat([]);
    }
  }

  async function persistMessage(role, text, meta) {
    if (!state.current) return;
    await api(`/api/projects/${encodeURIComponent(state.current.id)}/chat`, {
      method: "POST",
      body: JSON.stringify({ role, text, meta: meta || undefined }),
    });
  }

  function addMessage(text, role, scroll = true) {
    const el = document.createElement("div");
    el.className = "msg " + role + (role === "agent" && /^Erro/i.test(text) ? " error" : "");
    el.textContent = text;
    els.chatMessages.appendChild(el);
    if (scroll) els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return el;
  }

  function removeMessage(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  async function cancelRun() {
    if (!state.running) return;
    if (state.runId) {
      fetch("/api/run/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: state.runId }),
      }).catch(() => {});
    }
    if (state.abortController) {
      state.abortController.abort();
    }
  }

  async function sendPrompt() {
    const prompt = els.promptInput.value.trim();
    if (!prompt || state.running || !state.current) return;

    addMessage(prompt, "user");
    els.promptInput.value = "";
    state.running = true;
    state.runId = null;
    state.abortController = new AbortController();
    els.btnSend.disabled = true;
    els.btnCancel?.classList.remove("hidden");

    const mode = els.modeSelect.value;
    const progressEl = addMessage("Iniciando agente...", "progress");
    const agentEl = addMessage("", "agent live");

    try {
      await persistMessage("user", prompt);

      const res = await fetch("/api/run/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: state.abortController.signal,
        body: JSON.stringify({
          prompt,
          workspace: state.current.path,
          model: getSelectedModel(),
          max_steps: parseInt(els.maxStepsInput.value || "12", 10),
          plan_only: mode === "plan",
          dry_run: mode === "dry",
        }),
      });

      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        const err = new Error(errData.error || "Falha no streaming");
        err.data = errData;
        throw err;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let donePayload = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const line = block.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          const ev = JSON.parse(line.slice(6));
          if (ev.type === "done") {
            donePayload = ev;
            continue;
          }
          handleStreamEvent(ev, progressEl, agentEl);
        }
      }

      removeMessage(progressEl);
      agentEl.classList.remove("live");

      if (donePayload) {
        const summary = donePayload.report || "(sem relatório)";
        agentEl.textContent = summary;
        state.lastReport = summary;
        els.reportViewer.textContent = summary;
        if (donePayload.status === "CANCELLED") {
          agentEl.classList.add("error");
          addMessage("Execução cancelada.", "system");
          await persistMessage("system", "Execução cancelada.").catch(() => {});
        } else if (donePayload.created_files?.length || donePayload.modified_files?.length) {
          const changed = [...(donePayload.created_files || []), ...(donePayload.modified_files || [])];
          const note = `Arquivos alterados: ${changed.join(", ")}`;
          addMessage(note, "system");
          await persistMessage("system", note);
        }
        await loadProjects();
        await loadFiles();
        await refreshDevStatus();
        updatePreview();
        switchTab("report");
      } else {
        agentEl.textContent = agentEl.textContent || "Execução finalizada sem relatório.";
      }
    } catch (e) {
      removeMessage(progressEl);
      agentEl.classList.remove("live");
      if (e.name === "AbortError") {
        agentEl.textContent = "Execução cancelada.";
        agentEl.classList.add("error");
        await persistMessage("agent", "Execução cancelada.").catch(() => {});
      } else {
        const err = "Erro: " + e.message;
        agentEl.textContent = err;
        agentEl.classList.add("error");
        if (e.data?.missing_model) {
          addMessage(`Modelo ausente: ${e.data.model}. Abra Modelos IA para baixar.`, "system");
          openModelsModal();
          if (e.data.model) pullModel(e.data.model);
        }
        await persistMessage("agent", err).catch(() => {});
      }
    } finally {
      state.running = false;
      state.runId = null;
      state.abortController = null;
      els.btnSend.disabled = false;
      els.btnCancel?.classList.add("hidden");
      els.promptInput.focus();
    }
  }

  function handleStreamEvent(ev, progressEl, agentEl) {
    switch (ev.type) {
      case "started":
        if (ev.run_id) state.runId = ev.run_id;
        progressEl.textContent = "Agente iniciado...";
        break;
      case "cancelled":
        progressEl.textContent = "Cancelando...";
        break;
      case "plan":
        progressEl.textContent = `Plano: ${ev.summary || "criado"} (${ev.task_count || "?"} tarefas)`;
        break;
      case "step":
        progressEl.textContent = `Passo ${ev.step}/${ev.max_steps}: ${ev.task_title || ev.task_id}`;
        agentEl.textContent = "";
        break;
      case "tools":
        progressEl.textContent = `Ferramentas: ${(ev.tools || []).join(", ")} (${ev.ok || 0}/${ev.count || 0} ok)`;
        break;
      case "reflection":
        progressEl.textContent = `Reflexão: ${ev.status} — ${(ev.analysis || "").slice(0, 120)}`;
        break;
      case "planning":
        progressEl.textContent = ev.message || "Criando plano...";
        break;
      case "llm_chunk":
        progressEl.textContent = "Gerando chamada de ferramentas...";
        break;
      case "error":
        progressEl.textContent = "Erro: " + (ev.message || ev.error || "desconhecido");
        break;
      default:
        break;
    }
  }

  // ── Files ──

  function fileIcon(type, name) {
    if (type === "dir") return "📁";
    if (/\.html?$/i.test(name)) return "🌐";
    if (/\.(css|scss)$/i.test(name)) return "🎨";
    if (/\.(js|ts|jsx|tsx)$/i.test(name)) return "⚡";
    if (/\.py$/i.test(name)) return "🐍";
    return "📄";
  }

  async function loadFiles() {
    if (!state.current) return;
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/files?recursive=1`);
      state.files = (d.files || []).filter((f) => f.type === "file");
      renderFileTree();
    } catch (e) {
      state.files = [];
      els.fileTree.innerHTML = `<li class="file-error">${escapeHtml(e.message)}</li>`;
    }
  }

  function renderFileTree() {
    els.fileTree.innerHTML = "";
    if (!state.files.length) {
      els.fileTree.innerHTML = '<li class="file-empty">Sem arquivos ainda</li>';
      return;
    }
    state.files.forEach((f) => {
      const li = document.createElement("li");
      li.dataset.path = f.path;
      if (state.selectedFile === f.path) li.classList.add("selected");
      li.innerHTML = `<span class="icon">${fileIcon(f.type, f.name)}</span><span>${escapeHtml(f.path)}</span>`;
      li.addEventListener("click", () => openFile(f.path));
      els.fileTree.appendChild(li);
    });
  }

  async function openFile(path) {
    if (!state.current) return;
    state.selectedFile = path;
    renderFileTree();
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/file?path=${encodeURIComponent(path)}`);
      els.fileViewer.classList.remove("hidden");
      els.fileViewer.textContent = d.content;
      if (/\.html?$/i.test(path)) {
        switchTab("preview");
        updatePreview(path);
      }
    } catch (e) {
      els.fileViewer.classList.remove("hidden");
      els.fileViewer.textContent = "Erro: " + e.message;
    }
  }

  function findPreviewPath() {
    const html = state.files.find((f) => /^index\.html?$/i.test(f.name));
    if (html) return html.path;
    return state.files.find((f) => /\.html?$/i.test(f.name))?.path || null;
  }

  function updatePreview(explicitPath) {
    if (!state.current) return;

    if (state.previewMode === "dev" && state.devStatus?.running && state.devStatus.url) {
      els.previewHint.classList.add("hidden");
      els.previewFrame.src = state.devStatus.url + "?t=" + Date.now();
      return;
    }

    const path = explicitPath || findPreviewPath();
    if (!path) {
      els.previewFrame.src = "about:blank";
      els.previewHint.classList.remove("hidden");
      els.previewHint.textContent = state.devStatus?.has_dev_script
        ? "Nenhum HTML estático. Use npm run dev ou peça ao agente para criar index.html."
        : "Nenhum HTML encontrado. Peça ao agente para criar index.html.";
      return;
    }
    els.previewHint.classList.add("hidden");
    els.previewFrame.src = `/preview/${encodeURIComponent(state.current.id)}/${path.split("/").map(encodeURIComponent).join("/")}?t=${Date.now()}`;
  }

  // ── Dev server ──

  function renderDevControls() {
    const s = state.devStatus || {};
    const hasScript = s.has_dev_script;
    els.btnDevStart.classList.toggle("hidden", !hasScript || s.running);
    els.btnDevStop.classList.toggle("hidden", !s.running);
    els.previewMode.querySelector('option[value="dev"]').disabled = !hasScript;

    if (!hasScript) {
      els.devStatus.textContent = "Sem package.json dev/start";
    } else if (s.running) {
      els.devStatus.textContent = `Rodando :${s.port} (${s.script})`;
    } else if (!s.npm_available) {
      els.devStatus.textContent = "Instale Node.js para dev server";
    } else {
      els.devStatus.textContent = `Pronto: npm run ${s.script}`;
    }
  }

  async function refreshDevStatus() {
    if (!state.current) return;
    try {
      state.devStatus = await api(`/api/projects/${encodeURIComponent(state.current.id)}/dev/status`);
    } catch {
      state.devStatus = null;
    }
    renderDevControls();
  }

  async function startDevServer() {
    if (!state.current) return;
    els.btnDevStart.disabled = true;
    els.devStatus.textContent = "Iniciando (npm install pode demorar)...";
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/dev/start`, {
        method: "POST",
        body: JSON.stringify({ install: true }),
      });
      state.devStatus = { ...state.devStatus, ...d, running: true };
      state.previewMode = "dev";
      els.previewMode.value = "dev";
      renderDevControls();
      updatePreview();
      switchTab("preview");
    } catch (e) {
      els.devStatus.textContent = e.message;
    } finally {
      els.btnDevStart.disabled = false;
    }
  }

  async function stopDevServer() {
    if (!state.current) return;
    try {
      await api(`/api/projects/${encodeURIComponent(state.current.id)}/dev/stop`, { method: "POST", body: "{}" });
      await refreshDevStatus();
      if (state.previewMode === "dev") {
        state.previewMode = "static";
        els.previewMode.value = "static";
      }
      updatePreview();
    } catch (e) {
      els.devStatus.textContent = e.message;
    }
  }

  // ── Deploy ──

  function openDeployModal(text) {
    els.deployLog.textContent = text;
    els.deployModal.classList.remove("hidden");
  }

  function closeDeployModal() {
    els.deployModal.classList.add("hidden");
  }

  async function runDeploy() {
    if (!state.current) return;
    els.btnDeploy.disabled = true;
    openDeployModal("Preparando deploy...\n\nRequer VERCEL_TOKEN no ambiente para deploy automático.");
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(state.current.id)}/deploy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const d = await res.json();
      let log = d.message || "";
      if (d.url) log += `\n\nURL: ${d.url}`;
      if (d.steps?.length) log += "\n\nPassos manuais:\n" + d.steps.map((s, i) => `${i + 1}. ${s}`).join("\n");
      if (d.log_tail) log += "\n\n--- log ---\n" + d.log_tail;
      els.deployLog.textContent = log;
      if (d.url) {
        els.deployLog.innerHTML = escapeHtml(log).replace(
          escapeHtml(d.url),
          `<a class="deploy-link" href="${escapeHtml(d.url)}" target="_blank" rel="noopener">${escapeHtml(d.url)}</a>`
        );
      }
    } catch (e) {
      els.deployLog.textContent = "Erro: " + e.message;
    } finally {
      els.btnDeploy.disabled = false;
    }
  }

  // ── Tabs ──

  function switchTab(name) {
    document.querySelectorAll(".panel-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.tab === name);
    });
    $("panelFiles").classList.toggle("hidden", name !== "files");
    $("panelPreview").classList.toggle("hidden", name !== "preview");
    $("panelReport").classList.toggle("hidden", name !== "report");
    if (name === "preview") updatePreview();
  }

  // ── Modal ──

  function openNewProjectModal(template) {
    state.selectedTemplate = template || "blank";
    els.projectNameInput.value = "";
    els.newProjectModal.classList.remove("hidden");
    document.querySelectorAll(".modal-templates .template-card").forEach((card) => {
      card.classList.toggle("selected", card.dataset.template === state.selectedTemplate);
    });
    els.projectNameInput.focus();
  }

  function closeNewProjectModal() {
    els.newProjectModal.classList.add("hidden");
  }

  async function submitNewProject() {
    const name = els.projectNameInput.value.trim() || "novo-projeto";
    els.btnCreateProject.disabled = true;
    try {
      await createProject(name, state.selectedTemplate);
      closeNewProjectModal();
    } catch (e) {
      alert("Não foi possível criar o projeto: " + e.message);
    } finally {
      els.btnCreateProject.disabled = false;
    }
  }

  // ── Events ──

  els.btnSend.addEventListener("click", sendPrompt);
  els.btnCancel?.addEventListener("click", cancelRun);
  els.modelSelect?.addEventListener("change", () => {
    const custom = els.modelSelect.value === "__custom__";
    els.modelCustomInput?.classList.toggle("hidden", !custom);
    if (custom) els.modelCustomInput?.focus();
  });
  els.promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendPrompt();
    }
  });

  els.btnNewProject.addEventListener("click", () => openNewProjectModal("blank"));
  els.btnCancelProject.addEventListener("click", closeNewProjectModal);
  els.btnCreateProject.addEventListener("click", submitNewProject);
  els.newProjectModal.addEventListener("click", (e) => {
    if (e.target === els.newProjectModal) closeNewProjectModal();
  });

  els.btnRefreshFiles.addEventListener("click", () => {
    loadFiles();
    updatePreview();
  });

  els.btnDeploy.addEventListener("click", runDeploy);
  els.btnModels.addEventListener("click", openModelsModal);
  els.btnCloseModels.addEventListener("click", closeModelsModal);
  els.modelsModal.addEventListener("click", (e) => {
    if (e.target === els.modelsModal && !state.pullingModel) closeModelsModal();
  });
  els.btnCloseDeploy.addEventListener("click", closeDeployModal);
  els.deployModal.addEventListener("click", (e) => {
    if (e.target === els.deployModal) closeDeployModal();
  });

  els.btnDevStart.addEventListener("click", startDevServer);
  els.btnDevStop.addEventListener("click", stopDevServer);
  els.previewMode.addEventListener("change", () => {
    state.previewMode = els.previewMode.value;
    updatePreview();
  });

  document.querySelectorAll(".panel-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  function bindTemplateCards(container) {
    container.querySelectorAll(".template-card").forEach((card) => {
      card.addEventListener("click", () => {
        const tpl = card.dataset.template;
        if (container.classList.contains("modal-templates")) {
          state.selectedTemplate = tpl;
          container.querySelectorAll(".template-card").forEach((c) => c.classList.remove("selected"));
          card.classList.add("selected");
        } else {
          openNewProjectModal(tpl);
        }
      });
    });
  }

  bindTemplateCards(els.templateGrid);
  bindTemplateCards(document.querySelector(".modal-templates"));

  els.projectNameInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitNewProject();
  });

  // ── Init ──

  async function init() {
    checkHealth();
    setInterval(checkHealth, 15000);
    try {
      await loadProjects();
      if (state.projects.length) {
        await selectProject(state.projects[0].id);
      } else {
        showEmptyView();
      }
    } catch {
      showEmptyView();
    }
  }

  init();
})();
