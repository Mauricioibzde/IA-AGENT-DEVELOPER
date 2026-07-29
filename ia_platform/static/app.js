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
    selectedTemplate: "blank",
    models: [],
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
    btnNewProject: $("btnNewProject"),
    btnRefreshFiles: $("btnRefreshFiles"),
    fileTree: $("fileTree"),
    fileViewer: $("fileViewer"),
    previewFrame: $("previewFrame"),
    previewHint: $("previewHint"),
    reportViewer: $("reportViewer"),
    healthStatus: $("healthStatus"),
    newProjectModal: $("newProjectModal"),
    projectNameInput: $("projectNameInput"),
    btnCreateProject: $("btnCreateProject"),
    btnCancelProject: $("btnCancelProject"),
    templateGrid: $("templateGrid"),
    modeSelect: $("modeSelect"),
    modelInput: $("modelInput"),
    maxStepsInput: $("maxStepsInput"),
  };

  // ── API helpers ──

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data.error || res.statusText || "Erro na requisição";
      throw new Error(msg);
    }
    return data;
  }

  // ── Health ──

  async function checkHealth() {
    try {
      const d = await api("/api/health");
      state.models = d.models || [];
      const ok = d.ollama && d.agent;
      els.healthStatus.innerHTML = `<span class="status-dot ${ok ? "ok" : "err"}"></span>${ok ? "Ollama pronto" : "Ollama offline?"}`;
      if (!els.modelInput.value && state.models.length) {
        const coder = state.models.find((m) => /coder|qwen|deepseek/i.test(m));
        if (coder) els.modelInput.placeholder = coder;
      }
    } catch {
      els.healthStatus.innerHTML = '<span class="status-dot err"></span>offline';
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
    addMessage("Projeto criado. Descreva o que quer construir ou melhorar.", "system");
  }

  async function selectProject(id) {
    const project = state.projects.find((p) => p.id === id);
    if (!project) return;
    state.current = project;
    state.selectedFile = null;
    els.fileViewer.classList.add("hidden");
    els.fileViewer.textContent = "";
    els.projectTitle.textContent = project.name;
    els.emptyView.classList.add("hidden");
    els.workspaceView.classList.remove("hidden");
    renderProjectList();
    await loadFiles();
    updatePreview();
    if (!els.chatMessages.children.length) {
      addMessage(`Projeto "${project.name}" aberto. O agente vai editar arquivos em projects/${project.name}.`, "system");
    }
  }

  function showEmptyView() {
    state.current = null;
    els.emptyView.classList.remove("hidden");
    els.workspaceView.classList.add("hidden");
    renderProjectList();
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
    const path = explicitPath || findPreviewPath();
    if (!path) {
      els.previewFrame.src = "about:blank";
      els.previewHint.classList.remove("hidden");
      els.previewHint.textContent = "Nenhum HTML encontrado. Peça ao agente para criar index.html.";
      return;
    }
    els.previewHint.classList.add("hidden");
    els.previewFrame.src = `/preview/${encodeURIComponent(state.current.id)}/${path.split("/").map(encodeURIComponent).join("/")}?t=${Date.now()}`;
  }

  // ── Chat ──

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function addMessage(text, role) {
    const el = document.createElement("div");
    el.className = "msg " + role + (role === "agent" && /^Erro/i.test(text) ? " error" : "");
    el.textContent = text;
    els.chatMessages.appendChild(el);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return el;
  }

  function removeMessage(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  async function sendPrompt() {
    const prompt = els.promptInput.value.trim();
    if (!prompt || state.running || !state.current) return;

    addMessage(prompt, "user");
    els.promptInput.value = "";
    state.running = true;
    els.btnSend.disabled = true;
    const pending = addMessage("Agente trabalhando... (pode levar alguns minutos)", "system");

    const mode = els.modeSelect.value;
    try {
      const d = await api("/api/run", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          workspace: state.current.path,
          model: els.modelInput.value.trim() || null,
          max_steps: parseInt(els.maxStepsInput.value || "12", 10),
          plan_only: mode === "plan",
          dry_run: mode === "dry",
        }),
      });
      removeMessage(pending);
      const summary = d.report || "(sem relatório)";
      state.lastReport = summary;
      els.reportViewer.textContent = summary;
      addMessage(summary, "agent");
      if (d.created_files?.length || d.modified_files?.length) {
        const changed = [...(d.created_files || []), ...(d.modified_files || [])];
        addMessage(`Arquivos alterados: ${changed.join(", ")}`, "system");
      }
      await loadProjects();
      await loadFiles();
      updatePreview();
      switchTab("report");
    } catch (e) {
      removeMessage(pending);
      addMessage("Erro: " + e.message, "agent");
    } finally {
      state.running = false;
      els.btnSend.disabled = false;
      els.promptInput.focus();
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
