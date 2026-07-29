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
    fileEditorOriginal: "",
    fileEditorRevision: null,
    fileEditorDirty: false,
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
    deploying: false,
    deployReady: false,
    mobilePanelOpen: false,
    runs: [],
    selectedRunId: null,
    recentChangedFiles: [],
    expandedDirs: {},
    fileSearchTimer: null,
    projectSearchTimer: null,
    searchMatches: null,
    devWasRunning: false,
    devAutoRestarted: false,
    devPollTimer: null,
    previewLoadTimer: null,
    previewExpectingContent: false,
    previewLoadRetried: false,
    previewRevision: null,
    previewPollTimer: null,
    ollamaOk: false,
    previewDevice: "desktop",
    healthInFlight: false,
    setupInFlight: null,
    pendingPrompt: null,
    ollamaInstalled: true,
    setupPlatform: null,
    setupInstallUrl: null,
    serverFeatures: null,
    platformVersion: null,
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    sidebar: $("sidebar"),
    sidebarBackdrop: $("sidebarBackdrop"),
    btnToggleSidebar: $("btnToggleSidebar"),
    fileSearchInput: $("fileSearchInput"),
    runHistoryList: $("runHistoryList"),
    projectList: $("projectList"),
    projectSearch: $("projectSearch"),
    modeChip: $("modeChip"),
    emptyView: $("emptyView"),
    workspaceView: $("workspaceView"),
    projectTitle: $("projectTitle"),
    chatMessages: $("chatMessages"),
    promptInput: $("promptInput"),
    btnSend: $("btnSend"),
    btnCancel: $("btnCancel"),
    btnNewProject: $("btnNewProject"),
    btnRefreshFiles: $("btnRefreshFiles"),
    btnClearChat: $("btnClearChat"),
    btnDeploy: $("btnDeploy"),
    fileTree: $("fileTree"),
    fileViewer: $("fileViewer"),
    fileEditorShell: $("fileEditorShell"),
    fileEditorPath: $("fileEditorPath"),
    fileEditorDirty: $("fileEditorDirty"),
    btnFileSave: $("btnFileSave"),
    previewFrame: $("previewFrame"),
    previewHint: $("previewHint"),
    previewEmpty: $("previewEmpty"),
    btnPreviewStartDev: $("btnPreviewStartDev"),
    previewMode: $("previewMode"),
    btnDevStart: $("btnDevStart"),
    btnDevStop: $("btnDevStop"),
    btnDevClear: $("btnDevClear"),
    btnDevRestart: $("btnDevRestart"),
    devStatus: $("devStatus"),
    reportViewer: $("reportViewer"),
    healthStatus: $("healthStatus"),
    newProjectModal: $("newProjectModal"),
    deployModal: $("deployModal"),
    deployModalInner: $("deployModalInner"),
    deployBadge: $("deployBadge"),
    deploySpinner: $("deploySpinner"),
    deployChecklist: $("deployChecklist"),
    deployLog: $("deployLog"),
    btnOpenDeployUrl: $("btnOpenDeployUrl"),
    btnCloseDeploy: $("btnCloseDeploy"),
    rightPanel: $("rightPanel"),
    mobileTabs: $("mobileTabs"),
    mobileBackdrop: $("mobileBackdrop"),
    devErrorLog: $("devErrorLog"),
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
    chatHero: $("chatHero"),
    previewViewport: $("previewViewport"),
    deviceSwitcher: $("deviceSwitcher"),
    ollamaOfflineBanner: $("ollamaOfflineBanner"),
    ollamaBannerTitle: $("ollamaBannerTitle"),
    ollamaOfflineText: $("ollamaOfflineText"),
    btnAutoSetup: $("btnAutoSetup"),
    modelsSetupInline: $("modelsSetupInline"),
    modelsSetupPercent: $("modelsSetupPercent"),
    modelsSetupBarFill: $("modelsSetupBarFill"),
    modelsSetupStatus: $("modelsSetupStatus"),
    setupModal: $("setupModal"),
    setupStatus: $("setupStatus"),
    setupBarFill: $("setupBarFill"),
    setupPercent: $("setupPercent"),
    setupSteps: $("setupSteps"),
    setupLog: $("setupLog"),
    setupLogWrap: $("setupLogWrap"),
    setupSubtitle: $("setupSubtitle"),
    sidebarSetupPill: $("sidebarSetupPill"),
    sidebarSetupLabel: $("sidebarSetupLabel"),
    sidebarSetupBar: $("sidebarSetupBar"),
    setupModelPick: $("setupModelPick"),
    setupActions: $("setupActions"),
    btnSetupRetry: $("btnSetupRetry"),
    btnSetupClose: $("btnSetupClose"),
    setupInstallLink: $("setupInstallLink"),
    setupInstallLinkWrap: $("setupInstallLinkWrap"),
  };

  const SETUP_STEPS = [
    { id: "check", label: "Verificar ambiente" },
    { id: "install", label: "Instalar Ollama" },
    { id: "start", label: "Iniciar serviço Ollama" },
    { id: "node", label: "Verificar Node.js" },
    { id: "hardware", label: "Analisar hardware" },
    { id: "model", label: "Baixar modelo IA" },
    { id: "config", label: "Configurar modelo" },
    { id: "done", label: "Pronto para usar" },
  ];

  const SETUP_PHASE_STEP = {
    check: "check",
    install: "install",
    start: "start",
    node: "node",
    hardware: "hardware",
    model: "model",
    config: "config",
    done: "done",
  };

  const LAST_PROJECT_KEY = "forge_last_project";

  const SETUP_DISMISS_KEY = "forge_setup_dismissed";

  const setupProgress = {
    stepStatus: {},
    visible: false,
    lastPercent: 0,
  };

  function setupStepIcon(status) {
    if (status === "done") return "✓";
    if (status === "active") return "◉";
    if (status === "error") return "✕";
    if (status === "skip") return "—";
    return "○";
  }

  function renderSetupSteps() {
    if (!els.setupSteps) return;
    els.setupSteps.innerHTML = SETUP_STEPS.map((step) => {
      const status = setupProgress.stepStatus[step.id] || "pending";
      return `<li class="setup-step setup-step--${status}" data-step="${step.id}">
        <span class="setup-step-icon" aria-hidden="true">${setupStepIcon(status)}</span>
        <span class="setup-step-label">${escapeHtml(step.label)}</span>
      </li>`;
    }).join("");
  }

  function setSetupStep(stepId, status) {
    setupProgress.stepStatus[stepId] = status;
    const idx = SETUP_STEPS.findIndex((s) => s.id === stepId);
    if (idx > 0 && status === "active") {
      for (let i = 0; i < idx; i++) {
        const prev = SETUP_STEPS[i].id;
        const cur = setupProgress.stepStatus[prev];
        if (cur === "pending" || cur === "active") {
          setupProgress.stepStatus[prev] = "done";
        }
      }
    }
    renderSetupSteps();
  }

  function inferSetupStepFromMessage(message) {
    const msg = String(message || "").toLowerCase();
    if (/instal|winget|setup\.exe|download.*ollama|brew install|install\.sh/.test(msg)) return "install";
    if (/iniciando ollama|ollama serve|serviço|iniciado automaticamente|ollama pronto|ollama já/.test(msg)) return "start";
    if (/node\.js|npm|preview react/.test(msg)) return "node";
    if (/hardware|recomend|analisando|catalog|tier|ram/.test(msg)) return "hardware";
    if (/baixando|pull|download|modelo|manifest|gguf/.test(msg)) return "model";
    if (/configur|selecion|pronto para/.test(msg)) return "config";
    if (/verific|preparando|ambiente/.test(msg)) return "check";
    return null;
  }

  function appendSetupLog(line) {
    if (!els.setupLog || !line) return;
    els.setupLogWrap?.classList.remove("hidden");
    const ts = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    els.setupLog.textContent = (els.setupLog.textContent ? els.setupLog.textContent + "\n" : "") + `[${ts}] ${line}`;
    els.setupLog.scrollTop = els.setupLog.scrollHeight;
  }

  function resetSetupProgress() {
    setupProgress.stepStatus = {};
    SETUP_STEPS.forEach((s) => {
      setupProgress.stepStatus[s.id] = "pending";
    });
    if (els.setupLog) els.setupLog.textContent = "";
    els.setupLogWrap?.classList.add("hidden");
    renderSetupSteps();
    updateSetupProgress(0, "Iniciando configuração...");
  }

  function syncSidebarSetupProgress(percent, label) {
    if (!els.sidebarSetupPill) return;
    if (!setupProgress.visible) {
      els.sidebarSetupPill.classList.add("hidden");
      return;
    }
    els.sidebarSetupPill.classList.remove("hidden");
    if (els.sidebarSetupLabel && label) els.sidebarSetupLabel.textContent = label;
    if (els.sidebarSetupBar) els.sidebarSetupBar.style.width = `${Math.min(100, Math.max(0, percent || 0))}%`;
  }

  function syncInlineSetupProgress(percent, message) {
    const modelsOpen = els.modelsModal && !els.modelsModal.classList.contains("hidden");
    if (!setupProgress.visible || !modelsOpen) {
      els.modelsSetupInline?.classList.add("hidden");
      return;
    }
    els.modelsSetupInline?.classList.remove("hidden");
    if (els.modelsSetupPercent) els.modelsSetupPercent.textContent = `${percent}%`;
    if (els.modelsSetupBarFill) els.modelsSetupBarFill.style.width = `${percent}%`;
    if (message && els.modelsSetupStatus) els.modelsSetupStatus.textContent = message;
    if (els.btnAutoSetup) {
      els.btnAutoSetup.textContent = state.setupInFlight ? "Configurando..." : "Configurar automaticamente";
    }
  }

  function updateSetupProgress(percent, message, stepId) {
    const pct = Math.min(100, Math.max(0, Math.round(percent ?? 0)));
    setupProgress.lastPercent = pct;
    if (els.setupPercent) els.setupPercent.textContent = `${pct}%`;
    if (els.setupBarFill) els.setupBarFill.style.width = `${pct}%`;
    if (message && els.setupStatus) els.setupStatus.textContent = message;
    if (message) appendSetupLog(message);
    if (stepId) setSetupStep(stepId, "active");
    else if (message) {
      const inferred = inferSetupStepFromMessage(message);
      if (inferred) setSetupStep(inferred, "active");
    }
    syncSidebarSetupProgress(pct, message || "Configurando...");
    syncInlineSetupProgress(pct, message || "Configurando...");
  }

  function showSetupModal(message, percent) {
    setupProgress.visible = true;
    els.setupModal?.classList.remove("hidden");
    resetSetupProgress();
    updateSetupProgress(percent ?? 5, message || "Iniciando configuração...", "check");
  }

  function hideSetupModal(delayMs = 0) {
    const hide = () => {
      setupProgress.visible = false;
      els.setupModal?.classList.add("hidden");
      els.sidebarSetupPill?.classList.add("hidden");
      els.modelsSetupInline?.classList.add("hidden");
      if (els.setupBarFill) els.setupBarFill.style.width = "0%";
      if (els.setupPercent) els.setupPercent.textContent = "0%";
      setupProgress.stepStatus = {};
      if (els.btnAutoSetup) els.btnAutoSetup.textContent = "Configurar automaticamente";
      els.setupModelPick?.classList.add("hidden");
      showSetupActions(false);
    };
    if (delayMs > 0) setTimeout(hide, delayMs);
    else hide();
  }

  function finishSetupSuccess(message) {
    SETUP_STEPS.forEach((s) => {
      if (setupProgress.stepStatus[s.id] !== "error" && setupProgress.stepStatus[s.id] !== "skip") {
        setupProgress.stepStatus[s.id] = "done";
      }
    });
    renderSetupSteps();
    updateSetupProgress(100, message || "Ambiente configurado com sucesso!");
    if (els.setupSubtitle) els.setupSubtitle.textContent = "Tudo pronto — você já pode usar o agente.";
  }

  function finishSetupError(message, options = {}) {
    SETUP_STEPS.forEach((s) => {
      const st = setupProgress.stepStatus[s.id];
      if (st === "active") setupProgress.stepStatus[s.id] = "error";
      else if (st !== "done" && st !== "skip") setupProgress.stepStatus[s.id] = "pending";
    });
    const failed = SETUP_STEPS.find((s) => setupProgress.stepStatus[s.id] === "error");
    if (!failed) {
      const active = SETUP_STEPS.find((s) => setupProgress.stepStatus[s.id] === "active");
      if (active) setupProgress.stepStatus[active.id] = "error";
      else setupProgress.stepStatus.check = "error";
    }
    renderSetupSteps();
    let text = message || "Falha na configuração.";
    const installUrl = options.installUrl || state.setupInstallUrl;
    if (installUrl && els.setupInstallLink) {
      els.setupInstallLink.href = installUrl;
      els.setupInstallLinkWrap?.classList.remove("hidden");
    } else {
      els.setupInstallLinkWrap?.classList.add("hidden");
    }
    updateSetupProgress(setupProgress.lastPercent || 0, text);
    if (els.setupSubtitle) {
      els.setupSubtitle.textContent = installUrl
        ? "Corrija o problema abaixo, instale manualmente ou tente novamente."
        : "Corrija o problema abaixo ou tente novamente.";
    }
  }

  function clearSetupDismissed() {
    try {
      localStorage.removeItem(SETUP_DISMISS_KEY);
    } catch {
      /* private mode */
    }
  }

  function isSetupDismissed() {
    try {
      return localStorage.getItem(SETUP_DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  }

  function dismissSetupPrompt() {
    try {
      localStorage.setItem(SETUP_DISMISS_KEY, "1");
    } catch {
      /* private mode */
    }
  }

  function setupBannerHint() {
    const platform = (state.setupPlatform || "").toLowerCase();
    if (state.ollamaInstalled === false) {
      if (platform === "linux") {
        return "Ollama não detectado. A instalação pode pedir senha sudo no terminal do servidor.";
      }
      if (platform === "darwin") {
        return "Ollama não detectado. Tentaremos instalar via Homebrew ou você pode baixar manualmente.";
      }
      return "Ollama não detectado. Clique em Configurar automaticamente para instalar (winget), iniciar e baixar o modelo.";
    }
    if (!state.models.length) {
      return "Nenhum modelo instalado. Clique abaixo para baixar o recomendado para o seu hardware.";
    }
    return "Clique abaixo para iniciar o Ollama e baixar o modelo recomendado automaticamente.";
  }

  function isModelInstalled(name, installed) {
    if (!name) return false;
    const list = installed || state.models || [];
    if (list.includes(name)) return true;
    const base = String(name).split(":")[0];
    return list.some((m) => m.split(":")[0] === base);
  }

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

  function parseSseBlock(block) {
    const line = block.split("\n").find((l) => l.startsWith("data: "));
    if (!line) return null;
    try {
      return JSON.parse(line.slice(6));
    } catch {
      return null;
    }
  }

  function isApiRouteMissing(data) {
    return data?.error === "not found";
  }

  function outdatedServerMessage() {
    const platform = (state.setupPlatform || navigator.platform || "").toLowerCase();
    const verify = "Confirme em /api/health: platform_version=2 e full_setup_stream=true.";
    if (platform.includes("win")) {
      return (
        "Backend desatualizado (processo antigo na porta 8787). " +
        "Feche o terminal da plataforma (Ctrl+C) e execute:\n" +
        "powershell -ExecutionPolicy Bypass -File .\\scripts\\run-platform.ps1\n" +
        verify
      );
    }
    return (
      "Backend desatualizado (processo antigo na porta 8787). " +
      "Feche o terminal da plataforma (Ctrl+C) e execute:\n" +
      "./scripts/run-platform.sh\n" +
      verify
    );
  }

  async function readJsonResponse(res) {
    return res.json().catch(() => ({}));
  }

  async function checkServerSetupSupport() {
    try {
      const res = await fetch("/api/health");
      const d = await res.json().catch(() => ({}));
      state.serverFeatures = d.features || null;
      state.platformVersion = d.platform_version || null;
      if (d.platform_version >= 2) return true;
      if (d.features?.full_setup_stream === true) return true;
      if (d.features?.ollama_setup_stream === true || d.features?.ollama_auto_install === true) return true;
    } catch {
      /* try setup/status below */
    }

    try {
      const res = await fetch("/api/setup/status");
      if (res.ok) return true;
      const data = await readJsonResponse(res);
      return !isApiRouteMissing(data);
    } catch {
      return false;
    }
  }

  function updateChatHeroVisibility() {
    if (!els.chatHero) return;
    const hasConversation = els.chatMessages.querySelectorAll(".msg.user, .msg.agent").length > 0;
    els.chatHero.classList.toggle("hidden", hasConversation || state.running);
  }

  function updateOllamaOfflineUI() {
    const offline = !state.ollamaOk;
    els.ollamaOfflineBanner?.classList.toggle("hidden", !offline && state.models.length > 0);
    if (els.ollamaBannerTitle) {
      els.ollamaBannerTitle.textContent = state.ollamaInstalled === false
        ? "Ollama não instalado"
        : "Ollama offline";
    }
    if (els.ollamaOfflineText) {
      els.ollamaOfflineText.textContent = setupBannerHint();
    }
    if (els.btnAutoSetup) {
      els.btnAutoSetup.disabled = false;
      els.btnAutoSetup.textContent = state.setupInFlight ? "Configurando..." : "Configurar automaticamente";
    }
    document.querySelectorAll('[data-action="pull"]').forEach((btn) => {
      const model = btn.dataset.model;
      const entry = (state.modelRecommendations?.catalog || []).find((e) => e.ollama_name === model);
      const installed = entry?.installed;
      if (!state.ollamaOk) {
        btn.disabled = false;
        btn.title = "Baixar (Ollama será iniciado/instalado se necessário)";
      } else {
        btn.disabled = !!installed;
        btn.removeAttribute("title");
      }
    });
  }

  async function ensureOllamaViaEnsureEndpoint(showProgress = false) {
    if (showProgress) updateSetupProgress(12, "Conectando ao Ollama (modo compatível)...", "check");
    const res = await fetch("/api/ollama/ensure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ install: true }),
    });
    const data = await readJsonResponse(res);
    if (!res.ok || !data.ok) {
      if (showProgress) {
        if (res.status === 404 && isApiRouteMissing(data)) {
          finishSetupError(outdatedServerMessage());
        } else {
          finishSetupError(data.error || "Falha ao configurar Ollama.", { installUrl: data.install_url });
        }
      }
      state.ollamaOk = false;
      state.ollamaInstalled = data.installed !== false;
      updateOllamaOfflineUI();
      return false;
    }
    state.ollamaInstalled = true;
    if (showProgress) {
      if (data.started || /instal/i.test(data.message || "")) setSetupStep("install", "done");
      else setSetupStep("install", "skip");
      setSetupStep("check", "done");
      setSetupStep("start", "done");
      updateSetupProgress(45, data.message || "Ollama online.");
    }
    await checkHealth();
    return state.ollamaOk;
  }

  async function ensureOllamaRunning(showProgress = false) {
    if (state.ollamaOk) return true;
    if (showProgress && !setupProgress.visible) showSetupModal("Verificando Ollama...", 5);

    try {
      const res = await fetch("/api/ollama/setup/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ install: true }),
      });

      if (res.status === 404) {
        const data = await readJsonResponse(res);
        if (isApiRouteMissing(data)) {
          return ensureOllamaViaEnsureEndpoint(showProgress);
        }
        if (showProgress) {
          finishSetupError(data.error || "Falha ao configurar Ollama.", { installUrl: data.install_url });
        }
        state.ollamaOk = false;
        state.ollamaInstalled = data.installed !== false;
        updateOllamaOfflineUI();
        return false;
      }

      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        if (showProgress) finishSetupError(errData.error || "Falha ao configurar Ollama.", { installUrl: errData.install_url });
        state.ollamaOk = false;
        state.ollamaInstalled = errData.installed !== false;
        updateOllamaOfflineUI();
        return false;
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
          const ev = parseSseBlock(block);
          if (!ev) continue;
          if (ev.type === "started" && showProgress) {
            updateSetupProgress(8, "Conectando ao serviço Ollama...", "check");
          }
          if (ev.type === "status" && showProgress) {
            const step = inferSetupStepFromMessage(ev.message) || "start";
            const pct = step === "install" ? 28 : step === "start" ? 38 : 18;
            updateSetupProgress(pct, ev.message || "Configurando Ollama...", step);
          }
          if (ev.type === "done") donePayload = ev;
        }
      }

      if (!donePayload?.ok) {
        if (showProgress) {
          finishSetupError(donePayload?.error || "Não foi possível configurar o Ollama.", {
            installUrl: donePayload?.install_url,
          });
        }
        state.ollamaOk = false;
        state.ollamaInstalled = donePayload?.installed !== false;
        updateOllamaOfflineUI();
        return false;
      }

      state.ollamaInstalled = true;
      if (showProgress) {
        const msg = donePayload.message || "Ollama online.";
        if (/instal/i.test(msg)) {
          setSetupStep("install", "done");
        } else {
          setSetupStep("install", "skip");
        }
        setSetupStep("check", "done");
        setSetupStep("start", "done");
        updateSetupProgress(45, msg);
      }
      await checkHealth();
      return state.ollamaOk;
    } catch (e) {
      if (showProgress) finishSetupError("Erro: " + e.message);
      return false;
    }
  }

  function getRecommendedModelName() {
    return (
      state.modelRecommendations?.primary?.ollama_name ||
      state.recommendedModel ||
      null
    );
  }

  function showSetupActions(show) {
    els.setupActions?.classList.toggle("hidden", !show);
  }

  function handleSetupStreamEvent(ev, showProgress) {
    if (!ev || !showProgress) return null;

    if (ev.type === "error") {
      finishSetupError(ev.error || "Erro durante a configuração.", { installUrl: ev.install_url });
      showSetupActions(true);
      return false;
    }

    if (ev.type === "phase") {
      const step = SETUP_PHASE_STEP[ev.phase] || "check";
      if (ev.phase === "node") {
        if (ev.npm_available === false) {
          setSetupStep("node", "skip");
          if (ev.install_url && els.setupInstallLink) {
            els.setupInstallLink.href = ev.install_url;
            els.setupInstallLink.textContent = "Instalar Node.js";
            els.setupInstallLinkWrap?.classList.remove("hidden");
          }
        } else if (ev.skipped) {
          setSetupStep("node", "skip");
        } else {
          setSetupStep("node", "done");
        }
      } else if (ev.skipped) {
        setSetupStep(step, "skip");
      } else {
        setSetupStep(step, "active");
      }
      updateSetupProgress(ev.percent ?? setupProgress.lastPercent, ev.message, null);
      if (ev.model && els.setupModelPick) {
        els.setupModelPick.textContent = `Modelo selecionado: ${ev.model}`;
        els.setupModelPick.classList.remove("hidden");
      }
    }

    if (ev.type === "progress") {
      const step = SETUP_PHASE_STEP[ev.phase] || "model";
      updateSetupProgress(ev.percent ?? setupProgress.lastPercent, ev.message, step);
    }

    if (ev.type === "done") {
      if (ev.ok) {
        state.ollamaOk = true;
        state.ollamaInstalled = true;
        clearSetupDismissed();
        if (ev.model) {
          setModelSelection(ev.model);
          applyRecommendedModel(ev.model, ev.models || state.models);
        }
        setSetupStep("config", "done");
        setSetupStep("done", "done");
        finishSetupSuccess(ev.message || "Ambiente configurado — pronto para gerar apps!");
        showSetupActions(false);
        els.setupInstallLinkWrap?.classList.add("hidden");
        hideSetupModal(1200);
        checkHealth();
        loadModelRecommendations().catch(() => {});
        updateOllamaOfflineUI();
      } else {
        finishSetupError(ev.error || ev.message || "Falha na configuração automática.", {
          installUrl: ev.install_url,
        });
        showSetupActions(true);
      }
      return ev.ok;
    }

    return undefined;
  }

  async function runFullSetupStream(options = {}) {
    const { pullRecommended = true, showProgress = true } = options;
    if (showProgress) {
      showSetupModal("Iniciando configuração completa...", 3);
      showSetupActions(false);
    }

    try {
      const res = await fetch("/api/setup/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ install: true, pull_recommended: pullRecommended }),
      });

      if (res.status === 404) {
        const data = await readJsonResponse(res);
        if (isApiRouteMissing(data)) return null;
        if (showProgress) {
          finishSetupError(data.error || "Endpoint de configuração indisponível.", { installUrl: data.install_url });
          showSetupActions(true);
        }
        return false;
      }

      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        if (showProgress) {
          finishSetupError(errData.error || "Falha ao iniciar configuração.");
          showSetupActions(true);
        }
        return false;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let result = undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const ev = parseSseBlock(block);
          if (!ev) continue;
          const handled = handleSetupStreamEvent(ev, showProgress);
          if (handled !== undefined) result = handled;
        }
      }

      return result === true;
    } catch (e) {
      if (showProgress) {
        finishSetupError("Erro: " + e.message);
        showSetupActions(true);
      }
      return false;
    }
  }

  async function ensureEnvironmentLegacy(options = {}) {
    const { pullRecommended = false, showProgress = true } = options;
    const ollamaReady = await ensureOllamaRunning(showProgress);
    if (!ollamaReady) return false;

    if (showProgress) {
      setSetupStep("hardware", "active");
      updateSetupProgress(48, "Analisando hardware e escolhendo modelo recomendado...", "hardware");
    }

    try {
      await loadModelRecommendations();
    } catch {
      /* health may still be enough */
    }

    if (showProgress) setSetupStep("hardware", "done");

    const rec = getRecommendedModelName();
    const needsModel = !state.models.length || (rec && !isModelInstalled(rec, state.models));

    if (pullRecommended && needsModel && rec) {
      const pulled = await pullModel(rec, { setupUI: showProgress, autoConfigure: true });
      if (!pulled) {
        if (showProgress) {
          finishSetupError(`Falha ao baixar o modelo ${rec}.`);
          showSetupActions(true);
        }
        return false;
      }
      await checkHealth();
      if (showProgress) {
        setSetupStep("model", "done");
        setSetupStep("config", "done");
      }
    } else if (rec && isModelInstalled(rec, state.models)) {
      setModelSelection(rec);
      if (els.modelHint) els.modelHint.classList.add("hidden");
      if (showProgress) {
        setSetupStep("model", "skip");
        setSetupStep("config", "active");
        updateSetupProgress(92, `Modelo ${rec} já instalado — configurando...`, "config");
        setSetupStep("config", "done");
      }
    } else if (showProgress) {
      setSetupStep("model", "skip");
      setSetupStep("config", "skip");
    }

    updateOllamaOfflineUI();
    const ok = state.ollamaOk && state.models.length > 0;
    if (ok && showProgress) {
      finishSetupSuccess("Ambiente configurado — pronto para gerar apps!");
      hideSetupModal(1000);
    } else if (!ok && showProgress) {
      showSetupActions(true);
    }
    return ok;
  }

  async function ensureEnvironment(options = {}) {
    const { pullRecommended = true, showProgress = true } = options;
    if (state.setupInFlight) return state.setupInFlight;

    const task = (async () => {
      const supported = await checkServerSetupSupport();
      if (!supported) {
        if (showProgress) {
          showSetupModal("Verificando servidor...", 2);
          finishSetupError(outdatedServerMessage());
          showSetupActions(true);
        }
        return false;
      }

      const full = await runFullSetupStream({ pullRecommended, showProgress });
      if (full !== null) return full;
      return ensureEnvironmentLegacy({ pullRecommended, showProgress });
    })();

    state.setupInFlight = task;
    try {
      return await task;
    } finally {
      state.setupInFlight = null;
    }
  }

  async function clearChat() {
    if (!state.current) return;
    if (!window.confirm("Limpar toda a conversa deste projeto?")) return;
    try {
      await api(`/api/projects/${encodeURIComponent(state.current.id)}/chat`, {
        method: "POST",
        body: JSON.stringify({ clear: true }),
      });
      els.chatMessages.innerHTML = "";
      state.lastReport = "";
      els.reportViewer.classList.remove("report-shell");
      els.reportViewer.textContent = "Nenhuma execução ainda.";
      addMessage(`Projeto "${state.current.name}" aberto. O agente edita arquivos em projects/${state.current.name}.`, "system", false);
      updateChatHeroVisibility();
    } catch (e) {
      addMessage("Erro ao limpar chat: " + e.message, "system");
    }
  }

  async function checkHealth() {
    if (state.healthInFlight) return;
    state.healthInFlight = true;
    try {
      const d = await api("/api/health");
      state.models = d.models || [];
      state.ollamaOk = !!(d.ollama && d.agent);
      state.serverFeatures = d.features || null;
      state.platformVersion = d.platform_version || null;
      updateModelOptions(state.models);
      applyRecommendedModel(d.recommended_model, state.models);
      const modelLabel = getSelectedModel() ? ` · ${getSelectedModel()}` : " · auto";
      const serverOld = !state.platformVersion && !state.serverFeatures?.full_setup_stream;
      const serverHint = serverOld ? ' · <span class="status-warn">backend v1</span>' : "";
      els.healthStatus.innerHTML = `<span class="status-dot ${state.ollamaOk ? "ok" : "err"}"></span>${state.ollamaOk ? "Ollama pronto" : "Ollama offline?"}${modelLabel}${serverHint}`;
      updateOllamaOfflineUI();
    } catch {
      state.ollamaOk = false;
      els.healthStatus.innerHTML = '<span class="status-dot err"></span>offline';
      updateOllamaOfflineUI();
    } finally {
      state.healthInFlight = false;
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
        if (btn.dataset.action === "pull") pullModel(model, { autoConfigure: true, setupUI: true });
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
    updateOllamaOfflineUI();
  }

  function openModelsModal() {
    els.modelsModal.classList.remove("hidden");
    els.pullProgress.classList.add("hidden");
    updateOllamaOfflineUI();
    loadModelRecommendations().catch((e) => {
      els.hardwareGrid.textContent = "Erro: " + e.message;
    });
  }

  function closeModelsModal() {
    if (state.pullingModel) return;
    els.modelsModal.classList.add("hidden");
  }

  async function pullModel(model, options = {}) {
    const { showProgress = true, autoConfigure = false, setupUI = false } = options;
    if (state.pullingModel) return false;

    if (!state.ollamaOk) {
      const ok = await ensureOllamaRunning(showProgress || setupUI);
      if (!ok) {
        if (showProgress && !setupUI) {
          els.pullProgress?.classList.remove("hidden");
          els.pullStatus.textContent = "Ollama offline — use Configurar automaticamente.";
        }
        return false;
      }
    }

    state.pullingModel = true;
    if (setupUI) {
      setSetupStep("model", "active");
      updateSetupProgress(52, `Baixando modelo ${model}...`, "model");
    } else if (showProgress) {
      els.pullProgress?.classList.remove("hidden");
      els.pullBarFill.style.width = "0%";
      els.pullStatus.textContent = `Iniciando download de ${model}...`;
    }

    let success = false;
    try {
      const res = await fetch("/api/models/pull/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 503 || errData.ollama_offline) {
          const started = await ensureOllamaRunning(showProgress || setupUI);
          if (started) return pullModel(model, options);
          state.ollamaOk = false;
          updateOllamaOfflineUI();
          throw new Error(errData.error || "Ollama offline.");
        }
        throw new Error(errData.error || "Falha ao iniciar download");
      }

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
            const pct = ev.percent != null ? Math.round(ev.percent) : null;
            if (setupUI) {
              const overall = pct != null ? 52 + Math.round(pct * 0.4) : 55;
              const label = pct != null
                ? `Baixando ${model}... ${pct}%${ev.status ? " — " + ev.status : ""}`
                : ev.status || `Baixando ${model}...`;
              updateSetupProgress(overall, label, "model");
            } else if (showProgress) {
              if (pct != null) els.pullBarFill.style.width = `${pct}%`;
              els.pullStatus.textContent = ev.status || `Baixando ${model}...`;
            }
          }
          if (ev.type === "done") {
            success = !!ev.ok;
            if (setupUI) {
              if (success) {
                setSetupStep("model", "done");
                setSetupStep("config", "active");
                updateSetupProgress(94, `Modelo ${model} instalado — configurando...`, "config");
              } else {
                finishSetupError(`Falha ao baixar ${model}: ${ev.error || "desconhecido"}`);
              }
            } else if (showProgress) {
              els.pullBarFill.style.width = "100%";
              els.pullStatus.textContent = ev.ok ? `Modelo ${model} pronto!` : `Falha: ${ev.error || "desconhecido"}`;
            }
          }
          if (ev.type === "error") {
            if (ev.ollama_offline) {
              state.ollamaOk = false;
              updateOllamaOfflineUI();
            }
            if (setupUI) finishSetupError("Erro: " + (ev.error || "download falhou"));
            else if (showProgress) els.pullStatus.textContent = "Erro: " + (ev.error || "download falhou");
          }
        }
      }
      await checkHealth();
      await loadModelRecommendations();
      if (success && autoConfigure) {
        setModelSelection(model);
        applyRecommendedModel(model, state.models);
        if (els.modelHint) els.modelHint.classList.add("hidden");
        if (setupUI) setSetupStep("config", "done");
      }
    } catch (e) {
      if (setupUI) finishSetupError("Erro: " + e.message);
      else if (showProgress) els.pullStatus.textContent = "Erro: " + e.message;
      success = false;
    } finally {
      state.pullingModel = false;
    }
    return success;
  }

  // ── Projects ──

  function formatDate(ts) {
    if (!ts) return "";
    return new Date(ts * 1000).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  }

  function closeProjectMenu() {
    document.querySelectorAll(".project-menu").forEach((menu) => menu.remove());
  }

  function renderProjectList() {
    closeProjectMenu();
    els.projectList.innerHTML = "";
    if (!state.projects.length) {
      els.projectList.innerHTML = '<p class="sidebar-empty">Nenhum projeto ainda</p>';
      return;
    }
    state.projects.forEach((p) => {
      const item = document.createElement("div");
      item.className = "project-item" + (state.current?.id === p.id ? " active" : "");
      item.dataset.id = p.id;
      item.innerHTML = `
        <div class="project-item-row">
          <div class="project-item-main">
            <div class="name">${escapeHtml(p.name)}</div>
            <div class="meta">${p.files} arquivos · ${formatDate(p.updated)}</div>
          </div>
          <button type="button" class="project-menu-btn" title="Ações do projeto" aria-label="Ações">⋯</button>
        </div>`;
      item.querySelector(".project-item-main")?.addEventListener("click", () => {
        selectProject(p.id);
        closeSidebar();
      });
      item.querySelector(".project-menu-btn")?.addEventListener("click", (event) => {
        event.stopPropagation();
        openProjectMenu(p, event.currentTarget);
      });
      els.projectList.appendChild(item);
    });
  }

  function openProjectMenu(project, anchor) {
    closeProjectMenu();
    const menu = document.createElement("div");
    menu.className = "project-menu";
    menu.innerHTML = `
      <button type="button" data-action="rename">Renomear</button>
      <button type="button" data-action="duplicate">Duplicar</button>
      <button type="button" data-action="archive" class="danger">Arquivar</button>`;
    menu.addEventListener("click", (event) => {
      event.stopPropagation();
      const btn = event.target.closest("button[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;
      closeProjectMenu();
      if (action === "rename") renameProject(project.id);
      else if (action === "duplicate") duplicateProject(project.id);
      else if (action === "archive") archiveProject(project.id);
    });
    anchor.closest(".project-item")?.appendChild(menu);
    const dismiss = (event) => {
      if (!menu.contains(event.target) && event.target !== anchor) {
        closeProjectMenu();
        document.removeEventListener("click", dismiss);
      }
    };
    setTimeout(() => document.addEventListener("click", dismiss), 0);
  }

  async function renameProject(id) {
    const project = state.projects.find((p) => p.id === id);
    const newName = window.prompt("Novo nome do projeto:", project?.name || "");
    if (!newName?.trim()) return;
    try {
      const d = await api(`/api/projects/${encodeURIComponent(id)}/rename`, {
        method: "POST",
        body: JSON.stringify({ name: newName.trim() }),
      });
      await loadProjects();
      if (state.current?.id === id) {
        await selectProject(d.id || newName.trim());
      }
    } catch (e) {
      alert("Não foi possível renomear: " + e.message);
    }
  }

  async function duplicateProject(id) {
    try {
      const d = await api(`/api/projects/${encodeURIComponent(id)}/duplicate`, {
        method: "POST",
        body: "{}",
      });
      await loadProjects();
      await selectProject(d.id);
    } catch (e) {
      alert("Não foi possível duplicar: " + e.message);
    }
  }

  async function archiveProject(id) {
    if (!window.confirm("Arquivar este projeto? Ele sairá da lista principal.")) return;
    try {
      await api(`/api/projects/${encodeURIComponent(id)}/archive`, {
        method: "POST",
        body: "{}",
      });
      await loadProjects();
      if (state.current?.id === id) {
        if (state.projects.length) await selectProject(state.projects[0].id);
        else showEmptyView();
      }
    } catch (e) {
      alert("Não foi possível arquivar: " + e.message);
    }
  }

  async function loadProjects(q) {
    const query = (q ?? els.projectSearch?.value ?? "").trim();
    const url = query ? `/api/projects?q=${encodeURIComponent(query)}` : "/api/projects";
    const d = await api(url);
    state.projects = d.projects || [];
    renderProjectList();
  }

  async function createProject(name, template) {
    const d = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name, template }),
    });
    await loadProjects();
    const live =
      !!d.has_dev_script || template === "react" || template === "api";
    await selectProject(d.id, {
      preferDev: live,
      autoStart: live,
    });
    const intro =
      template === "api"
        ? "API FastAPI criada. Preview ao vivo (uvicorn /docs) pode ser iniciado no painel."
        : d.has_dev_script || template === "react"
          ? "Projeto React criado. Preview ao vivo iniciando (npm run dev)…"
          : "Projeto criado. Descreva o que quer construir — pedidos de app executam no projeto automaticamente.";
    await persistMessage("system", intro);
  }

  async function selectProject(id, options = {}) {
    const project = state.projects.find((p) => p.id === id);
    if (!project) return;
    state.current = project;
    state.selectedFile = null;
    state.selectedRunId = null;
    state.lastReport = "";
    state.recentChangedFiles = [];
    state.searchMatches = null;
    state.previewMode = "static";
    state.devAutoRestarted = false;
    state.previewLoadRetried = false;
    els.previewMode.value = "static";
    if (els.fileSearchInput) els.fileSearchInput.value = "";
    els.fileEditorShell?.classList.add("hidden");
    if (els.fileViewer) els.fileViewer.value = "";
    state.fileEditorOriginal = "";
    state.fileEditorRevision = null;
    state.fileEditorDirty = false;
    syncFileEditorDirty();
    els.projectTitle.textContent = project.name;
    els.emptyView.classList.add("hidden");
    els.workspaceView.classList.remove("hidden");
    try {
      localStorage.setItem(LAST_PROJECT_KEY, id);
    } catch {
      /* private mode */
    }
    renderProjectList();
    closeSidebar();
    await loadChat();
    await loadRunHistory();
    await loadFiles();
    await refreshDevStatus();
    await maybeEnableDevPreview({ preferDev: options.preferDev, autoStart: !!options.autoStart });
    updatePreview();
    syncDevPolling();
    await resumeActiveRunIfNeeded();
  }

  async function resumeActiveRunIfNeeded() {
    if (!state.current || state.running) return;
    try {
      const info = await api(`/api/projects/${encodeURIComponent(state.current.id)}/active-run`);
      if (!info?.active || !info.run_id) return;
      addMessage(
        `Reconectando à execução${info.goal ? `: ${info.goal}` : ""}…`,
        "system"
      );
      await pollActiveRun(info.run_id, info.goal || "Execução em andamento");
    } catch {
      /* ignore */
    }
  }

  async function pollActiveRun(runId, goal) {
    state.running = true;
    state.runId = runId;
    els.btnSend.disabled = true;
    els.btnCancel?.classList.remove("hidden");
    els.btnCancel.disabled = false;
    const progressEl = addMessage("", "progress");
    const activity = createRunActivity(goal);
    startActivityTimer(progressEl, activity);
    const agentEl = addMessage("Execução retomada — aguardando eventos…", "agent live");
    let after = 0;
    let donePayload = null;
    try {
      while (state.running) {
        const data = await api(`/api/runs/${encodeURIComponent(runId)}/events?after=${after}`);
        const events = data.events || [];
        for (const ev of events) {
          after = Math.max(after, Number(ev._seq || after));
          if (ev.type === "done") {
            donePayload = ev;
            continue;
          }
          handleStreamEvent(ev, progressEl, agentEl, activity);
        }
        if (donePayload || data.active === false) break;
        await new Promise((r) => setTimeout(r, 900));
      }
      stopActivityTimer(activity);
      finishRunActivity(progressEl, activity, donePayload);
      agentEl.classList.remove("live", "thinking");
      if (donePayload) {
        const fullReport = donePayload.report || "(sem relatório)";
        const chatSummary = donePayload.summary || fullReport;
        setMessageContent(agentEl, chatSummary, "agent");
        state.lastReport = fullReport;
        await syncWorkspaceAfterRun(donePayload);
        renderRunArtifacts({
          report: fullReport,
          created_files: donePayload.created_files || [],
          modified_files: donePayload.modified_files || [],
          summary: chatSummary,
        });
        addMessage("Execução retomada e concluída.", "system");
        window.setTimeout(() => removeMessage(progressEl), 4500);
      } else {
        agentEl.textContent = agentEl.textContent || "Execução finalizada.";
      }
    } catch (e) {
      stopActivityTimer(activity);
      agentEl.classList.remove("live", "thinking");
      agentEl.textContent = "Falha ao reconectar: " + (e.message || String(e));
      agentEl.classList.add("error");
    } finally {
      state.running = false;
      state.runId = null;
      els.btnSend.disabled = false;
      els.btnCancel?.classList.add("hidden");
      syncModeControls();
    }
  }

  async function maybeEnableDevPreview({ preferDev = false, autoStart = false } = {}) {
    const hasScript = !!state.devStatus?.has_dev_script;
    if (!hasScript) return false;
    state.previewMode = "dev";
    if (els.previewMode) els.previewMode.value = "dev";
    renderDevControls();
    if (autoStart || preferDev) {
      setPreviewEmptyVisible(
        true,
        state.devStatus?.running
          ? "Preview ao vivo pronto."
          : "Este projeto usa Vite. Inicie o preview ao vivo para ver o app."
      );
    }
    if (autoStart && !state.devStatus?.running && canStartDevPreview()) {
      await startDevServer();
      syncDevPolling();
      return true;
    }
    if (hasScript && state.previewMode === "dev") syncDevPolling();
    return hasScript;
  }

  function showEmptyView() {
    state.current = null;
    stopDevPolling();
    stopPreviewPolling();
    clearPreviewLoadTimer();
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

  function renderMarkdown(text) {
    const src = String(text || "");
    const chunks = [];
    let last = 0;
    const fenceRe = /```(\w*)\n([\s\S]*?)```/g;
    let match;
    while ((match = fenceRe.exec(src)) !== null) {
      if (match.index > last) chunks.push({ type: "text", value: src.slice(last, match.index) });
      chunks.push({ type: "code", value: match[2] });
      last = match.index + match[0].length;
    }
    if (last < src.length) chunks.push({ type: "text", value: src.slice(last) });

    function formatText(part) {
      let html = escapeHtml(part);
      html = html.replace(/^### (.+)$/gm, '<h4 class="md-h">$1</h4>');
      html = html.replace(/^## (.+)$/gm, '<h3 class="md-h">$1</h3>');
      html = html.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/`([^`\n]+)`/g, '<code class="md-inline">$1</code>');
      html = html.replace(/^- (.+)$/gm, '<li class="md-li">$1</li>');
      html = html.replace(/(<li class="md-li">.*?<\/li>(?:<br>)?)+/g, (block) => `<ul class="md-ul">${block}</ul>`);
      html = html.replace(/\n/g, "<br>");
      return html;
    }

    return chunks
      .map((chunk) =>
        chunk.type === "code"
          ? `<pre class="md-code"><code>${escapeHtml(chunk.value)}</code></pre>`
          : formatText(chunk.value)
      )
      .join("");
  }

  function setMessageContent(el, text, role) {
    if (!el) return;
    const useMarkdown = role === "agent" || el.classList.contains("report-viewer");
    if (useMarkdown) el.innerHTML = renderMarkdown(text);
    else el.textContent = text;
  }

  function isMobileLayout() {
    return window.matchMedia("(max-width: 900px)").matches;
  }

  function openSidebar() {
    els.sidebar?.classList.add("sidebar-open");
    els.sidebarBackdrop?.classList.remove("hidden");
  }

  function closeSidebar() {
    els.sidebar?.classList.remove("sidebar-open");
    els.sidebarBackdrop?.classList.add("hidden");
  }

  function syncSidebarToggle() {
    const show = isMobileLayout();
    els.btnToggleSidebar?.classList.toggle("hidden", !show);
    if (!show) closeSidebar();
  }

  function runStatusClass(status) {
    if (!status) return "";
    if (status === "SUCCESS") return "ok";
    if (status === "CANCELLED" || status === "PARTIAL_SUCCESS") return "warn";
    return "err";
  }

  function formatRunTime(ts) {
    if (!ts) return "";
    return new Date(ts * 1000).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function renderRunHistory() {
    if (!els.runHistoryList) return;
    const runs = state.runs || [];
    if (!runs.length) {
      els.runHistoryList.innerHTML = '<li class="run-empty">Nenhuma execução registrada.</li>';
      return;
    }
    els.runHistoryList.innerHTML = runs
      .map((run) => {
        const active = run.id === state.selectedRunId ? " active" : "";
        const goal = escapeHtml((run.goal || run.summary || "Execução").slice(0, 80));
        const status = escapeHtml(run.status || "?");
        const cls = runStatusClass(run.status);
        const changed = [...(run.created_files || []), ...(run.modified_files || [])];
        const count = changed.length;
        return `<li data-run-id="${escapeHtml(run.id)}" class="${active.trim()}">
          <div class="run-status ${cls}">${status}</div>
          <div class="run-goal">${goal}</div>
          <div class="run-meta">${formatRunTime(run.ts)}${count ? ` · ${count} arquivo(s)` : ""}</div>
        </li>`;
      })
      .join("");
    els.runHistoryList.querySelectorAll("[data-run-id]").forEach((item) => {
      item.addEventListener("click", () => selectRun(item.dataset.runId));
    });
  }

  function formatTimelineEvent(ev) {
    if (!ev) return "";
    const type = String(ev.type || ev.status || "?");
    const detail =
      ev.summary ||
      ev.message ||
      ev.analysis ||
      (ev.paths?.length ? ev.paths.join(", ") : "") ||
      (ev.tools?.length ? `${ev.tools.length} ferramenta(s)` : "");
    return detail ? `${type}: ${detail}` : type;
  }

  function renderRunArtifacts(run) {
    if (!els.reportViewer) return;
    const created = run?.created_files || [];
    const modified = run?.modified_files || [];
    const changed = Array.from(new Set([...created, ...modified]));
    const report = run?.report || run?.summary || state.lastReport || "Nenhuma execução ainda.";
    const events = Array.isArray(run?.events) ? run.events : [];

    let html = "";
    if (events.length) {
      html += `
        <div class="run-timeline">
          <div class="run-timeline-title">Linha do tempo</div>
          <ul class="run-timeline-list">
            ${events
              .slice(-12)
              .map(
                (ev) =>
                  `<li class="run-timeline-item"><strong>${escapeHtml(String(ev.type || ev.status || "evento"))}</strong><span>${escapeHtml(formatTimelineEvent(ev).slice(0, 160))}</span></li>`
              )
              .join("")}
          </ul>
        </div>`;
    }
    if (changed.length) {
      html += `
        <div class="run-artifacts">
          <div class="run-artifacts-title">Arquivos desta execução</div>
          <div class="run-artifacts-list">
            ${changed
              .slice(0, 16)
              .map((path) => {
                const createdMark = created.includes(path) ? "criado" : "editado";
                return `<button type="button" class="run-artifact" data-path="${escapeHtml(path)}">
                  <span>${escapeHtml(path)}</span>
                  <em>${createdMark}</em>
                </button>`;
              })
              .join("")}
          </div>
          ${
            run?.has_checkpoint && run?.id
              ? `<button type="button" class="btn btn-ghost btn-sm run-undo" data-run-id="${escapeHtml(run.id)}">Desfazer alterações desta execução</button>`
              : ""
          }
        </div>`;
    }
    html += `<div class="report-body">${renderMarkdown(report)}</div>`;
    els.reportViewer.innerHTML = html;
    els.reportViewer.classList.add("report-viewer", "report-shell");
    els.reportViewer.querySelectorAll(".run-artifact").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!btn.dataset.path) return;
        markChangedFiles([btn.dataset.path]);
        await openFile(btn.dataset.path, {
          switchToFiles: !/\.html?$/i.test(btn.dataset.path),
          preferPreview: /\.html?$/i.test(btn.dataset.path),
        });
      });
    });
    els.reportViewer.querySelector(".run-undo")?.addEventListener("click", async (ev) => {
      const btn = ev.currentTarget;
      const runId = btn?.dataset?.runId;
      if (!runId || !state.current) return;
      if (!window.confirm("Desfazer as alterações desta execução? Arquivos criados serão removidos e os editados voltam ao estado anterior.")) {
        return;
      }
      btn.disabled = true;
      try {
        const res = await api(
          `/api/projects/${encodeURIComponent(state.current.id)}/runs/${encodeURIComponent(runId)}/undo`,
          { method: "POST", body: "{}" }
        );
        addMessage(
          `Desfeito: ${ (res.restored || []).length } restaurado(s), ${ (res.removed || []).length } removido(s).`,
          "system"
        );
        await loadFiles();
        updatePreview();
        switchTab("preview");
      } catch (e) {
        addMessage("Falha ao desfazer: " + (e.message || String(e)), "system");
      } finally {
        btn.disabled = false;
      }
    });
  }

  function selectRun(runId) {
    const run = (state.runs || []).find((r) => r.id === runId);
    if (!run) return;
    state.selectedRunId = runId;
    state.lastReport = run.report || run.summary || "";
    markChangedFiles([...(run.created_files || []), ...(run.modified_files || [])]);
    renderRunHistory();
    renderRunArtifacts(run);
    switchTab("report");
  }

  async function loadRunHistory() {
    if (!state.current) return;
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/runs`);
      state.runs = d.runs || [];
      renderRunHistory();
      if (state.runs.length) {
        state.selectedRunId = state.runs[0].id;
        const selected = state.runs[0];
        state.lastReport = selected.report || selected.summary || "";
        renderRunArtifacts(selected);
        renderRunHistory();
      }
    } catch {
      state.runs = [];
      renderRunHistory();
    }
  }

  async function searchProjectFiles(query) {
    if (!state.current) return;
    const q = String(query || "").trim();
    if (!q) {
      state.searchMatches = null;
      await loadFiles();
      return;
    }
    if (q.length >= 2) {
      try {
        const d = await api(
          `/api/projects/${encodeURIComponent(state.current.id)}/search?q=${encodeURIComponent(q)}`
        );
        if (d.matches?.length) {
          state.searchMatches = d.matches;
          renderFileTree();
          return;
        }
      } catch {
        /* fallback to local filter */
      }
    }
    state.searchMatches = null;
    renderFileTree();
  }

  function openMobilePanel() {
    if (!isMobileLayout()) return;
    els.rightPanel?.classList.add("mobile-open");
    els.mobileBackdrop?.classList.remove("hidden");
    state.mobilePanelOpen = true;
  }

  function closeMobilePanel() {
    els.rightPanel?.classList.remove("mobile-open");
    els.mobileBackdrop?.classList.add("hidden");
    state.mobilePanelOpen = false;
  }

  function syncMobileTabs(name) {
    document.querySelectorAll(".mobile-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.tab === name);
    });
  }

  function renderChat(messages) {
    els.chatMessages.innerHTML = "";
    if (!messages.length) {
      addMessage(`Projeto "${state.current.name}" aberto. O agente edita arquivos em projects/${state.current.name}.`, "system", false);
      updateChatHeroVisibility();
      return;
    }
    messages.forEach((m) => addMessage(m.text, m.role, false));
    updateChatHeroVisibility();
  }

  async function loadChat() {
    if (!state.current) return;
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/chat`);
      renderChat(d.messages || []);
      const lastAgent = [...(d.messages || [])].reverse().find((m) => m.role === "agent");
      if (lastAgent) {
        state.lastReport = lastAgent.text;
        setMessageContent(els.reportViewer, lastAgent.text, "agent");
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

  function setThinkingState(el) {
    if (!el) return;
    el.classList.add("live", "thinking");
    el.innerHTML = `
      <div class="thinking-indicator" aria-live="polite" aria-label="pensando">
        <svg class="thinking-brain" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M8.5 4.5c-1.7 0-3 1.4-3 3.1 0 .4.1.8.2 1.1A3.2 3.2 0 0 0 4 11.7c0 1.5 1 2.7 2.4 3.1v.2c0 1.9 1.4 3.5 3.3 3.5h.3c.6 1.1 1.8 1.8 3.1 1.8s2.5-.7 3.1-1.8h.2c1.9 0 3.4-1.6 3.4-3.5v-.1A3.3 3.3 0 0 0 22 11.5a3.2 3.2 0 0 0-2.1-3 3 3 0 0 0 .2-1.1c0-1.7-1.3-3.1-3-3.1-.6 0-1.1.2-1.6.4A3.8 3.8 0 0 0 12 3.5c-1.3 0-2.5.7-3.1 1.7-.5-.4-1.1-.7-1.4-.7Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M12 8.5v7M9.5 10.5c.8-.6 1.7-.9 2.5-.9s1.7.3 2.5.9M9.5 13.5c.8.6 1.7.9 2.5.9s1.7-.3 2.5-.9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <span class="thinking-label">pensando...</span>
      </div>`;
  }

  function clearThinkingState(el) {
    if (!el || !el.classList.contains("thinking")) return;
    el.classList.remove("thinking");
    el.textContent = "";
  }

  function addMessage(text, role, scroll = true) {
    const el = document.createElement("div");
    el.className = "msg " + role + (role === "agent" && /^Erro/i.test(text) ? " error" : "");
    if (/\blive\b/.test(role) && !String(text || "").trim()) {
      setThinkingState(el);
    } else {
      setMessageContent(el, text, role);
    }
    els.chatMessages.appendChild(el);
    if (scroll) els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    if (role === "user" || role.startsWith("agent")) updateChatHeroVisibility();
    return el;
  }

  function removeMessage(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  const ACTIVITY_PHASES = [
    { id: "prepare", label: "Preparar" },
    { id: "plan", label: "Planejar" },
    { id: "think", label: "Modelo" },
    { id: "work", label: "Executar" },
    { id: "check", label: "Validar" },
    { id: "done", label: "Final" },
  ];

  function createRunActivity(prompt) {
    return {
      prompt,
      startedAt: Date.now(),
      stage: "Preparando",
      detail: "Conferindo ambiente, projeto e modelo selecionado.",
      phaseId: "prepare",
      model: getSelectedModel() || state.recommendedModel || "auto",
      runId: null,
      step: 0,
      maxSteps: parseInt(els.maxStepsInput?.value || "20", 10),
      task: "",
      planSummary: "",
      taskCount: null,
      tools: [],
      okTools: 0,
      toolCount: 0,
      reflection: "",
      llmChars: 0,
      files: [],
      finished: false,
      events: [],
      timer: null,
      fileRefreshTimer: null,
    };
  }

  function formatDuration(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const min = Math.floor(total / 60);
    const sec = total % 60;
    return min ? `${min}m ${String(sec).padStart(2, "0")}s` : `${sec}s`;
  }

  function estimateRemaining(activity) {
    if (activity.finished) return "concluído";
    if (!activity.step || !activity.maxSteps) return "calculando";
    const elapsed = Date.now() - activity.startedAt;
    const progress = Math.min(0.92, Math.max(0.08, activity.step / activity.maxSteps));
    const totalEstimate = elapsed / progress;
    const remaining = Math.max(0, totalEstimate - elapsed);
    if (remaining < 5000) return "menos de 5s";
    return "~" + formatDuration(remaining);
  }

  function activityPhaseMeta(activity) {
    const stage = String(activity?.stage || "").toLowerCase();
    if (activity?.finished || /conclu|finaliz/.test(stage)) return { cls: "ok", label: "concluído", phaseId: "done" };
    if (/erro|falha/.test(stage)) return { cls: "err", label: "precisa de atenção", phaseId: activity?.phaseId || "work" };
    if (/cancel/.test(stage)) return { cls: "warn", label: "cancelando", phaseId: "done" };
    if (/plano|planej|criando plano/.test(stage)) return { cls: "think", label: "planejando", phaseId: "plan" };
    if (/modelo|gerando/.test(stage)) return { cls: "think", label: "modelo pensando", phaseId: "think" };
    if (/ferrament/.test(stage)) return { cls: "work", label: "executando", phaseId: "work" };
    if (/valid|avaliando|reflet/.test(stage)) return { cls: "check", label: "checando", phaseId: "check" };
    if (/iniciado|prepar/.test(stage)) return { cls: "work", label: "preparando", phaseId: "prepare" };
    return { cls: "work", label: "trabalhando", phaseId: activity?.phaseId || "work" };
  }

  function renderActivityPhases(phaseId) {
    const currentIdx = Math.max(0, ACTIVITY_PHASES.findIndex((p) => p.id === phaseId));
    return ACTIVITY_PHASES.map((phase, idx) => {
      let status = "pending";
      if (idx < currentIdx) status = "done";
      else if (idx === currentIdx) status = "active";
      return `<li class="activity-phase activity-phase--${status}">${escapeHtml(phase.label)}</li>`;
    }).join("");
  }

  function addActivityEvent(activity, label, detail) {
    const cleanLabel = String(label || "Evento").trim();
    const cleanDetail = String(detail || "").trim();
    const last = activity.events[activity.events.length - 1];
    if (last && last.label === cleanLabel && last.detail === cleanDetail) return;
    activity.events.push({
      time: Date.now(),
      label: cleanLabel,
      detail: cleanDetail,
    });
    activity.events = activity.events.slice(-8);
  }

  function updateActivity(activity, patch = {}) {
    Object.assign(activity, patch);
    if (patch.stage || patch.detail) {
      addActivityEvent(activity, patch.stage || activity.stage, patch.detail || activity.detail);
    }
  }

  function scheduleFileRefresh(activity) {
    if (!activity || activity.fileRefreshTimer) return;
    activity.fileRefreshTimer = window.setTimeout(() => {
      activity.fileRefreshTimer = null;
      loadFiles().catch(() => {});
    }, 700);
  }

  function renderRunActivity(progressEl, activity) {
    if (!progressEl || !activity) return;
    const elapsed = formatDuration(Date.now() - activity.startedAt);
    const remaining = estimateRemaining(activity);
    const stepPct = activity.finished
      ? 100
      : activity.maxSteps
        ? Math.min(100, Math.round((activity.step / activity.maxSteps) * 100))
        : 0;
    const phase = activityPhaseMeta(activity);
    activity.phaseId = phase.phaseId;
    const tools = activity.tools.length ? activity.tools.join(", ") : "nenhuma ainda";
    const files = activity.files.length ? activity.files.slice(-6).join(", ") : "";
    const recent = activity.events
      .slice()
      .reverse()
      .map((event) => {
        const ago = formatDuration(Date.now() - event.time);
        return `<li><span>${escapeHtml(ago)}</span><strong>${escapeHtml(event.label)}</strong>${event.detail ? `<em>${escapeHtml(event.detail)}</em>` : ""}</li>`;
      })
      .join("");

    progressEl.innerHTML = `
      <div class="agent-activity agent-activity--${phase.cls}">
        <div class="activity-head">
          <div>
            <div class="activity-kicker">${escapeHtml(phase.label)}</div>
            <div class="activity-title">${escapeHtml(activity.stage)}</div>
          </div>
          <div class="activity-time">
            <strong>${escapeHtml(elapsed)}</strong>
            <span>${activity.finished ? "tempo total" : `restante ${escapeHtml(remaining)}`}</span>
          </div>
        </div>
        <ol class="activity-phases">${renderActivityPhases(phase.phaseId)}</ol>
        <div class="activity-detail">${escapeHtml(activity.detail || "Aguardando próxima ação...")}</div>
        <div class="activity-bar"><span style="width:${stepPct}%"></span></div>
        <div class="activity-grid">
          <div><span>Modelo</span><strong>${escapeHtml(activity.model || "auto")}</strong></div>
          <div><span>Passo</span><strong>${activity.step || 0}/${activity.maxSteps || "?"}</strong></div>
          <div><span>Ferramentas</span><strong>${activity.okTools || 0}/${activity.toolCount || 0}</strong></div>
        </div>
        ${activity.task ? `<div class="activity-current"><span>Tarefa atual</span>${escapeHtml(activity.task)}</div>` : ""}
        ${activity.planSummary ? `<div class="activity-current"><span>Plano</span>${escapeHtml(activity.planSummary)}${activity.taskCount ? ` (${activity.taskCount} tarefas)` : ""}</div>` : ""}
        <div class="activity-current"><span>Últimas ferramentas</span>${escapeHtml(tools)}</div>
        ${files ? `<div class="activity-current"><span>Arquivos alterados</span>${escapeHtml(files)}</div>` : ""}
        ${activity.reflection ? `<div class="activity-current"><span>Leitura do agente</span>${escapeHtml(activity.reflection)}</div>` : ""}
        <ol class="activity-log">${recent}</ol>
      </div>
    `;
  }

  function startActivityTimer(progressEl, activity) {
    renderRunActivity(progressEl, activity);
    activity.timer = window.setInterval(() => renderRunActivity(progressEl, activity), 1000);
  }

  function stopActivityTimer(activity) {
    if (activity?.timer) {
      window.clearInterval(activity.timer);
      activity.timer = null;
    }
    if (activity?.fileRefreshTimer) {
      window.clearTimeout(activity.fileRefreshTimer);
      activity.fileRefreshTimer = null;
    }
  }

  function finishRunActivity(progressEl, activity, donePayload) {
    if (!activity) return;
    stopActivityTimer(activity);
    const created = donePayload?.created_files || [];
    const modified = donePayload?.modified_files || [];
    const changed = [...created, ...modified].filter(Boolean);
    if (changed.length) {
      activity.files = Array.from(new Set([...(activity.files || []), ...changed])).slice(-12);
    }
    const cancelled = donePayload?.status === "CANCELLED";
    updateActivity(activity, {
      finished: true,
      phaseId: "done",
      stage: cancelled ? "Execução cancelada" : "Execução concluída",
      detail: cancelled
        ? "O agente parou a pedido do usuário."
        : changed.length
          ? `Pronto. ${changed.length} arquivo(s) alterado(s).`
          : "Pronto. Relatório final disponível abaixo.",
      step: activity.maxSteps || activity.step,
    });
    renderRunActivity(progressEl, activity);
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

    const offlineScaffold = looksLikeOfflineScaffoldGoal(prompt);
    let ready = !!state.ollamaOk;
    if (!ready && !offlineScaffold) {
      ready = await ensureEnvironment({
        pullRecommended: true,
        showProgress: true,
      });
    } else if (!ready && offlineScaffold) {
      // Soft health refresh without blocking on Ollama install.
      try {
        await checkHealth();
        ready = !!state.ollamaOk;
      } catch (_) {
        ready = false;
      }
    }
    if (!ready && !offlineScaffold) {
      addMessage(
        "Ambiente não configurado. Use Modelos IA → Configurar automaticamente (Ollama + modelo recomendado).",
        "system"
      );
      openModelsModal();
      state.pendingPrompt = prompt;
      return;
    }
    if (!ready && offlineScaffold) {
      addMessage(
        "Ollama offline — vou criar o starter (HTML/React/API) sem modelo. Depois você pode melhorar com IA.",
        "system"
      );
    }

    const mode = els.modeSelect?.value || "chat";
    if (mode === "chat") {
      if (looksLikeStrongCreateIntent(prompt) || (offlineScaffold && looksLikeCodeRequest(prompt))) {
        if (els.modeSelect) els.modeSelect.value = "execute";
        syncModeControls();
        addMessage(
          "Pedido claro de criação — executando no projeto.",
          "system"
        );
        return sendAgentPrompt(prompt, "execute");
      }
      if (looksLikeCodeRequest(prompt)) {
        addMessage(prompt, "user");
        els.promptInput.value = "";
        updateChatHeroVisibility();
        persistMessage("user", prompt).catch(() => {});
        addExecuteHandoff(
          prompt,
          "Isso parece um pedido para criar ou editar código. No Chat eu só converso — para alterar arquivos, execute:"
        );
        return;
      }
      return sendChatPrompt(prompt);
    }
    if (looksLikeConversationOnly(prompt)) {
      if (els.modeSelect) els.modeSelect.value = "chat";
      syncModeControls();
      addMessage(
        "Isso parece só uma conversa — mudei para Chat (rápido). Use Executar código quando quiser alterar arquivos.",
        "system"
      );
      return sendChatPrompt(prompt);
    }
    return sendAgentPrompt(prompt, mode);
  }

  function looksLikeConversationOnly(text) {
    const t = String(text || "").trim();
    if (!t) return false;
    if (looksLikeCodeRequest(t)) return false;
    const lower = t.toLowerCase();
    if (t.length <= 120) {
      if (/^(oi|ol[aá]|iae|e a[ií]|hey|hi|hello|bom dia|boa tarde|boa noite)\b/i.test(lower)) return true;
      if (/^(tudo bem|como vai|obrigad[oa]|valeu|ok|beleza)\b/i.test(lower)) return true;
      if (
        /\b(pergunt|d[uú]vida|s[oó] (quero )?pergunt|conversar|me explica|explique|o que (é|e)|como funciona|por\s*qu[eê]|voc[eê] (é|e|pode))\b/i.test(
          lower
        )
      ) {
        return true;
      }
    }
    return t.length <= 40 && !/[./\\]|\.(html|css|js|ts|py|tsx)\b/i.test(t);
  }

  function looksLikeOfflineScaffoldGoal(text) {
    const t = String(text || "").toLowerCase();
    if (!t) return false;
    const react = /\b(react|vite|next\.?js)\b/.test(t) && /\b(cri(e|ar)|faz(er)?|mont(e|ar)|app|aplicat|site|dashboard)\b/.test(t);
    const api = /\b(fastapi|api rest|endpoint|\/health|backend python)\b/.test(t) && /\b(cri(e|ar)|faz(er)?|implement|mont(e|ar))\b/.test(t);
    const plain =
      !/\b(react|vite|fastapi|flask|django)\b/.test(t) &&
      (/\bhtml\b/.test(t) && /\b(css|javascript|\bjs\b)\b/.test(t) ||
        /\b(html|css|javascript|site|p[aá]gina|landing|aplicat|app)\b/.test(t)) &&
      /\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?|pequena|simples|mini|melhor(e|ar)|adicion|alter|edit)\b/.test(t);
    return react || api || plain;
  }

  function looksLikeStrongCreateIntent(text) {
    const t = String(text || "").toLowerCase().trim();
    if (t.length < 14) return false;
    return (
      /\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?)\b/.test(t) &&
      /\b(app|aplicat|site|landing|dashboard|api|react|html|p[aá]gina)\b/.test(t)
    );
  }

  function looksLikeCodeRequest(text) {

    const t = String(text || "").toLowerCase().trim();
    if (t.length < 12) return false;
    // Pure questions / explanations stay in Chat even if they mention "site"/"app".
    if (
      /^(me )?(explica|explique|o que|qual|como funciona|por\s*qu[eê]|pode (me )?(dizer|explicar))\b/i.test(t) ||
      (/\b(me explica|o que (é|e|significa)|s[oó] (uma )?pergunt|como funciona)\b/i.test(t) &&
        !/\b(cri(e|ar)|implement|adicion|alter|edit|corrig|refator|melhor(e|ar)|faz(er)?)\b/i.test(t))
    ) {
      return false;
    }
    const hasAction =
      /\b(cri(e|ar)|faz(er)?|implement(e|ar)?|adicion(e|ar)?|alter(e|ar)?|edit(e|ar)?|corrig(a|ir)?|refator(e|ar)?|melhor(e|ar)|redesenh(e|ar)?|build|gera(r)?|escrev(a|er)|mont(e|ar)|atualiz(e|ar))\b/i.test(
        t
      );
    const hasTarget =
      /\b(landing|website|site|app|aplicativ|html|css|react|vite|api|arquivo|c[oó]digo|componente|p[aá]gina|endpoint|fun[cç][aã]o|layout|ui|ux|dashboard|backend|frontend|visual|estilo|navbar|hero|formul[aá]rio)\b/i.test(
        t
      );
    return hasAction && hasTarget;
  }

  function addExecuteHandoff(prompt, reason) {
    const el = document.createElement("div");
    el.className = "msg system next-steps";
    el.innerHTML = `
      <div class="next-steps-card">
        <div class="next-steps-title">${escapeHtml(reason || "Quer que o agente edite o projeto?")}</div>
        <div class="next-steps-actions">
          <button type="button" class="btn btn-primary btn-gradient btn-sm handoff-execute">Executar este pedido</button>
          <button type="button" class="btn btn-ghost btn-sm handoff-stay">Continuar no Chat</button>
        </div>
      </div>`;
    el.querySelector(".handoff-execute")?.addEventListener("click", () => {
      if (els.modeSelect) els.modeSelect.value = "execute";
      syncModeControls();
      els.promptInput.value = prompt;
      removeMessage(el);
      sendPrompt();
    });
    el.querySelector(".handoff-stay")?.addEventListener("click", () => removeMessage(el));
    els.chatMessages.appendChild(el);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return el;
  }

  async function sendChatPrompt(prompt) {
    state.pendingPrompt = null;
    addMessage(prompt, "user");
    els.promptInput.value = "";
    updateChatHeroVisibility();
    state.running = true;
    state.runId = null;
    state.abortController = new AbortController();
    els.btnSend.disabled = true;
    els.btnCancel?.classList.remove("hidden");
    els.btnCancel.disabled = true;

    const statusEl = addMessage("Respondendo…", "progress");
    const agentEl = addMessage("", "agent live");
    let wasAbort = false;
    let fullText = "";

    try {
      await persistMessage("user", prompt);
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: state.abortController.signal,
        body: JSON.stringify({
          prompt,
          workspace: state.current.path,
          model: getSelectedModel() || "",
        }),
      });

      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        const err = new Error(errData.error || "Falha no chat");
        err.data = errData;
        err.status = res.status;
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
          const ev = parseSseBlock(block);
          if (!ev) continue;
          if (ev.type === "started" && ev.run_id) {
            state.runId = ev.run_id;
            els.btnCancel.disabled = false;
            statusEl.textContent = `Chat · ${ev.model || "auto"} · primeira resposta pode demorar se o modelo estiver a carregar…`;
          } else if (ev.type === "chat_chunk" && ev.text) {
            if (statusEl.isConnected) statusEl.textContent = `Chat · respondendo…`;
            clearThinkingState(agentEl);
            fullText += ev.text;
            agentEl.textContent = fullText;
            els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
          } else if (ev.type === "error") {
            throw Object.assign(new Error(ev.error || ev.message || "Erro no chat"), { data: ev });
          } else if (ev.type === "cancelled") {
            statusEl.textContent = "Chat cancelado";
          } else if (ev.type === "done") {
            donePayload = ev;
          }
        }
      }

      removeMessage(statusEl);
      agentEl.classList.remove("live", "thinking");
      const finalText = (donePayload?.summary || donePayload?.report || fullText || "").trim();
      if (donePayload?.status === "CANCELLED") {
        agentEl.textContent = finalText || "Chat cancelado.";
        agentEl.classList.add("error");
      } else if (finalText) {
        setMessageContent(agentEl, finalText, "agent");
        if (/executar c[oó]digo|modo executar|mudar o seletor|para criar\/editar/i.test(finalText)) {
          addExecuteHandoff(prompt, "O assistente sugeriu executar o pedido no projeto:");
        }
      } else {
        agentEl.textContent = "Sem resposta do modelo.";
      }
    } catch (e) {
      removeMessage(statusEl);
      agentEl.classList.remove("live", "thinking");
      if (e.status === 409 || e.data?.busy) {
        agentEl.textContent = e.message || "Já existe uma execução neste projeto.";
        agentEl.classList.add("error");
      } else if (e.name === "AbortError") {
        wasAbort = true;
        agentEl.textContent = "Chat cancelado.";
        agentEl.classList.add("error");
      } else if (e.status === 503 || e.data?.ollama_offline) {
        const ready = await ensureEnvironment({ pullRecommended: true, showProgress: true });
        if (ready) {
          els.promptInput.value = prompt;
          state.running = false;
          removeMessage(agentEl);
          return sendChatPrompt(prompt);
        }
        agentEl.textContent = "Erro: Ollama offline.";
        agentEl.classList.add("error");
        openModelsModal();
      } else {
        const raw = String(e.message || "erro desconhecido");
        const isNetwork =
          e.name === "TypeError" ||
          /failed to fetch|networkerror|network error|load failed|fetch/i.test(raw);
        agentEl.textContent = isNetwork
          ? "Erro de conexão com o servidor. Reinicie a plataforma e tente de novo."
          : /404|n[aã]o encontrado|model.*not found/i.test(raw)
            ? "Modelo indisponível no Ollama. Mude para Auto (recomendado) ou outro modelo instalado e tente de novo."
            : "Erro: " + raw;
        agentEl.classList.add("error");
        await persistMessage("agent", agentEl.textContent).catch(() => {});
      }
    } finally {
      state.running = false;
      state.runId = null;
      state.abortController = null;
      els.btnSend.disabled = false;
      els.btnCancel?.classList.add("hidden");
      els.btnCancel.disabled = false;
      updateChatHeroVisibility();
      syncModeControls();
      if (wasAbort) {
        await new Promise((r) => setTimeout(r, 400));
        await loadChat().catch(() => {});
      }
      els.promptInput.focus();
    }
  }

  async function sendAgentPrompt(prompt, mode, opts = {}) {
    if (!opts.offlineRetry) {
      state._offlineScaffoldRetried = false;
    }
    state.pendingPrompt = null;
    addMessage(prompt, "user");
    els.promptInput.value = "";
    updateChatHeroVisibility();
    state.running = true;
    state.runId = null;
    state.abortController = new AbortController();
    state.llmPreviewChars = 0;
    els.btnSend.disabled = true;
    els.btnCancel?.classList.add("hidden");
    els.btnCancel?.classList.remove("hidden");
    els.btnCancel.disabled = true;

    const progressEl = addMessage("", "progress");
    const activity = createRunActivity(prompt);
    startActivityTimer(progressEl, activity);
    const agentEl = addMessage("", "agent live");
    let wasAbort = false;

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
          max_steps: parseInt(els.maxStepsInput.value || "20", 10),
          plan_only: mode === "plan",
          dry_run: mode === "dry",
        }),
      });

      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        const err = new Error(errData.error || "Falha no streaming");
        err.data = errData;
        err.status = res.status;
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
          const ev = parseSseBlock(block);
          if (!ev) continue;
          if (ev.type === "done") {
            donePayload = ev;
            continue;
          }
          handleStreamEvent(ev, progressEl, agentEl, activity);
        }
      }

      stopActivityTimer(activity);
      finishRunActivity(progressEl, activity, donePayload);
      agentEl.classList.remove("live", "thinking");

      if (donePayload) {
        const fullReport = donePayload.report || "(sem relatório)";
        const chatSummary = donePayload.summary || fullReport;
        setMessageContent(agentEl, chatSummary, "agent");
        state.lastReport = fullReport;
        if (donePayload.status === "CANCELLED") {
          agentEl.classList.add("error");
        }
        await syncWorkspaceAfterRun(donePayload);
        renderRunArtifacts({
          report: fullReport,
          created_files: donePayload.created_files || [],
          modified_files: donePayload.modified_files || [],
          summary: chatSummary,
        });
        window.setTimeout(() => removeMessage(progressEl), 4500);
      } else {
        agentEl.textContent = agentEl.textContent || "Execução finalizada sem relatório.";
        window.setTimeout(() => removeMessage(progressEl), 2500);
      }
    } catch (e) {
      stopActivityTimer(activity);
      removeMessage(progressEl);
      agentEl.classList.remove("live", "thinking");
      if (e.status === 409 || e.data?.busy) {
        agentEl.textContent = e.message || "Agente já em execução neste projeto.";
        agentEl.classList.add("error");
        addMessage("Aguarde a execução atual terminar ou cancele antes de enviar outro prompt.", "system");
      } else if (e.name === "AbortError") {
        wasAbort = true;
        agentEl.textContent = "Cancelando...";
        agentEl.classList.add("error");
      } else if (e.status === 503 || e.data?.ollama_offline) {
        // Offline scaffolds should pass preflight; one soft retry only (avoid loops).
        if (
          looksLikeOfflineScaffoldGoal(prompt) &&
          mode !== "plan" &&
          !state._offlineScaffoldRetried
        ) {
          state._offlineScaffoldRetried = true;
          state.ollamaOk = false;
          updateOllamaOfflineUI();
          els.promptInput.value = prompt;
          state.running = false;
          removeMessage(agentEl);
          removeMessage(progressEl);
          addMessage(
            "Ollama offline — tentando scaffold determinístico (HTML/React/API)…",
            "system"
          );
          return sendAgentPrompt(prompt, mode, { offlineRetry: true });
        }
        state._offlineScaffoldRetried = false;
        const ready = await ensureEnvironment({ pullRecommended: true, showProgress: true });
        if (ready) {
          els.promptInput.value = prompt;
          state.running = false;
          removeMessage(agentEl);
          removeMessage(progressEl);
          return sendAgentPrompt(prompt, mode);
        }
        state.ollamaOk = false;
        updateOllamaOfflineUI();
        const err = e.message || "Ollama offline.";
        agentEl.textContent = "Erro: " + err;
        agentEl.classList.add("error");
        openModelsModal();
      } else {
        const raw = String(e.message || "erro desconhecido");
        const isNetwork =
          e.name === "TypeError" ||
          /failed to fetch|networkerror|network error|load failed|fetch/i.test(raw);
        const err = isNetwork
          ? "Erro de conexão com o servidor. Reinicie a plataforma (porta 8787) e tente de novo. Se o modelo for grande, a 1ª resposta pode demorar alguns minutos."
          : "Erro: " + raw;
        agentEl.textContent = err;
        agentEl.classList.add("error");
        if (e.data?.missing_model) {
          addMessage(`Modelo ausente: ${e.data.model}. Baixando automaticamente...`, "system");
          openModelsModal();
          if (e.data.model) {
            const pulled = await pullModel(e.data.model, { autoConfigure: true, showProgress: true });
            if (pulled) {
              els.promptInput.value = prompt;
              state.running = false;
              removeMessage(agentEl);
              removeMessage(progressEl);
              return sendAgentPrompt(prompt, mode);
            }
          }
        }
        await persistMessage("agent", err).catch(() => {});
      }
    } finally {
      stopActivityTimer(activity);
      state.running = false;
      state.runId = null;
      state.abortController = null;
      state.llmPreviewChars = 0;
      els.btnSend.disabled = false;
      els.btnCancel?.classList.add("hidden");
      els.btnCancel.disabled = false;
      updateChatHeroVisibility();
      syncModeControls();
      if (wasAbort) {
        await new Promise((r) => setTimeout(r, 400));
        await loadChat().catch(() => {});
      }
      els.promptInput.focus();
    }
  }

  function handleStreamEvent(ev, progressEl, agentEl, activity) {
    switch (ev.type) {
      case "started":
        if (ev.run_id) {
          state.runId = ev.run_id;
          if (els.btnCancel) els.btnCancel.disabled = false;
        }
        updateActivity(activity, {
          runId: ev.run_id || activity.runId,
          phaseId: "prepare",
          stage: "Agente iniciado",
          detail: `Run ${ev.run_id || ""} aberto. Preparando leitura do projeto e contexto da conversa.`.trim(),
        });
        break;
      case "cancelled":
        updateActivity(activity, {
          phaseId: "done",
          stage: "Cancelando",
          detail: "Pedido de cancelamento enviado. Aguardando o agente parar no próximo ponto seguro.",
        });
        break;
      case "planning":
        updateActivity(activity, {
          phaseId: "plan",
          stage: "Criando plano",
          detail: ev.message || "Lendo o projeto e montando uma sequência segura de tarefas.",
        });
        break;
      case "plan":
        updateActivity(activity, {
          phaseId: "plan",
          stage: "Plano criado",
          detail: "O agente terminou de decidir a estratégia e vai executar as tarefas uma por uma.",
          planSummary: ev.summary || "Plano criado",
          taskCount: ev.task_count || null,
        });
        break;
      case "step":
        updateActivity(activity, {
          phaseId: "think",
          stage: "Executando tarefa",
          detail: `Passo ${ev.step}/${ev.max_steps}: ${ev.task_title || ev.task_id || "tarefa"}`,
          step: ev.step || activity.step,
          maxSteps: ev.max_steps || activity.maxSteps,
          task: ev.task_title || ev.task_id || "",
          tools: [],
          okTools: 0,
          toolCount: 0,
          reflection: "",
        });
        agentEl.textContent = "";
        setThinkingState(agentEl);
        break;
      case "llm_chunk":
        updateActivity(activity, {
          phaseId: "think",
          stage: "Modelo gerando a próxima ação",
          detail: "Aguardando o Ollama responder com as ferramentas que o agente deve usar.",
          llmChars: (activity.llmChars || 0) + (ev.text ? ev.text.length : 0),
        });
        if (ev.text && agentEl) {
          clearThinkingState(agentEl);
          state.llmPreviewChars = Math.min(state.llmPreviewChars + ev.text.length, 2000);
          agentEl.textContent = (agentEl.textContent + ev.text).slice(-2000);
        }
        break;
      case "tools_start":
        updateActivity(activity, {
          phaseId: "work",
          stage: "Executando ferramentas",
          detail: `${ev.count || 0} chamada(s) em andamento: ${(ev.tools || []).join(", ") || "preparando"}.`,
          tools: ev.tools || [],
          toolCount: ev.count || 0,
          okTools: 0,
        });
        break;
      case "tools":
        updateActivity(activity, {
          phaseId: "work",
          stage: "Ferramentas executadas",
          detail: `${ev.ok || 0} de ${ev.count || 0} chamadas concluíram com sucesso.`,
          tools: ev.tools || [],
          okTools: ev.ok || 0,
          toolCount: ev.count || 0,
        });
        break;
      case "files_changed": {
        const paths = [...(ev.paths || []), ...(ev.created || []), ...(ev.modified || [])].filter(Boolean);
        const unique = Array.from(new Set([...(activity.files || []), ...paths])).slice(-12);
        markChangedFiles(paths);
        updateActivity(activity, {
          phaseId: "work",
          stage: "Arquivos atualizados",
          detail: paths.length
            ? `Alterações em: ${paths.slice(0, 4).join(", ")}${paths.length > 4 ? "…" : ""}`
            : "Arquivos do projeto foram atualizados.",
          files: unique,
        });
        scheduleFileRefresh(activity);
        if (paths.some(isUiPath)) {
          window.setTimeout(() => updatePreview(paths.find((p) => /\.html?$/i.test(p)) || findPreviewPath()), 800);
        }
        break;
      }
      case "validation_start":
        updateActivity(activity, {
          phaseId: "check",
          stage: "Validando alterações",
          detail: `Rodando: ${(ev.commands || []).join(", ") || "validações automáticas"}.`,
        });
        break;
      case "validation":
        updateActivity(activity, {
          phaseId: "check",
          stage: "Validação concluída",
          detail: `${ev.ok || 0} de ${ev.count || 0} validações passaram.`,
          reflection: ev.summary || activity.reflection,
        });
        break;
      case "reflection":
        updateActivity(activity, {
          phaseId: "check",
          stage: "Avaliando resultado",
          detail: `Decisão: ${ev.status || "continue"}`,
          reflection: (ev.analysis || "").slice(0, 180),
        });
        break;
      case "error":
        updateActivity(activity, {
          stage: "Erro encontrado",
          detail: ev.message || ev.error || "Erro desconhecido durante a execução.",
        });
        break;
      default:
        break;
    }
    renderRunActivity(progressEl, activity);
  }

  // ── Files ──

  function fileKind(name) {
    if (/\.html?$/i.test(name)) return { label: "HTML", cls: "html" };
    if (/\.(css|scss)$/i.test(name)) return { label: "CSS", cls: "css" };
    if (/\.(js|mjs|cjs)$/i.test(name)) return { label: "JS", cls: "js" };
    if (/\.(ts|tsx|jsx)$/i.test(name)) return { label: "TS", cls: "ts" };
    if (/\.py$/i.test(name)) return { label: "PY", cls: "py" };
    if (/\.json$/i.test(name)) return { label: "JSON", cls: "json" };
    if (/\.md$/i.test(name)) return { label: "MD", cls: "md" };
    return { label: "FILE", cls: "file" };
  }

  function markChangedFiles(paths) {
    const clean = (paths || []).map((p) => String(p || "").replace(/\\/g, "/")).filter(Boolean);
    state.recentChangedFiles = Array.from(new Set([...(state.recentChangedFiles || []), ...clean])).slice(-24);
    clean.forEach((path) => {
      const parts = path.split("/");
      for (let i = 1; i < parts.length; i += 1) {
        state.expandedDirs[parts.slice(0, i).join("/")] = true;
      }
    });
  }

  function isRecentlyChanged(path) {
    const norm = String(path || "").replace(/\\/g, "/");
    return (state.recentChangedFiles || []).some((p) => p === norm || p.endsWith("/" + norm) || norm.endsWith("/" + p));
  }

  function isUiPath(path) {
    return /\.(html?|css|scss|js|jsx|ts|tsx|vue)$/i.test(path || "");
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

  function buildFileTree(files) {
    const root = { name: "", path: "", dirs: {}, files: [] };
    files.forEach((file) => {
      const parts = String(file.path || "").replace(/\\/g, "/").split("/").filter(Boolean);
      if (!parts.length) return;
      let node = root;
      for (let i = 0; i < parts.length - 1; i += 1) {
        const part = parts[i];
        const dirPath = parts.slice(0, i + 1).join("/");
        if (!node.dirs[part]) {
          node.dirs[part] = { name: part, path: dirPath, dirs: {}, files: [] };
        }
        node = node.dirs[part];
      }
      node.files.push({
        ...file,
        name: parts[parts.length - 1],
        path: parts.join("/"),
      });
    });
    return root;
  }

  function isDirExpanded(path) {
    if (!path) return true;
    if (Object.prototype.hasOwnProperty.call(state.expandedDirs, path)) {
      return !!state.expandedDirs[path];
    }
    return path.split("/").length <= 2;
  }

  function toggleDir(path) {
    state.expandedDirs[path] = !isDirExpanded(path);
    renderFileTree();
  }

  function renderTreeNode(node, depth, container) {
    const dirNames = Object.keys(node.dirs).sort((a, b) => a.localeCompare(b));
    dirNames.forEach((name) => {
      const dir = node.dirs[name];
      const expanded = isDirExpanded(dir.path);
      const hasChangedChild = (state.recentChangedFiles || []).some(
        (p) => p === dir.path || p.startsWith(dir.path + "/")
      );
      const li = document.createElement("li");
      li.className = `file-dir${expanded ? " open" : ""}${hasChangedChild ? " changed" : ""}`;
      li.style.paddingLeft = `${10 + depth * 14}px`;
      li.innerHTML = `
        <button type="button" class="file-dir-toggle" aria-expanded="${expanded}">
          <span class="file-dir-chevron">${expanded ? "▾" : "▸"}</span>
          <span class="file-dir-name">${escapeHtml(dir.name)}</span>
        </button>`;
      li.querySelector(".file-dir-toggle").addEventListener("click", (event) => {
        event.stopPropagation();
        toggleDir(dir.path);
      });
      container.appendChild(li);
      if (expanded) renderTreeNode(dir, depth + 1, container);
    });

    node.files
      .slice()
      .sort((a, b) => {
        const aNew = isRecentlyChanged(a.path) ? 0 : 1;
        const bNew = isRecentlyChanged(b.path) ? 0 : 1;
        if (aNew !== bNew) return aNew - bNew;
        return a.name.localeCompare(b.name);
      })
      .forEach((f) => {
        const kind = fileKind(f.name);
        const changed = isRecentlyChanged(f.path);
        const li = document.createElement("li");
        li.dataset.path = f.path;
        li.style.paddingLeft = `${10 + depth * 14}px`;
        if (state.selectedFile === f.path) li.classList.add("selected");
        if (changed) li.classList.add("changed");
        li.innerHTML = `
          <span class="file-kind file-kind--${kind.cls}">${kind.label}</span>
          <span class="file-path">${escapeHtml(f.name)}</span>
          ${changed ? '<span class="file-changed">novo</span>' : ""}`;
        li.title = f.path;
        li.addEventListener("click", () => openFile(f.path));
        container.appendChild(li);
      });
  }

  function renderFileTree() {
    els.fileTree.innerHTML = "";
    if (!state.files.length) {
      els.fileTree.innerHTML = `
        <li class="file-empty">
          <strong>Sem arquivos ainda</strong>
          <span>Peça ao agente para criar a estrutura do projeto.</span>
        </li>`;
      return;
    }

    const query = (els.fileSearchInput?.value || "").trim().toLowerCase();

    if (state.searchMatches?.length) {
      state.searchMatches.forEach((match) => {
        const path = match.path || "";
        const kind = fileKind(path.split("/").pop() || path);
        const changed = isRecentlyChanged(path);
        const symbols = (match.symbols || []).slice(0, 3).join(", ");
        const li = document.createElement("li");
        li.dataset.path = path;
        if (state.selectedFile === path) li.classList.add("selected");
        if (changed) li.classList.add("changed");
        li.innerHTML = `
          <span class="file-kind file-kind--${kind.cls}">${kind.label}</span>
          <span class="file-path">${escapeHtml(path)}</span>
          ${symbols ? `<span class="file-search-symbols">${escapeHtml(symbols)}</span>` : ""}
          ${changed ? '<span class="file-changed">novo</span>' : ""}`;
        li.title = path;
        li.addEventListener("click", () => openFile(path));
        els.fileTree.appendChild(li);
      });
      return;
    }

    const files = query
      ? state.files.filter((f) => f.path.toLowerCase().includes(query) || f.name.toLowerCase().includes(query))
      : state.files;

    if (!files.length) {
      els.fileTree.innerHTML = '<li class="file-empty">Nenhum arquivo corresponde à busca.</li>';
      return;
    }

    if (query) {
      files
        .slice()
        .sort((a, b) => a.path.localeCompare(b.path))
        .forEach((f) => {
          const kind = fileKind(f.name);
          const changed = isRecentlyChanged(f.path);
          const li = document.createElement("li");
          li.dataset.path = f.path;
          if (state.selectedFile === f.path) li.classList.add("selected");
          if (changed) li.classList.add("changed");
          li.innerHTML = `
            <span class="file-kind file-kind--${kind.cls}">${kind.label}</span>
            <span class="file-path">${escapeHtml(f.path)}</span>
            ${changed ? '<span class="file-changed">novo</span>' : ""}`;
          li.addEventListener("click", () => openFile(f.path));
          els.fileTree.appendChild(li);
        });
      return;
    }

    const tree = buildFileTree(files);
    renderTreeNode(tree, 0, els.fileTree);
  }

  async function openFile(path, options = {}) {
    if (!state.current || !path) return;
    if (state.fileEditorDirty && state.selectedFile && state.selectedFile !== path) {
      if (!window.confirm("Descartar alterações não salvas em " + state.selectedFile + "?")) {
        return;
      }
    }
    state.selectedFile = path;
    renderFileTree();
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/file?path=${encodeURIComponent(path)}`);
      els.fileEditorShell?.classList.remove("hidden");
      if (els.fileViewer) {
        els.fileViewer.value = d.content ?? "";
        els.fileViewer.readOnly = false;
      }
      if (els.fileEditorPath) els.fileEditorPath.textContent = path;
      state.fileEditorOriginal = d.content ?? "";
      state.fileEditorRevision = d.revision || null;
      state.fileEditorDirty = false;
      syncFileEditorDirty();
      if (options.preferPreview !== false && /\.html?$/i.test(path)) {
        switchTab("preview");
        updatePreview(path);
      } else if (options.switchToFiles) {
        switchTab("files");
      }
    } catch (e) {
      els.fileEditorShell?.classList.remove("hidden");
      if (els.fileViewer) {
        els.fileViewer.value = "Erro: " + e.message;
        els.fileViewer.readOnly = true;
      }
      if (els.fileEditorPath) els.fileEditorPath.textContent = path;
      state.fileEditorOriginal = "";
      state.fileEditorRevision = null;
      state.fileEditorDirty = false;
      syncFileEditorDirty();
      if (options.switchToFiles) switchTab("files");
    }
  }

  function syncFileEditorDirty() {
    const dirty = !!state.fileEditorDirty;
    els.fileEditorDirty?.classList.toggle("hidden", !dirty);
    if (els.btnFileSave) els.btnFileSave.disabled = !dirty || !state.selectedFile;
  }

  function onFileEditorInput() {
    if (!els.fileViewer || els.fileViewer.readOnly) return;
    state.fileEditorDirty = els.fileViewer.value !== state.fileEditorOriginal;
    syncFileEditorDirty();
  }

  async function saveCurrentFile(options = {}) {
    if (!state.current || !state.selectedFile || !els.fileViewer || els.fileViewer.readOnly) return;
    if (!state.fileEditorDirty && !options.force) return;
    const path = state.selectedFile;
    const content = els.fileViewer.value;
    const asCopy = !!options.asCopy;
    const savePath = asCopy ? path.replace(/(\.[^.]+)?$/, ".copy$1") : path;
    els.btnFileSave && (els.btnFileSave.disabled = true);
    try {
      const body = { path: savePath, content };
      if (!asCopy && state.fileEditorRevision) {
        body.expected_revision = state.fileEditorRevision;
      }
      const saved = await api(`/api/projects/${encodeURIComponent(state.current.id)}/file`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (!asCopy) {
        state.fileEditorOriginal = content;
        state.fileEditorRevision = saved.revision || null;
        state.fileEditorDirty = false;
      }
      syncFileEditorDirty();
      if (els.fileEditorPath) {
        els.fileEditorPath.textContent = (asCopy ? savePath : path) + " · salvo";
        window.setTimeout(() => {
          if (state.selectedFile === path && els.fileEditorPath) {
            els.fileEditorPath.textContent = path;
          }
        }, 1600);
      }
      await loadFiles().catch(() => {});
      if (/\.html?$|\.css$|\.js$/i.test(savePath)) {
        updatePreview(/\.html?$/i.test(savePath) ? savePath : findPreviewPath());
      }
    } catch (e) {
      if (e.status === 409 && e.data?.conflict) {
        const choice = window.confirm(
          "Conflito: o arquivo mudou (ex.: o agente editou).\n\nOK = recarregar do disco\nCancelar = salvar como cópia (.copy)"
        );
        if (choice) {
          await openFile(path, { switchToFiles: true, preferPreview: false });
        } else {
          await saveCurrentFile({ asCopy: true, force: true });
        }
        return;
      }
      if (els.fileEditorPath) {
        els.fileEditorPath.textContent = path + " · erro: " + (e.message || String(e));
      }
      syncFileEditorDirty();
    }
  }

  function findPreviewPath() {
    const html = state.files.find((f) => /^index\.html?$/i.test(f.name));
    if (html) return html.path;
    return state.files.find((f) => /\.html?$/i.test(f.name))?.path || null;
  }

  function setPreviewEmptyVisible(visible, message) {
    if (els.previewEmpty) els.previewEmpty.classList.toggle("hidden", !visible);
    if (els.previewHint) {
      els.previewHint.classList.toggle("hidden", true);
      if (message) els.previewHint.textContent = message;
    }
    if (visible && message && els.previewEmpty) {
      const copy = els.previewEmpty.querySelector(".preview-empty-copy");
      if (copy) copy.textContent = message;
    }
    const hasScript = !!state.devStatus?.has_dev_script;
    const running = !!state.devStatus?.running;
    els.btnPreviewStartDev?.classList.toggle("hidden", !(visible && hasScript && !running));
  }

  function setPreviewDevice(device) {
    if (!device) return;
    state.previewDevice = device;
    if (els.previewViewport) {
      els.previewViewport.classList.remove("device-desktop", "device-tablet", "device-mobile");
      els.previewViewport.classList.add(`device-${device}`);
    }
    els.deviceSwitcher?.querySelectorAll(".device-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.device === device);
    });
  }

  function clearPreviewLoadTimer() {
    if (state.previewLoadTimer) {
      clearTimeout(state.previewLoadTimer);
      state.previewLoadTimer = null;
    }
  }

  function schedulePreviewLoadCheck() {
    clearPreviewLoadTimer();
    state.previewLoadTimer = setTimeout(async () => {
      if (!state.previewExpectingContent) return;
      await refreshDevStatus();
      if (
        state.previewMode === "dev" &&
        state.devStatus?.has_dev_script &&
        !state.previewLoadRetried &&
        canStartDevPreview()
      ) {
        state.previewLoadRetried = true;
        await startDevServer();
      }
    }, 8000);
  }

  function bindPreviewFrameLoad() {
    if (!els.previewFrame) return;
    els.previewFrame.onload = () => {
      const src = els.previewFrame.getAttribute("src") || "";
      if (src && src !== "about:blank") {
        state.previewExpectingContent = false;
        clearPreviewLoadTimer();
      }
    };
  }

  function updatePreview(explicitPath) {
    if (!state.current) return;
    syncPreviewPolling();

    if (state.previewMode === "dev" && state.devStatus?.running && state.devStatus.url) {
      setPreviewEmptyVisible(false);
      state.previewExpectingContent = true;
      els.previewFrame.src = state.devStatus.url + "?t=" + Date.now();
      schedulePreviewLoadCheck();
      return;
    }

    if (state.previewMode === "dev" && state.devStatus?.has_dev_script && !state.devStatus?.running) {
      els.previewFrame.src = "about:blank";
      const runtime = state.devStatus?.runtime || state.devStatus?.script;
      let msg = "Clique em Iniciar preview ao vivo.";
      if (runtime === "uvicorn") {
        msg =
          state.devStatus?.python_available === false
            ? "Instale Python para rodar a API FastAPI."
            : "API FastAPI detectada — inicie o preview ao vivo (uvicorn).";
      } else if (!state.devStatus?.npm_available) {
        msg = "Instale Node.js para rodar o preview ao vivo deste app.";
      } else {
        msg = "Este projeto precisa do Vite. Clique em Iniciar preview ao vivo.";
      }
      setPreviewEmptyVisible(true, msg);
      return;
    }

    const path = explicitPath || findPreviewPath();
    if (!path) {
      els.previewFrame.src = "about:blank";
      const runtime = state.devStatus?.runtime || state.devStatus?.script;
      const msg = state.devStatus?.has_dev_script
        ? runtime === "uvicorn"
          ? "API FastAPI — clique em Iniciar preview ao vivo (abre /docs)."
          : "Apps React/Vite precisam de npm run dev — clique em Iniciar preview ao vivo."
        : "Nenhum HTML encontrado. Peça ao agente para criar index.html.";
      setPreviewEmptyVisible(true, msg);
      return;
    }
    setPreviewEmptyVisible(false);
    state.previewExpectingContent = true;
    els.previewFrame.src = `/preview/${encodeURIComponent(state.current.id)}/${path.split("/").map(encodeURIComponent).join("/")}?t=${Date.now()}`;
    schedulePreviewLoadCheck();
    api(`/api/projects/${encodeURIComponent(state.current.id)}/preview-revision`)
      .then((d) => {
        state.previewRevision = d.revision || null;
      })
      .catch(() => {});
  }

  function addNextStepActions(changed, donePayload) {
    const el = document.createElement("div");
    el.className = "msg system next-steps";
    const status = donePayload?.status || "";
    const htmlPath = changed.find((p) => /\.html?$/i.test(p));
    const actions = [];
    const hasDev = !!state.devStatus?.has_dev_script;
    const devRunning = !!state.devStatus?.running;

    if (hasDev && !devRunning) {
      actions.push({ action: "start-dev", label: "Iniciar preview" });
    }
    if (htmlPath || changed.some(isUiPath)) {
      actions.push({ action: "preview", label: "Ver preview" });
    }
    if (changed[0]) {
      actions.push({ action: "open-file", label: "Abrir arquivo", path: changed[0] });
    }
    if (changed.length) {
      actions.push({ action: "files", label: `Arquivos (${changed.length})` });
    }
    actions.push({
      action: "prompt",
      label: "Melhorar visual",
      prompt: "Melhore o visual desta página: tipografia, espaçamento, cores e responsividade, sem quebrar a estrutura.",
    });
    actions.push({
      action: "prompt",
      label: "Adicionar seção",
      prompt: "Adicione uma nova seção relevante na página principal com bom layout e texto em português.",
    });
    if (status && status !== "SUCCESS" && status !== "CANCELLED") {
      actions.push({
        action: "prompt",
        label: "Corrigir o erro da última execução",
        prompt:
          "Corrija o erro da última execução neste projeto. Leia o relatório e os logs, identifique a causa e aplique a correção mínima necessária.",
      });
    }
    actions.push({ action: "deploy", label: "Deploy" });

    const title =
      status === "CANCELLED"
        ? "Execução cancelada"
        : changed.length
          ? `${changed.length} arquivo(s) atualizado(s)`
          : "Pronto para o próximo passo";

    el.innerHTML = `
      <div class="next-steps-card">
        <div class="next-steps-title">${escapeHtml(title)}</div>
        ${changed.length ? `<div class="next-steps-files">${changed.slice(0, 5).map((p) => `<button type="button" class="next-file" data-path="${escapeHtml(p)}">${escapeHtml(p)}</button>`).join("")}</div>` : ""}
        <div class="next-steps-actions">
          ${actions
            .map(
              (item) =>
                `<button type="button" class="btn btn-ghost btn-sm next-action" data-action="${item.action}" ${
                  item.path ? `data-path="${escapeHtml(item.path)}"` : ""
                } ${item.prompt ? `data-prompt="${escapeHtml(item.prompt)}"` : ""}>${escapeHtml(item.label)}</button>`
            )
            .join("")}
        </div>
      </div>`;

    el.addEventListener("click", async (event) => {
      const fileBtn = event.target.closest(".next-file");
      if (fileBtn?.dataset.path) {
        await openFile(fileBtn.dataset.path, { switchToFiles: true, preferPreview: false });
        return;
      }
      const btn = event.target.closest(".next-action");
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === "preview") {
        switchTab("preview");
        updatePreview(htmlPath || findPreviewPath());
      } else if (action === "start-dev") {
        state.previewMode = "dev";
        if (els.previewMode) els.previewMode.value = "dev";
        syncDevPolling();
        startDevServer();
      } else if (action === "deploy") {
        runDeploy();
      } else if (action === "files") {
        switchTab("files");
      } else if (action === "open-file" && btn.dataset.path) {
        await openFile(btn.dataset.path, { switchToFiles: true, preferPreview: false });
      } else if (action === "prompt" && btn.dataset.prompt) {
        els.promptInput.value = btn.dataset.prompt;
        els.promptInput.focus();
      }
    });

    els.chatMessages.appendChild(el);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return el;
  }

  async function syncWorkspaceAfterRun(donePayload) {
    const created = donePayload?.created_files || [];
    const modified = donePayload?.modified_files || [];
    const changed = Array.from(new Set([...created, ...modified].map((p) => String(p || "").replace(/\\/g, "/")).filter(Boolean)));
    markChangedFiles(changed);

    await loadProjects();
    await loadFiles();
    await loadRunHistory();
    await refreshDevStatus();

    const htmlChanged = changed.find((p) => /\.html?$/i.test(p));
    const uiChanged = changed.some(isUiPath);
    const packageTouched = changed.some((p) => /(^|\/)package\.json$/i.test(p) || /(^|\/)vite\.config\./i.test(p));
    const hasDev = !!state.devStatus?.has_dev_script;

    if (hasDev && (packageTouched || uiChanged) && !state.devStatus?.running && canStartDevPreview()) {
      await maybeEnableDevPreview({ preferDev: true, autoStart: true });
    } else if (hasDev) {
      await maybeEnableDevPreview({ preferDev: true, autoStart: false });
    }

    if (donePayload?.status === "CANCELLED") {
      switchTab("report");
    } else if (hasDev || uiChanged || htmlChanged) {
      switchTab("preview");
      updatePreview(htmlChanged || findPreviewPath());
    } else if (changed[0]) {
      await openFile(changed[0], { switchToFiles: true, preferPreview: false });
    } else {
      switchTab("report");
      updatePreview();
    }

    addNextStepActions(changed, donePayload);
  }

  // ── Dev server ──

  function stopDevPolling() {
    if (state.devPollTimer) {
      clearInterval(state.devPollTimer);
      state.devPollTimer = null;
    }
  }

  function syncDevPolling() {
    stopDevPolling();
    if (state.current && state.previewMode === "dev") {
      state.devPollTimer = setInterval(() => {
        if (state.current && state.previewMode === "dev") {
          refreshDevStatus().then(() => {
            if (state.devStatus?.running) updatePreview();
          });
        }
      }, 5000);
    }
  }

  function stopPreviewPolling() {
    if (state.previewPollTimer) {
      clearInterval(state.previewPollTimer);
      state.previewPollTimer = null;
    }
  }

  function syncPreviewPolling() {
    stopPreviewPolling();
    const previewOpen = !$("panelPreview")?.classList.contains("hidden");
    if (!state.current || state.previewMode !== "static" || !previewOpen) return;
    state.previewPollTimer = setInterval(async () => {
      if (!state.current || state.previewMode !== "static") return;
      if ($("panelPreview")?.classList.contains("hidden")) return;
      try {
        const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/preview-revision`);
        const rev = d.revision || null;
        if (state.previewRevision && rev && rev !== state.previewRevision) {
          updatePreview(findPreviewPath());
        }
        state.previewRevision = rev;
      } catch {
        /* ignore */
      }
    }, 3500);
  }

  async function clearDevError() {
    if (!state.current) return;
    try {
      await api(`/api/projects/${encodeURIComponent(state.current.id)}/dev/clear-error`, {
        method: "POST",
        body: "{}",
      });
      await refreshDevStatus();
    } catch (e) {
      els.devStatus.textContent = e.message;
    }
  }

  function canStartDevPreview(status = state.devStatus) {
    if (!status?.has_dev_script) return false;
    const runtime = status.runtime || (status.script === "uvicorn" ? "uvicorn" : "npm");
    if (runtime === "uvicorn") return status.python_available !== false;
    return !!status.npm_available;
  }

  function renderDevControls() {
    const s = state.devStatus || {};
    const hasScript = s.has_dev_script;
    const runtime = s.runtime || (s.script === "uvicorn" ? "uvicorn" : "npm");
    els.btnDevStart.classList.toggle("hidden", !hasScript || s.running);
    els.btnDevStop.classList.toggle("hidden", !s.running);
    els.btnDevClear?.classList.toggle("hidden", !hasScript || !s.last_error);
    els.btnDevRestart?.classList.toggle("hidden", !hasScript);
    els.previewMode.querySelector('option[value="dev"]').disabled = !hasScript;

    if (!hasScript) {
      els.devStatus.textContent = "Sem preview ao vivo (npm ou FastAPI)";
    } else if (s.running) {
      const label = runtime === "uvicorn" ? "uvicorn" : s.script;
      els.devStatus.textContent = `Rodando :${s.port} (${label})`;
      els.devErrorLog?.classList.add("hidden");
    } else if (runtime === "uvicorn" && s.python_available === false) {
      els.devStatus.textContent = "Instale Python para rodar FastAPI";
    } else if (runtime !== "uvicorn" && !s.npm_available) {
      els.devStatus.textContent = "Instale Node.js para dev server";
    } else if (s.last_error) {
      els.devStatus.textContent = "Último erro no preview";
      if (els.devErrorLog) {
        els.devErrorLog.textContent = s.last_error;
        els.devErrorLog.classList.remove("hidden");
      }
    } else if (runtime === "uvicorn") {
      els.devStatus.textContent = "Pronto: uvicorn main:app";
    } else {
      els.devStatus.textContent = `Pronto: npm run ${s.script}`;
    }
  }

  async function refreshDevStatus() {
    if (!state.current) return null;
    const wasRunning = !!state.devStatus?.running;
    try {
      state.devStatus = await api(`/api/projects/${encodeURIComponent(state.current.id)}/dev/status`);
    } catch {
      state.devStatus = null;
    }
    const isRunning = !!state.devStatus?.running;
    renderDevControls();
    if (wasRunning && !isRunning && state.previewMode === "dev" && !state.devAutoRestarted) {
      state.devAutoRestarted = true;
      if (canStartDevPreview()) {
        await startDevServer();
      }
    }
    if (isRunning) {
      state.devAutoRestarted = false;
      state.previewLoadRetried = false;
    }
    state.devWasRunning = isRunning;
    return state.devStatus;
  }

  async function startDevServer() {
    if (!state.current) return;
    els.btnDevStart.disabled = true;
    const runtime = state.devStatus?.runtime || state.devStatus?.script;
    els.devStatus.textContent =
      runtime === "uvicorn"
        ? "Iniciando uvicorn (pip install pode demorar)..."
        : "Iniciando (npm install pode demorar)...";
    els.devErrorLog?.classList.add("hidden");
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/dev/start`, {
        method: "POST",
        body: JSON.stringify({ install: true }),
      });
      state.devStatus = { ...state.devStatus, ...d, running: true };
      state.previewMode = "dev";
      els.previewMode.value = "dev";
      renderDevControls();
      syncDevPolling();
      updatePreview();
      switchTab("preview");
    } catch (e) {
      els.devStatus.textContent = e.message;
      if (e.data?.stderr && els.devErrorLog) {
        els.devErrorLog.textContent = e.data.stderr;
        els.devErrorLog.classList.remove("hidden");
      }
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

  function resetDeployModal() {
    els.deployModalInner?.classList.remove("deploy-modal--ok", "deploy-modal--warn", "deploy-modal--err");
    els.deployBadge?.classList.add("hidden");
    els.deploySpinner?.classList.add("hidden");
    els.btnOpenDeployUrl?.classList.add("hidden");
    if (els.deployChecklist) els.deployChecklist.innerHTML = "";
  }

  function renderDeployChecklist(data) {
    if (!els.deployChecklist) return;
    const reqs = data?.requirements || [];
    if (!reqs.length) {
      els.deployChecklist.innerHTML = '<li class="deploy-check-item warn"><span class="deploy-check-icon">○</span><span>Sem dados de preflight.</span></li>';
      return;
    }
    els.deployChecklist.innerHTML = reqs
      .map(
        (item) => `
        <li class="deploy-check-item ${item.ok ? "ok" : "warn"}">
          <span class="deploy-check-icon">${item.ok ? "✓" : "○"}</span>
          <span>${escapeHtml(item.label || item.id || "Requisito")}${!item.ok && item.fix ? `<small>${escapeHtml(item.fix)}</small>` : ""}</span>
        </li>`
      )
      .join("");
    state.deployReady = !!data?.ready;
  }

  async function fetchDeployStatus() {
    if (!state.current) return null;
    try {
      return await api(`/api/projects/${encodeURIComponent(state.current.id)}/deploy/status`);
    } catch {
      return null;
    }
  }

  function openDeployModal(text) {
    if (text) els.deployLog.textContent = text;
    els.deployModal.classList.remove("hidden");
  }

  function closeDeployModal() {
    if (state.deploying) return;
    els.deployModal.classList.add("hidden");
    resetDeployModal();
  }

  function renderDeployResult(d) {
    let log = d.message || "";
    if (d.url) log += `\n\nURL: ${d.url}`;
    if (d.steps?.length) log += "\n\nPassos manuais:\n" + d.steps.map((s, i) => `${i + 1}. ${s}`).join("\n");
    if (d.log_tail) log += "\n\n--- log ---\n" + d.log_tail;
    els.deployLog.textContent = log;

    resetDeployModal();
    if (d.ok && d.url) {
      els.deployModalInner?.classList.add("deploy-modal--ok");
      els.deployBadge.textContent = "Sucesso";
      els.deployBadge.classList.remove("hidden");
      els.btnOpenDeployUrl.href = d.url;
      els.btnOpenDeployUrl.classList.remove("hidden");
      els.deployLog.innerHTML = escapeHtml(log).replace(
        escapeHtml(d.url),
        `<a class="deploy-link" href="${escapeHtml(d.url)}" target="_blank" rel="noopener">${escapeHtml(d.url)}</a>`
      );
    } else if (d.manual) {
      els.deployModalInner?.classList.add("deploy-modal--warn");
      els.deployBadge.textContent = "Manual";
      els.deployBadge.classList.remove("hidden");
    } else {
      els.deployModalInner?.classList.add("deploy-modal--err");
      els.deployBadge.textContent = "Falhou";
      els.deployBadge.classList.remove("hidden");
    }
  }

  async function runDeploy() {
    if (!state.current) return;
    state.deploying = true;
    els.btnDeploy.disabled = true;
    els.btnCloseDeploy.disabled = true;
    resetDeployModal();
    openDeployModal("Verificando requisitos...");
    const preflight = await fetchDeployStatus();
    if (preflight) renderDeployChecklist(preflight);
    els.deploySpinner?.classList.remove("hidden");
    els.deployLog.textContent = preflight?.ready
      ? "Requisitos OK. Iniciando deploy..."
      : "Alguns requisitos estão pendentes — tentando deploy mesmo assim...\n\nRequer VERCEL_TOKEN no ambiente para deploy automático.";
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/deploy`, {
        method: "POST",
        body: "{}",
      });
      if (d.requirements) renderDeployChecklist({ requirements: d.requirements, ready: d.ok });
      renderDeployResult(d);
    } catch (e) {
      resetDeployModal();
      els.deployModalInner?.classList.add("deploy-modal--err");
      els.deployBadge.textContent = "Erro";
      els.deployBadge.classList.remove("hidden");
      els.deployLog.textContent = "Erro: " + e.message;
    } finally {
      state.deploying = false;
      els.deploySpinner?.classList.add("hidden");
      els.btnCloseDeploy.disabled = false;
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
    syncMobileTabs(name);
    if (isMobileLayout()) openMobilePanel();
    else closeMobilePanel();
    if (name === "preview") updatePreview();
    else stopPreviewPolling();
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
  els.mobileTabs?.addEventListener("click", (e) => {
    const btn = e.target.closest(".mobile-tab");
    if (!btn?.dataset.tab) return;
    switchTab(btn.dataset.tab);
  });
  els.mobileBackdrop?.addEventListener("click", closeMobilePanel);
  window.addEventListener("resize", () => {
    if (!isMobileLayout()) closeMobilePanel();
    syncSidebarToggle();
  });

  els.btnToggleSidebar?.addEventListener("click", () => {
    if (els.sidebar?.classList.contains("sidebar-open")) closeSidebar();
    else openSidebar();
  });
  els.sidebarBackdrop?.addEventListener("click", closeSidebar);

  els.fileSearchInput?.addEventListener("input", () => {
    clearTimeout(state.fileSearchTimer);
    const q = els.fileSearchInput.value;
    state.fileSearchTimer = setTimeout(() => searchProjectFiles(q), 250);
  });

  els.projectSearch?.addEventListener("input", () => {
    clearTimeout(state.projectSearchTimer);
    state.projectSearchTimer = setTimeout(() => loadProjects(), 250);
  });

  document.querySelectorAll(".preview-cta").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!btn.dataset.prompt) return;
      els.promptInput.value = btn.dataset.prompt;
      els.promptInput.focus();
      if (!state.running) sendPrompt();
    });
  });
  els.btnPreviewStartDev?.addEventListener("click", () => {
    state.previewMode = "dev";
    if (els.previewMode) els.previewMode.value = "dev";
    startDevServer();
  });

  els.btnClearChat?.addEventListener("click", clearChat);
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
  els.btnAutoSetup?.addEventListener("click", () => runAutoSetupFromModelsModal());
  els.btnSetupRetry?.addEventListener("click", () => runAutoSetupFromModelsModal());
  els.btnSetupClose?.addEventListener("click", () => {
    dismissSetupPrompt();
    hideSetupModal();
    showSetupActions(false);
  });

  async function runAutoSetupFromModelsModal() {
    try {
      clearSetupDismissed();
      resetSetupProgress();
      els.setupInstallLinkWrap?.classList.add("hidden");
      showSetupModal("Iniciando configuração automática...", 3);
      showSetupActions(false);
      const ok = await ensureEnvironment({ pullRecommended: true, showProgress: true });
      if (ok) {
        updateOllamaOfflineUI();
        await loadModelRecommendations().catch(() => {});
        if (state.pendingPrompt && state.current) {
          els.promptInput.value = state.pendingPrompt;
          state.pendingPrompt = null;
          closeModelsModal();
          sendPrompt();
        } else {
          closeModelsModal();
        }
      }
    } catch (e) {
      finishSetupError(e.message || "Erro inesperado na configuração.");
      showSetupActions(true);
    }
  }
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
  els.btnDevClear?.addEventListener("click", clearDevError);
  els.btnFileSave?.addEventListener("click", () => {
    saveCurrentFile().catch(() => {});
  });
  els.fileViewer?.addEventListener("input", onFileEditorInput);
  els.fileViewer?.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      saveCurrentFile().catch(() => {});
    }
  });
  window.addEventListener("beforeunload", (e) => {
    if (state.fileEditorDirty) {
      e.preventDefault();
      e.returnValue = "";
    }
  });
  els.btnDevRestart?.addEventListener("click", startDevServer);
  const MODE_PREF_KEY = "forge.mode";

  function syncModeControls() {
    const mode = els.modeSelect?.value || "chat";
    const isChat = mode === "chat";
    const isExecute = mode === "execute";
    document.querySelector(".steps-control")?.classList.toggle("hidden", isChat);
    if (els.modeChip) {
      els.modeChip.textContent = isExecute ? "Executar" : "Chat";
      els.modeChip.classList.toggle("mode-chip--execute", isExecute);
      els.modeChip.title = isExecute ? "Modo Executar — altera arquivos no projeto" : "Modo Chat — só conversa";
    }
    if (els.promptInput) {
      els.promptInput.placeholder = isChat
        ? "Converse com o agente… (para criar código, mude para Executar código)"
        : "Peça uma mudança, um componente ou uma correção…";
    }
    try {
      localStorage.setItem(MODE_PREF_KEY, mode);
    } catch (_) {
      /* ignore */
    }
  }

  try {
    const savedMode = localStorage.getItem(MODE_PREF_KEY);
    if (savedMode && els.modeSelect?.querySelector(`option[value="${savedMode}"]`)) {
      els.modeSelect.value = savedMode;
    }
  } catch (_) {
    /* ignore */
  }

  els.modeSelect?.addEventListener("change", syncModeControls);
  syncModeControls();

  els.previewMode.addEventListener("change", () => {
    state.previewMode = els.previewMode.value;
    state.devAutoRestarted = false;
    state.previewLoadRetried = false;
    syncDevPolling();
    updatePreview();
  });

  bindPreviewFrameLoad();

  document.querySelectorAll(".panel-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  document.querySelectorAll(".quick-card").forEach((card) => {
    card.addEventListener("click", () => {
      const prompt = card.dataset.prompt;
      if (!prompt || !state.current || state.running) return;
      els.promptInput.value = prompt;
      els.promptInput.focus();
    });
  });

  els.deviceSwitcher?.addEventListener("click", (e) => {
    const btn = e.target.closest(".device-btn");
    if (!btn?.dataset.device) return;
    setPreviewDevice(btn.dataset.device);
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
    syncSidebarToggle();
    setPreviewDevice(state.previewDevice);
    checkHealth();
    setInterval(checkHealth, 30000);
    checkHealth().then(async () => {
      try {
        const status = await api("/api/setup/status");
        state.setupPlatform = status.platform || null;
        state.setupInstallUrl = status.install_url || null;
        state.ollamaInstalled = status.ollama_installed !== false;
        updateOllamaOfflineUI();
        if (!status.setup_complete && !isSetupDismissed()) {
          ensureEnvironment({ pullRecommended: true, showProgress: true }).catch(() => {
            showSetupActions(true);
          });
        }
      } catch {
        if (!isSetupDismissed()) {
          ensureEnvironment({ pullRecommended: true, showProgress: true }).catch(() => {
            showSetupActions(true);
          });
        }
      }
    });
    try {
      await loadProjects();
      let targetId = null;
      try {
        const lastId = localStorage.getItem(LAST_PROJECT_KEY);
        if (lastId && state.projects.some((p) => p.id === lastId)) targetId = lastId;
      } catch {
        /* ignore */
      }
      if (!targetId && state.projects.length) targetId = state.projects[0].id;
      if (targetId) await selectProject(targetId);
      else showEmptyView();
    } catch {
      showEmptyView();
    }
  }

  init();
})();
