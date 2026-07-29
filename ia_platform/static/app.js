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
    userSettings: null,
    profileMode: "detected",
    pullingModel: false,
    pullingModelName: null,
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
    previewPollAbort: null,
    previewPollInFlight: false,
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
    surfaceMode: "chat", // chat | work
    attachments: [],
    chats: [],
    chatsExpanded: true,
    projectsShowAll: false,
    liveCode: {
      current: null,
      history: [],
      autoOpened: false,
    },
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    sidebar: $("sidebar"),
    sidebarBackdrop: $("sidebarBackdrop"),
    btnToggleSidebar: $("btnToggleSidebar"),
    btnCollapseSidebar: $("btnCollapseSidebar"),
    btnSidebarSearch: $("btnSidebarSearch"),
    fileSearchInput: $("fileSearchInput"),
    runHistoryList: $("runHistoryList"),
    projectList: $("projectList"),
    chatList: $("chatList"),
    btnToggleChats: $("btnToggleChats"),
    btnNewChat: $("btnNewChat"),
    btnProjectsMore: $("btnProjectsMore"),
    btnSurfaceChat: $("btnSurfaceChat"),
    btnSurfaceWork: $("btnSurfaceWork"),
    emptyTitle: $("emptyTitle"),
    emptySub: $("emptySub"),
    workHomeActions: $("workHomeActions"),
    btnChooseProjectEmpty: $("btnChooseProjectEmpty"),
    btnNewProjectEmpty: $("btnNewProjectEmpty"),
    heroKicker: $("heroKicker"),
    heroTitle: $("heroTitle"),
    heroSub: $("heroSub"),
    composer: $("composer"),
    composerMenu: $("composerMenu"),
    btnComposerPlus: $("btnComposerPlus"),
    btnAttachFiles: $("btnAttachFiles"),
    attachFileInput: $("attachFileInput"),
    attachmentChips: $("attachmentChips"),
    composerModelSelect: $("composerModelSelect"),
    btnPickProject: $("btnPickProject"),
    composerProjectLabel: $("composerProjectLabel"),
    composerToolbar: $("composerToolbar"),
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
    panelLive: $("panelLive"),
    liveCodeBadge: $("liveCodeBadge"),
    liveCodePath: $("liveCodePath"),
    liveCodeStats: $("liveCodeStats"),
    liveCodeBody: $("liveCodeBody"),
    liveCodeTimeline: $("liveCodeTimeline"),
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
    clientHardwareGrid: $("clientHardwareGrid"),
    hardwareMismatch: $("hardwareMismatch"),
    hardwareNote: $("hardwareNote"),
    localRunGuide: $("localRunGuide"),
    localRunCommands: $("localRunCommands"),
    btnCopyLocalRun: $("btnCopyLocalRun"),
    btnRefreshHardware: $("btnRefreshHardware"),
    hwModeDetected: $("hwModeDetected"),
    hwModeManual: $("hwModeManual"),
    hwProfileFields: $("hwProfileFields"),
    hwPreset: $("hwPreset"),
    hwRam: $("hwRam"),
    hwVram: $("hwVram"),
    hwCores: $("hwCores"),
    hwHasGpu: $("hwHasGpu"),
    hwGpuName: $("hwGpuName"),
    btnSaveHwProfile: $("btnSaveHwProfile"),
    primaryModelCard: $("primaryModelCard"),
    modelsCatalog: $("modelsCatalog"),
    pullProgress: $("pullProgress"),
    pullBarFill: $("pullBarFill"),
    pullStatus: $("pullStatus"),
    pullTitle: $("pullTitle"),
    pullModelName: $("pullModelName"),
    pullPercent: $("pullPercent"),
    pullError: $("pullError"),
    pullPhases: $("pullPhases"),
    modelActionFeedback: $("modelActionFeedback"),
    toastStack: $("toastStack"),
    busyBanner: $("busyBanner"),
    busyBannerText: $("busyBannerText"),
    btnForceCancel: $("btnForceCancel"),
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
  const MODEL_PREF_KEY = "forge_preferred_model";

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
    const [base, tag = ""] = String(name).split(":");
    const baseL = base.toLowerCase();
    const tagL = tag.toLowerCase();
    return list.some((m) => {
      const [mb, mt = ""] = String(m).split(":");
      if (mb.toLowerCase() !== baseL) return false;
      if (!tagL) return true;
      const mtL = mt.toLowerCase();
      return mtL === tagL || mtL.startsWith(`${tagL}-`);
    });
  }

  function catalogEntryForModel(name, catalog) {
    const list = catalog || state.modelRecommendations?.catalog || [];
    const lower = String(name || "").toLowerCase();
    return list.find((e) => String(e.ollama_name || "").toLowerCase() === lower) || null;
  }

  function modelFitsHardware(name, catalog) {
    const entry = catalogEntryForModel(name, catalog);
    if (!entry) return true;
    return entry.fits !== false;
  }

  function modelOptionLabel(name, catalog) {
    if (modelFitsHardware(name, catalog)) return name;
    return `${name} (exige mais memória*)`;
  }

  function warnIfModelTooLarge(selected) {
    if (!selected) return;
    if (modelFitsHardware(selected)) return;
    const entry = catalogEntryForModel(selected);
    const need = entry?.ram_gb ? `~${entry.ram_gb} GB RAM` : "mais memória";
    const profileHint =
      state.profileMode === "manual"
        ? "Pelo perfil “Meu PC” atual este modelo ainda parece exigente."
        : "O Forge está medindo o <strong>servidor</strong> (pode ser um túnel/container). Defina o perfil “Meu PC” se a sua máquina for maior.";
    showToast(
      `<strong>${escapeHtml(selected)}</strong> pode exigir ${escapeHtml(String(need))}. ${profileHint} Você ainda pode usá-lo se o Ollama rodar no PC certo.`,
      "info",
      8000
    );
  }

  function rememberModelPreference(model) {
    try {
      if (!model) localStorage.removeItem(MODEL_PREF_KEY);
      else localStorage.setItem(MODEL_PREF_KEY, model);
    } catch (_) {
      /* ignore */
    }
  }

  function readModelPreference() {
    try {
      return localStorage.getItem(MODEL_PREF_KEY) || "";
    } catch (_) {
      return "";
    }
  }

  function syncHwProfileFieldsEnabled() {
    const manual = !!els.hwModeManual?.checked;
    els.hwProfileFields?.classList.toggle("is-disabled", !manual);
  }

  function fillHardwarePresets(presets) {
    if (!els.hwPreset) return;
    const current = els.hwPreset.value;
    const opts = ['<option value="">Personalizado…</option>'].concat(
      (presets || []).map(
        (p) =>
          `<option value="${escapeHtml(p.id)}">${escapeHtml(p.label || p.id)}</option>`
      )
    );
    els.hwPreset.innerHTML = opts.join("");
    if (current && [...els.hwPreset.options].some((o) => o.value === current)) {
      els.hwPreset.value = current;
    }
  }

  function applyPresetToFields(presetId, presets) {
    const preset = (presets || state.userSettings?.presets || []).find((p) => p.id === presetId);
    if (!preset) return;
    if (els.hwRam) els.hwRam.value = preset.ram_total_gb ?? "";
    if (els.hwVram) els.hwVram.value = preset.vram_total_gb ?? "";
    if (els.hwCores) els.hwCores.value = preset.cpu_cores ?? "";
    if (els.hwHasGpu) els.hwHasGpu.checked = !!preset.has_gpu;
  }

  function renderHardwareSettings(settings) {
    if (!settings) return;
    state.userSettings = settings;
    fillHardwarePresets(settings.presets || []);
    const mode = settings.hardware_mode === "manual" ? "manual" : "detected";
    if (els.hwModeManual) els.hwModeManual.checked = mode === "manual";
    if (els.hwModeDetected) els.hwModeDetected.checked = mode !== "manual";
    const profile = settings.hardware_profile || {};
    if (els.hwPreset) els.hwPreset.value = settings.hardware_preset || "";
    if (els.hwRam) els.hwRam.value = profile.ram_total_gb ?? "";
    if (els.hwVram) els.hwVram.value = profile.vram_total_gb ?? "";
    if (els.hwCores) els.hwCores.value = profile.cpu_cores ?? "";
    if (els.hwHasGpu) els.hwHasGpu.checked = !!profile.has_gpu;
    if (els.hwGpuName) els.hwGpuName.value = profile.gpu_name || "";
    syncHwProfileFieldsEnabled();
  }

  async function saveHardwareProfile() {
    const mode = els.hwModeManual?.checked ? "manual" : "detected";
    const payload = {
      hardware_mode: mode,
      hardware_preset: els.hwPreset?.value || "",
      hardware_profile: {
        ram_total_gb: els.hwRam?.value ? Number(els.hwRam.value) : null,
        vram_total_gb: els.hwVram?.value ? Number(els.hwVram.value) : null,
        cpu_cores: els.hwCores?.value ? Number(els.hwCores.value) : null,
        has_gpu: !!els.hwHasGpu?.checked,
        gpu_name: els.hwGpuName?.value?.trim() || "",
      },
    };
    if (mode === "manual" && !(payload.hardware_profile.ram_total_gb > 0)) {
      showToast("Informe a RAM do seu PC (ex.: 40) para o perfil manual.", "err");
      return;
    }
    if (els.btnSaveHwProfile) els.btnSaveHwProfile.disabled = true;
    try {
      const data = await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
      renderHardwareSettings(data.settings);
      state.profileMode = data.settings?.hardware_mode || mode;
      showToast(
        mode === "manual"
          ? "Perfil “Meu PC” salvo. Catálogo e Auto atualizados."
          : "Usando hardware detectado do servidor.",
        "ok"
      );
      await loadModelRecommendations({ refresh: true });
    } catch (err) {
      showToast(err.message || "Falha ao salvar perfil", "err");
    } finally {
      if (els.btnSaveHwProfile) els.btnSaveHwProfile.disabled = false;
    }
  }

  function getSelectedModel() {
    return resolveModelForRequest();
  }

  function topBarModelValue() {
    const value = els.modelSelect?.value || "__auto__";
    if (value === "__auto__") return null;
    if (value === "__custom__") {
      const custom = els.modelCustomInput?.value.trim();
      return custom || null;
    }
    return value || null;
  }

  function resolveModelForRequest() {
    const top = topBarModelValue();
    const composerVal = els.composerModelSelect?.value || "";
    // Prefer an explicit non-empty composer only when top is Auto.
    if (!top && composerVal) return composerVal;
    if (top) return top;
    return null;
  }

  function syncModelSelectorsFromCanonical() {
    const top = topBarModelValue();
    const composerVal = els.composerModelSelect?.value || "";
    // If they diverge, top bar wins (Work toolbar); mirror into composer.
    if (top && els.composerModelSelect) {
      const opts = Array.from(els.composerModelSelect.options).map((o) => o.value);
      if (opts.includes(top)) els.composerModelSelect.value = top;
    } else if (!top && composerVal) {
      // Composer had a model while top was Auto — promote composer to top.
      setModelSelection(composerVal, { skipComposer: true });
    } else if (!top && els.composerModelSelect) {
      els.composerModelSelect.value = "";
    }
  }

  function pickFittingInstalledModel(avoidName) {
    const catalog = state.modelRecommendations?.catalog || [];
    const installed = state.models || [];
    const avoid = String(avoidName || "").toLowerCase();
    const recommended = state.recommendedModel;
    if (
      recommended &&
      recommended.toLowerCase() !== avoid &&
      installed.includes(recommended) &&
      modelFitsHardware(recommended)
    ) {
      return recommended;
    }
    const fitting = catalog
      .filter((e) => e.installed && e.fits !== false && String(e.ollama_name || "").toLowerCase() !== avoid)
      .sort((a, b) => (b.score || 0) - (a.score || 0));
    if (fitting[0]?.ollama_name) return fitting[0].ollama_name;
    return installed.find((name) => name.toLowerCase() !== avoid && modelFitsHardware(name)) || null;
  }

  function setModelSelection(model, opts = {}) {
    if (!els.modelSelect) return;
    const options = Array.from(els.modelSelect.options).map((o) => o.value);
    if (!model) {
      els.modelSelect.value = "__auto__";
      els.modelCustomInput?.classList.add("hidden");
      if (!opts.skipComposer && els.composerModelSelect) els.composerModelSelect.value = "";
      return;
    }
    if (options.includes(model)) {
      els.modelSelect.value = model;
      els.modelCustomInput?.classList.add("hidden");
    } else {
      els.modelSelect.value = "__custom__";
      if (els.modelCustomInput) {
        els.modelCustomInput.value = model;
        els.modelCustomInput.classList.remove("hidden");
      }
    }
    if (!opts.skipComposer && els.composerModelSelect) {
      const cOpts = Array.from(els.composerModelSelect.options).map((o) => o.value);
      if (cOpts.includes(model)) els.composerModelSelect.value = model;
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

    const previousCanonical = resolveModelForRequest();

    if (els.modelGroupInstalled) {
      els.modelGroupInstalled.innerHTML = (installed || [])
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(modelOptionLabel(name, catalog))}</option>`)
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

    if (els.composerModelSelect) {
      const opts = ['<option value="">Auto</option>']
        .concat((installed || []).map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(modelOptionLabel(name, catalog))}</option>`));
      els.composerModelSelect.innerHTML = opts.join("");
    }

    // Restore a single canonical selection on both selectors.
    const preferred = readModelPreference();
    const restore =
      (previousCanonical && (installed || []).includes(previousCanonical) && previousCanonical) ||
      (preferred && (installed || []).includes(preferred) && preferred) ||
      null;
    setModelSelection(restore);
  }

  // ── API helpers ──

  async function api(path, options = {}) {
    const { headers: extraHeaders, ...rest } = options;
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(extraHeaders || {}) },
      ...rest,
    });
    if (rest.signal?.aborted) {
      const err = new Error("Aborted");
      err.name = "AbortError";
      throw err;
    }
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
    const isInstalled = recommended && list.includes(recommended);
    const current = getSelectedModel();
    const preferred = readModelPreference();
    const isAuto = !els.modelSelect || els.modelSelect.value === "__auto__";

    // Never force-replace an explicit user choice. Prefer saved preference, else keep Auto.
    if (preferred && list.includes(preferred)) {
      if (!current || isAuto) setModelSelection(preferred);
    } else if (isAuto) {
      // Stay on Auto — server picks a fitting model at request time.
      setModelSelection(null);
    }

    if (els.modelHint) {
      if (recommended && !isInstalled) {
        els.modelHint.textContent = `Recomendado: ${recommended} — clique em Modelos IA para baixar.`;
        els.modelHint.classList.remove("hidden");
      } else if (recommended) {
        const src = state.profileMode === "manual" ? "pelo perfil Meu PC" : "pelo hardware detectado";
        els.modelHint.textContent = `Sugestão ${src}: ${recommended} — você pode escolher outro modelo livremente.`;
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

  function readClientHardware() {
    const ua = navigator.userAgent || "";
    let os = "Desconhecido";
    if (/Windows NT/i.test(ua)) os = "Windows";
    else if (/Mac OS X|Macintosh/i.test(ua)) os = "macOS";
    else if (/Android/i.test(ua)) os = "Android";
    else if (/Linux/i.test(ua)) os = "Linux";
    const ram = typeof navigator.deviceMemory === "number" ? navigator.deviceMemory : null;
    return {
      os,
      platform: navigator.platform || "",
      cpu_cores: navigator.hardwareConcurrency || null,
      ram_gb_approx: ram,
      language: navigator.language || "",
    };
  }

  function renderHwStats(container, stats) {
    if (!container) return;
    container.innerHTML = stats
      .map(
        ([label, value]) =>
          `<div class="hw-stat"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(String(value))}</div></div>`
      )
      .join("");
  }

  function renderClientHardware() {
    const client = readClientHardware();
    const stats = [
      ["SO (navegador)", client.os],
      ["CPU (núcleos)", client.cpu_cores != null ? String(client.cpu_cores) : "—"],
      ["RAM aprox.", client.ram_gb_approx != null ? `~${client.ram_gb_approx} GB` : "— (Chrome/Edge)"],
      ["Platform", client.platform || "—"],
    ];
    renderHwStats(els.clientHardwareGrid, stats);
    return client;
  }

  function normalizeOs(name) {
    const raw = String(name || "").toLowerCase();
    if (raw.includes("win")) return "windows";
    if (raw.includes("mac") || raw.includes("darwin")) return "macos";
    if (raw.includes("linux")) return "linux";
    return raw || "unknown";
  }

  function renderHardwareMismatch(serverHw, clientHw) {
    if (!els.hardwareMismatch) return;
    if (!serverHw || !clientHw) {
      els.hardwareMismatch.classList.add("hidden");
      els.hardwareMismatch.textContent = "";
      els.localRunGuide?.classList.add("hidden");
      return;
    }
    const serverOs = normalizeOs(serverHw.os);
    const clientOs = normalizeOs(clientHw.os);
    const host = serverHw.hostname || "servidor";
    const source = serverHw.source || "native";
    const differentOs = serverOs !== "unknown" && clientOs !== "unknown" && serverOs !== clientOs;
    const coreGap =
      serverHw.cpu_cores &&
      clientHw.cpu_cores &&
      Math.abs(Number(serverHw.cpu_cores) - Number(clientHw.cpu_cores)) >= 2;
    const remoteLike = differentOs || source === "container" || source === "wsl";

    if (!differentOs && !coreGap && source === "native") {
      els.hardwareMismatch.classList.add("hidden");
      els.hardwareMismatch.textContent = "";
      els.localRunGuide?.classList.add("hidden");
      return;
    }

    const bits = [];
    if (differentOs) {
      bits.push(
        `O navegador está em <strong>${escapeHtml(clientHw.os)}</strong>, mas o Forge/Ollama rodam em <strong>${escapeHtml(
          `${serverHw.os} (${host})`
        )}</strong>.`
      );
    } else if (coreGap) {
      bits.push(
        `CPU do navegador (${escapeHtml(String(clientHw.cpu_cores))} núcleos) difere do servidor Forge (${escapeHtml(
          String(serverHw.cpu_cores)
        )} núcleos em <strong>${escapeHtml(host)}</strong>).`
      );
    }
    if (source === "wsl") {
      bits.push("Detecção via WSL — o perfil é do ambiente Linux, não do Windows host completo.");
    } else if (source === "container") {
      bits.push("Forge parece estar em container/túnel remoto — o hardware reportado é da VM (ex.: host <code>cursor</code>), não deste PC.");
    }
    bits.push(
      "Baixar modelo e recomendações usam o <strong>servidor</strong>. Para GPU/RAM deste PC, rode o Forge localmente (passos abaixo)."
    );
    els.hardwareMismatch.innerHTML = bits.join(" ");
    els.hardwareMismatch.classList.remove("hidden");

    if (els.localRunGuide) {
      const showGuide = remoteLike && clientOs === "windows";
      els.localRunGuide.classList.toggle("hidden", !showGuide);
      if (showGuide && els.localRunCommands) {
        els.localRunCommands.textContent =
          "# Na pasta do repositório no seu Windows\n" +
          "ollama serve\n\n" +
          "powershell -ExecutionPolicy Bypass -File .\\scripts\\run-platform.ps1\n\n" +
          "# Depois abra http://127.0.0.1:8787 (SO deve ser Windows, host != cursor)";
      }
    }
  }

  function renderHardware(hw) {
    if (!hw) {
      if (els.hardwareGrid) els.hardwareGrid.textContent = "Não foi possível detectar hardware.";
      return;
    }
    const gpu = hw.gpus?.length ? hw.gpus.map((g) => g.name).join(", ") : "Nenhuma detectada";
    const when = hw.detected_at
      ? new Date(hw.detected_at * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
      : "—";
    const profileLabel =
      hw.profile_mode === "manual" || hw.scope === "user_profile"
        ? "Meu PC (manual)"
        : "Servidor detectado";
    const stats = [
      ["Perfil", profileLabel],
      ["Host", hw.hostname || "—"],
      ["ID", hw.fingerprint || "—"],
      ["Tier", hw.tier || "?"],
      ["RAM", `${hw.ram_available_gb}/${hw.ram_total_gb} GB`],
      ["VRAM", hw.vram_total_gb ? `${hw.vram_free_gb}/${hw.vram_total_gb} GB` : "—"],
      ["CPU", `${hw.cpu_cores} núcleos`],
      ["Memória útil", `${hw.effective_memory_gb} GB`],
      ["GPU", gpu],
      ["SO", `${hw.os || ""} ${hw.machine || ""}`.trim()],
      ["Ambiente", hw.source || "native"],
      ["Detectado", when],
    ];
    renderHwStats(els.hardwareGrid, stats);
    if (els.hardwareNote && hw.note) {
      els.hardwareNote.textContent = hw.note;
    }
  }

  function modelCardHtml(entry, featured) {
    const tags = (entry.tags || [])
      .map((t) => `<span class="model-tag">${escapeHtml(t)}</span>`)
      .join("");
    const statusTags = [
      entry.installed ? '<span class="model-tag ok">instalado</span>' : '<span class="model-tag warn">não instalado</span>',
      entry.fits
        ? '<span class="model-tag ok">compatível</span>'
        : entry.installed
          ? '<span class="model-tag warn">exige mais memória*</span>'
          : '<span class="model-tag warn">pode não caber</span>',
      entry.recommended ? '<span class="model-tag accent">recomendado</span>' : "",
    ].join("");
    const name = escapeHtml(entry.ollama_name);
    return `
      <h5>${escapeHtml(entry.name)}</h5>
      <p>${escapeHtml(entry.description || "")}</p>
      <div class="model-meta">${tags}${statusTags}</div>
      <p class="model-meta">Ollama: <code>${name}</code> · ~${entry.size_gb} GB · RAM ${entry.ram_gb} GB · VRAM ${entry.vram_gb} GB</p>
      <div class="model-actions">
        <button type="button" class="btn btn-primary btn-sm" data-action="use" data-model="${name}" data-installed="${entry.installed ? "1" : "0"}">Usar</button>
        <button type="button" class="btn btn-ghost btn-sm" data-action="pull" data-model="${name}" ${entry.installed ? "disabled" : ""}>${entry.installed ? "Instalado" : "Baixar"}</button>
      </div>
      <div class="model-pull-slot hidden" data-pull-slot>
        <div class="pull-bar"><div class="pull-bar-fill" data-pull-fill></div></div>
        <p class="model-pull-status" data-pull-status>Preparando...</p>
      </div>
    `;
  }

  function showToast(message, kind = "info", ms = 4200) {
    if (!els.toastStack) return;
    const toast = document.createElement("div");
    toast.className = `toast ${kind === "ok" ? "ok" : kind === "err" ? "err" : "info"}`;
    toast.innerHTML = message;
    els.toastStack.appendChild(toast);
    window.setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.2s ease";
      window.setTimeout(() => toast.remove(), 220);
    }, ms);
  }

  function showBusyBanner(info = {}) {
    if (!els.busyBanner) return;
    const goal = info.goal ? String(info.goal).slice(0, 80) : "";
    const started = info.started_at ? Math.max(0, Math.round(Date.now() / 1000 - Number(info.started_at))) : null;
    const wait = started != null ? ` · ${started}s` : "";
    if (els.busyBannerText) {
      els.busyBannerText.textContent = goal
        ? `Execução em andamento${wait}: ${goal}`
        : `Já existe uma execução neste projeto${wait}. Cancele para liberar.`;
    }
    els.busyBanner.classList.remove("hidden");
    els.btnCancel?.classList.remove("hidden");
    if (els.btnCancel) els.btnCancel.disabled = false;
    if (info.run_id) state.runId = info.run_id;
  }

  function hideBusyBanner() {
    els.busyBanner?.classList.add("hidden");
  }

  function setPullPhase(phase) {
    if (!els.pullPhases) return;
    const order = ["download", "install", "ready"];
    if (phase === "error") {
      els.pullPhases.querySelectorAll("[data-phase]").forEach((el) => {
        if (el.classList.contains("active") || el.classList.contains("done")) {
          el.classList.add("err");
        }
        el.classList.remove("active");
      });
      return;
    }
    const idx = order.indexOf(phase);
    els.pullPhases.querySelectorAll("[data-phase]").forEach((el) => {
      const name = el.getAttribute("data-phase");
      const pos = order.indexOf(name);
      el.classList.remove("active", "done", "err");
      if (pos < idx) el.classList.add("done");
      else if (pos === idx) el.classList.add("active");
    });
  }

  function classifyPullPhase(status) {
    const s = String(status || "").toLowerCase();
    if (/verif|digest|writ|packing|install|success/.test(s)) return "install";
    if (/download|pull|manifest|layer|fetch/.test(s)) return "download";
    return "download";
  }

  function showModelFeedback(message, kind = "info") {
    if (!els.modelActionFeedback) return;
    els.modelActionFeedback.classList.remove("hidden", "ok", "err", "info");
    els.modelActionFeedback.classList.add(kind === "ok" ? "ok" : kind === "err" ? "err" : "info");
    els.modelActionFeedback.innerHTML = message;
    showToast(message, kind);
  }

  function hideModelFeedback() {
    els.modelActionFeedback?.classList.add("hidden");
  }

  function formatPullBytes(value) {
    const n = Number(value) || 0;
    if (n <= 0) return "";
    if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(1)} GB`;
    if (n >= 1024 ** 2) return `${Math.round(n / 1024 ** 2)} MB`;
    if (n >= 1024) return `${Math.round(n / 1024)} KB`;
    return `${n} B`;
  }

  function explainPullError(raw) {
    const msg = String(raw || "Falha desconhecida no download");
    const lower = msg.toLowerCase();
    if (/connection refused|errno 111|ollama offline|failed to connect/i.test(msg)) {
      return {
        title: "Ollama offline",
        detail: `${msg}\n\nInicie o Ollama neste PC (ícone da llama) ou use “Configurar automaticamente”. O download acontece na máquina onde o Forge/Ollama estão rodando.`,
      };
    }
    if (/timeout|timed out/i.test(lower)) {
      return {
        title: "Tempo esgotado",
        detail: `${msg}\n\nO download demorou demais. Verifique a internet e tente de novo.`,
      };
    }
    if (/no space|enospc|disk/i.test(lower)) {
      return {
        title: "Sem espaço em disco",
        detail: `${msg}\n\nLibere espaço e tente novamente.`,
      };
    }
    if (/not found|404|pull model/i.test(lower)) {
      return {
        title: "Modelo não encontrado",
        detail: `${msg}\n\nConfira o nome do modelo no catálogo Ollama.`,
      };
    }
    return { title: "Falha no download", detail: msg };
  }

  function findModelCards(model) {
    return Array.from(document.querySelectorAll(".model-card")).filter((card) =>
      Array.from(card.querySelectorAll("[data-model]")).some((el) => el.dataset.model === model)
    );
  }

  function setModelCardsPulling(model, active) {
    findModelCards(model).forEach((card) => {
      card.classList.toggle("pulling", !!active);
      const slot = card.querySelector("[data-pull-slot]");
      if (slot) slot.classList.toggle("hidden", !active);
    });
    document.querySelectorAll('[data-action="pull"], [data-action="use"]').forEach((btn) => {
      if (active) {
        btn.dataset.prevDisabled = btn.disabled ? "1" : "0";
        btn.disabled = true;
      } else if (btn.dataset.prevDisabled != null) {
        btn.disabled = btn.dataset.prevDisabled === "1";
        delete btn.dataset.prevDisabled;
      }
    });
  }

  function updateCardPullProgress(model, percent, statusText) {
    findModelCards(model).forEach((card) => {
      const fill = card.querySelector("[data-pull-fill]");
      const status = card.querySelector("[data-pull-status]");
      if (fill) {
        if (percent == null) {
          fill.classList.add("indeterminate");
        } else {
          fill.classList.remove("indeterminate");
          fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
        }
      }
      if (status) status.textContent = statusText;
    });
  }

  function resetPullProgressUi() {
    els.pullProgress?.classList.remove("is-error", "is-success");
    if (els.pullError) {
      els.pullError.textContent = "";
      els.pullError.classList.add("hidden");
    }
    if (els.pullBarFill) {
      els.pullBarFill.classList.remove("indeterminate");
      els.pullBarFill.style.width = "0%";
    }
    if (els.pullPercent) els.pullPercent.textContent = "0%";
  }

  function showPullProgress(model, statusText) {
    resetPullProgressUi();
    els.pullProgress?.classList.remove("hidden");
    if (els.pullTitle) els.pullTitle.textContent = "Baixando modelo";
    if (els.pullModelName) els.pullModelName.textContent = model;
    if (els.pullStatus) els.pullStatus.textContent = statusText || `Iniciando download de ${model}...`;
    if (els.pullPercent) els.pullPercent.textContent = "…";
    els.pullBarFill?.classList.add("indeterminate");
    setPullPhase("download");
    els.pullProgress?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function updatePullProgress(model, ev) {
    const pct = ev.percent != null ? Math.round(Number(ev.percent)) : null;
    const completed = formatPullBytes(ev.completed);
    const total = formatPullBytes(ev.total);
    const sizeBit = completed && total ? ` (${completed} / ${total})` : completed ? ` (${completed})` : "";
    const phase = classifyPullPhase(ev.status);
    setPullPhase(phase);
    const phaseLabel = phase === "install" ? "Instalando" : "Baixando";
    if (els.pullTitle) {
      els.pullTitle.textContent = phase === "install" ? "Instalando modelo no Ollama" : "Baixando modelo";
    }
    const statusText = `${ev.status || `${phaseLabel} ${model}...`}${sizeBit}${pct != null ? ` — ${pct}%` : ""}`;

    if (els.pullStatus) els.pullStatus.textContent = statusText;
    if (pct != null) {
      els.pullBarFill?.classList.remove("indeterminate");
      if (els.pullBarFill) els.pullBarFill.style.width = `${pct}%`;
      if (els.pullPercent) els.pullPercent.textContent = `${pct}%`;
    } else {
      els.pullBarFill?.classList.add("indeterminate");
      if (els.pullPercent) els.pullPercent.textContent = "…";
    }
    updateCardPullProgress(model, pct, statusText);
  }

  function finishPullProgress(model, success, errorMsg) {
    els.pullBarFill?.classList.remove("indeterminate");
    if (success) {
      setPullPhase("ready");
      els.pullProgress?.classList.add("is-success");
      els.pullProgress?.classList.remove("is-error");
      if (els.pullBarFill) els.pullBarFill.style.width = "100%";
      if (els.pullPercent) els.pullPercent.textContent = "100%";
      if (els.pullTitle) els.pullTitle.textContent = "Modelo instalado";
      if (els.pullStatus) els.pullStatus.textContent = `${model} instalado e pronto para uso.`;
      if (els.pullError) els.pullError.classList.add("hidden");
      updateCardPullProgress(model, 100, "Instalado com sucesso");
      showModelFeedback(`Modelo <strong>${escapeHtml(model)}</strong> instalado com sucesso.`, "ok");
      showToast(`Modelo ${escapeHtml(model)} instalado.`, "ok", 5000);
    } else {
      setPullPhase("error");
      const explained = explainPullError(errorMsg);
      els.pullProgress?.classList.add("is-error");
      els.pullProgress?.classList.remove("is-success");
      if (els.pullTitle) els.pullTitle.textContent = explained.title;
      if (els.pullStatus) els.pullStatus.textContent = "O download/instalação não foi concluído.";
      if (els.pullError) {
        els.pullError.textContent = explained.detail;
        els.pullError.classList.remove("hidden");
      }
      if (els.pullPercent) els.pullPercent.textContent = "Erro";
      updateCardPullProgress(model, null, explained.title);
      showModelFeedback(`Falha ao baixar <strong>${escapeHtml(model)}</strong>: ${escapeHtml(explained.title)}`, "err");
    }
  }

  function isSetupModalVisible() {
    return !!(els.setupModal && !els.setupModal.classList.contains("hidden"));
  }

  function bindModelCardActions(container) {
    container.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const model = btn.dataset.model;
        if (!model) return;
        if (btn.dataset.action === "use") {
          const installed = btn.dataset.installed === "1";
          if (!installed) {
            showModelFeedback(
              `O modelo <strong>${escapeHtml(model)}</strong> ainda não está instalado. Iniciando download...`,
              "info"
            );
            pullModel(model, { autoConfigure: true, showProgress: true, setupUI: false });
            return;
          }
          setModelSelection(model);
          rememberModelPreference(model);
          warnIfModelTooLarge(model);
          if (modelFitsHardware(model)) {
            showModelFeedback(`Modelo <strong>${escapeHtml(model)}</strong> selecionado.`, "ok");
            showToast(`Modelo selecionado: ${escapeHtml(model)}`, "ok");
          } else {
            showModelFeedback(
              `<strong>${escapeHtml(model)}</strong> selecionado. Se o Ollama rodar no seu PC potente, pode funcionar mesmo com aviso de memória.`,
              "info"
            );
          }
          return;
        }
        if (btn.dataset.action === "pull") {
          showModelFeedback(`Iniciando download de <strong>${escapeHtml(model)}</strong>...`, "info");
          pullModel(model, { autoConfigure: true, showProgress: true, setupUI: false });
        }
      });
    });
  }

  async function loadModelRecommendations(options = {}) {
    const refresh = !!options.refresh;
    const client = renderClientHardware();
    const data = await api(`/api/models/recommendations${refresh ? "?refresh=1" : ""}`);
    state.modelRecommendations = data;
    state.profileMode = data.profile_mode || data.hardware?.profile_mode || "detected";
    if (data.settings) renderHardwareSettings(data.settings);
    state.models = (data.catalog || []).filter((e) => e.installed).map((e) => e.ollama_name);
    populateModelSelect(
      data.catalog?.filter((e) => e.installed).map((e) => e.ollama_name) || state.models,
      data.catalog || [],
      data.primary?.ollama_name
    );
    applyRecommendedModel(data.primary?.ollama_name, state.models);
    renderHardware(data.hardware);
    renderHardwareMismatch(data.hardware, client);
    if (data.primary) {
      els.primaryModelCard.innerHTML = modelCardHtml(data.primary, true);
      els.primaryModelCard.dataset.model = data.primary.ollama_name || "";
      bindModelCardActions(els.primaryModelCard);
    }
    els.modelsCatalog.innerHTML = (data.catalog || [])
      .map((entry) => `<div class="model-card" data-model="${escapeHtml(entry.ollama_name)}">${modelCardHtml(entry, false)}</div>`)
      .join("");
    bindModelCardActions(els.modelsCatalog);
    if (state.pullingModel && state.pullingModelName) {
      setModelCardsPulling(state.pullingModelName, true);
    }
    updateOllamaOfflineUI();
  }

  function openModelsModal() {
    els.modelsModal.classList.remove("hidden");
    if (!state.pullingModel) {
      els.pullProgress?.classList.add("hidden");
      hideModelFeedback();
    }
    updateOllamaOfflineUI();
    renderClientHardware();
    loadModelRecommendations({ refresh: true }).catch((e) => {
      if (els.hardwareGrid) els.hardwareGrid.textContent = "Erro: " + e.message;
    });
  }

  function closeModelsModal() {
    if (state.pullingModel) {
      showModelFeedback("Aguarde o download terminar antes de fechar.", "info");
      els.pullProgress?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }
    els.modelsModal.classList.add("hidden");
  }

  async function pullModel(model, options = {}) {
    const { showProgress = true, autoConfigure = false, setupUI = false } = options;
    if (state.pullingModel) {
      showModelFeedback(`Já há um download em andamento (${escapeHtml(state.pullingModelName || "modelo")}).`, "info");
      return false;
    }

    const useSetupUi = setupUI && isSetupModalVisible();
    const useModalProgress = showProgress || (els.modelsModal && !els.modelsModal.classList.contains("hidden"));

    if (!state.ollamaOk) {
      if (useModalProgress) {
        showPullProgress(model, "Ollama offline — tentando iniciar/configurar...");
        showModelFeedback("Ollama offline. Tentando iniciar antes do download...", "info");
      }
      const ok = await ensureOllamaRunning(showProgress || setupUI || useModalProgress);
      if (!ok) {
        const err = "Ollama offline — use “Configurar automaticamente” ou inicie o Ollama neste PC.";
        if (useModalProgress) finishPullProgress(model, false, err);
        else if (useSetupUi) finishSetupError(err);
        return false;
      }
    }

    state.pullingModel = true;
    state.pullingModelName = model;
    setModelCardsPulling(model, true);

    if (useSetupUi) {
      setSetupStep("model", "active");
      updateSetupProgress(52, `Baixando modelo ${model}...`, "model");
    }
    if (useModalProgress) {
      showPullProgress(model, `Conectando ao Ollama para baixar ${model}...`);
      updateCardPullProgress(model, null, "Conectando ao Ollama...");
    }

    let success = false;
    let lastError = "";
    try {
      const res = await fetch("/api/models/pull/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 503 || errData.ollama_offline) {
          const started = await ensureOllamaRunning(showProgress || setupUI || useModalProgress);
          state.pullingModel = false;
          state.pullingModelName = null;
          setModelCardsPulling(model, false);
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
          if (ev.type === "started") {
            if (useModalProgress) updatePullProgress(model, { status: "Download iniciado", percent: 0 });
          }
          if (ev.type === "progress") {
            const pct = ev.percent != null ? Math.round(ev.percent) : null;
            if (useSetupUi) {
              const overall = pct != null ? 52 + Math.round(pct * 0.4) : 55;
              const label = pct != null
                ? `Baixando ${model}... ${pct}%${ev.status ? " — " + ev.status : ""}`
                : ev.status || `Baixando ${model}...`;
              updateSetupProgress(overall, label, "model");
            }
            if (useModalProgress) updatePullProgress(model, ev);
          }
          if (ev.type === "done") {
            success = !!ev.ok;
            lastError = ev.error || "";
            if (useSetupUi) {
              if (success) {
                setSetupStep("model", "done");
                setSetupStep("config", "active");
                updateSetupProgress(94, `Modelo ${model} instalado — configurando...`, "config");
              } else {
                finishSetupError(`Falha ao baixar ${model}: ${ev.error || "desconhecido"}`);
              }
            }
            if (useModalProgress) finishPullProgress(model, success, lastError || "desconhecido");
          }
          if (ev.type === "error") {
            lastError = ev.error || "download falhou";
            if (ev.ollama_offline) {
              state.ollamaOk = false;
              updateOllamaOfflineUI();
            }
            if (useSetupUi) finishSetupError("Erro: " + lastError);
            if (useModalProgress) finishPullProgress(model, false, lastError);
          }
        }
      }
      await checkHealth();
      await loadModelRecommendations();
      if (success && autoConfigure) {
        setModelSelection(model);
        applyRecommendedModel(model, state.models);
        if (els.modelHint) els.modelHint.classList.add("hidden");
        if (useSetupUi) setSetupStep("config", "done");
        if (useModalProgress) {
          showModelFeedback(`Modelo <strong>${escapeHtml(model)}</strong> instalado e selecionado.`, "ok");
        }
      }
    } catch (e) {
      lastError = e.message || String(e);
      if (useSetupUi) finishSetupError("Erro: " + lastError);
      if (useModalProgress) finishPullProgress(model, false, lastError);
      success = false;
    } finally {
      state.pullingModel = false;
      state.pullingModelName = null;
      setModelCardsPulling(model, false);
    }
    return success;
  }

  // ── Projects ──

  function formatDate(ts) {
    if (!ts) return "";
    return new Date(ts * 1000).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
  }

  function setSurfaceMode(mode) {
    state.surfaceMode = mode === "work" ? "work" : "chat";
    document.body.classList.toggle("surface-work", state.surfaceMode === "work");
    document.body.classList.toggle("surface-chat", state.surfaceMode === "chat");
    els.btnSurfaceChat?.classList.toggle("active", state.surfaceMode === "chat");
    els.btnSurfaceWork?.classList.toggle("active", state.surfaceMode === "work");
    els.btnSurfaceChat?.setAttribute("aria-selected", state.surfaceMode === "chat" ? "true" : "false");
    els.btnSurfaceWork?.setAttribute("aria-selected", state.surfaceMode === "work" ? "true" : "false");

    if (els.modeSelect) {
      if (state.surfaceMode === "work" && els.modeSelect.value === "chat") {
        els.modeSelect.value = "execute";
      } else if (state.surfaceMode === "chat" && els.modeSelect.value === "execute") {
        els.modeSelect.value = "chat";
      }
      syncModeControls();
    }

    if (els.emptyTitle) {
      els.emptyTitle.textContent =
        state.surfaceMode === "work" ? "No que vamos trabalhar?" : "No que você está pensando hoje?";
    }
    if (els.emptySub) {
      els.emptySub.textContent =
        state.surfaceMode === "work"
          ? "Escolha um projeto ou template. No Work o agente edita código e o preview atualiza."
          : "Converse no Chat ou mude para Work para criar e editar apps no projeto.";
    }
    if (els.promptInput) {
      els.promptInput.placeholder =
        state.surfaceMode === "work" ? "Trabalhe no que quiser…" : "No que você está pensando?";
    }
    if (els.heroTitle) {
      els.heroTitle.textContent =
        state.surfaceMode === "work" ? "No que vamos trabalhar?" : "O que você quer saber?";
    }
    if (els.heroSub) {
      els.heroSub.textContent =
        state.surfaceMode === "work"
          ? "Peça mudanças no código — anexos entram no projeto e o agente aplica o padrão sênior."
          : "Pergunte qualquer coisa. Para alterar arquivos, mude para Work.";
    }
    syncComposerProjectLabel();
    try {
      localStorage.setItem("forge_surface_mode", state.surfaceMode);
    } catch (_) {
      /* ignore */
    }
  }

  function syncComposerProjectLabel() {
    if (els.composerProjectLabel) {
      els.composerProjectLabel.textContent = state.current
        ? `Projeto: ${state.current.name}`
        : "Sem projeto";
    }
  }

  function renderChatList() {
    if (!els.chatList) return;
    els.chatList.innerHTML = "";
    if (!state.chats.length) {
      els.chatList.innerHTML = '<p class="sidebar-empty">Nenhum chat ainda</p>';
      return;
    }
    state.chats.forEach((chat) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chat-item" + (state.current?.id === chat.project_id ? " active" : "");
      btn.innerHTML = `
        <div class="name">${escapeHtml(chat.title || chat.project_name)}</div>
        <div class="meta">${escapeHtml(chat.project_name)} · ${formatDate(chat.updated)}</div>`;
      btn.addEventListener("click", () => {
        setSurfaceMode("chat");
        selectProject(chat.project_id);
        closeSidebar();
      });
      els.chatList.appendChild(btn);
    });
  }

  async function loadChats() {
    try {
      const data = await api("/api/chats?limit=40");
      state.chats = data.chats || [];
      renderChatList();
    } catch (_) {
      state.chats = [];
      renderChatList();
    }
  }

  function renderAttachmentChips() {
    if (!els.attachmentChips) return;
    if (!state.attachments.length) {
      els.attachmentChips.classList.add("hidden");
      els.attachmentChips.innerHTML = "";
      return;
    }
    els.attachmentChips.classList.remove("hidden");
    els.attachmentChips.innerHTML = state.attachments
      .map(
        (file, idx) =>
          `<span class="attachment-chip"><span>${escapeHtml(file.name)}</span><button type="button" data-idx="${idx}" aria-label="Remover">×</button></span>`
      )
      .join("");
    els.attachmentChips.querySelectorAll("button[data-idx]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.attachments.splice(Number(btn.dataset.idx), 1);
        renderAttachmentChips();
      });
    });
  }

  function readFileAsAttachment(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      const isText = /^(text\/|application\/(json|xml|javascript|typescript)|.*\+(json|xml))/.test(file.type) ||
        /\.(txt|md|json|js|ts|tsx|jsx|css|html|htm|py|rs|go|java|sql|yml|yaml|toml|env|sh|svg)$/i.test(file.name);
      reader.onerror = () => reject(new Error(`Falha ao ler ${file.name}`));
      reader.onload = () => {
        if (isText) {
          resolve({
            name: file.name,
            mime: file.type || "text/plain",
            kind: "text",
            content: String(reader.result || ""),
          });
        } else {
          const result = String(reader.result || "");
          const base64 = result.includes(",") ? result.split(",")[1] : result;
          resolve({
            name: file.name,
            mime: file.type || "application/octet-stream",
            kind: "binary",
            content_base64: base64,
          });
        }
      };
      if (isText) reader.readAsText(file);
      else reader.readAsDataURL(file);
    });
  }

  async function addLocalFiles(fileList) {
    const files = Array.from(fileList || []);
    for (const file of files.slice(0, 8)) {
      if (file.size > 2_000_000) {
        showToast(`Arquivo grande demais: ${escapeHtml(file.name)} (máx. 2 MB)`, "err");
        continue;
      }
      try {
        const attachment = await readFileAsAttachment(file);
        state.attachments.push(attachment);
      } catch (err) {
        showToast(err.message || "Falha ao ler arquivo", "err");
      }
    }
    renderAttachmentChips();
  }

  async function uploadAttachmentsForSend() {
    if (!state.attachments.length) return [];
    if (!state.current) {
      showToast("Abra ou crie um projeto para anexar arquivos.", "err");
      throw new Error("project required for attachments");
    }
    const uploaded = [];
    for (const file of state.attachments) {
      const body = {
        name: file.name,
        mime: file.mime,
      };
      if (file.kind === "text") body.content = file.content;
      else body.content_base64 = file.content_base64;
      const saved = await api(`/api/projects/${encodeURIComponent(state.current.id)}/attachments`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      uploaded.push(saved);
    }
    return uploaded;
  }

  function buildPromptWithAttachments(prompt, uploaded) {
    if (!uploaded?.length) return prompt;
    const parts = [prompt.trim(), "", "Arquivos anexados pelo usuário:"];
    uploaded.forEach((file) => {
      parts.push(`- ${file.path} (${file.mime || "file"}, ${file.bytes || 0} bytes)`);
      if (file.kind === "text" && file.preview) {
        parts.push("```");
        parts.push(file.preview);
        parts.push("```");
      }
    });
    parts.push("");
    parts.push("Use esses arquivos no contexto da resposta ou das edições.");
    return parts.join("\n");
  }

  function closeComposerMenu() {
    els.composerMenu?.classList.add("hidden");
  }

  function toggleComposerMenu() {
    els.composerMenu?.classList.toggle("hidden");
  }

  function renderProjectList() {
    closeProjectMenu();
    els.projectList.innerHTML = "";
    if (!state.projects.length) {
      els.projectList.innerHTML = '<p class="sidebar-empty">Nenhum projeto ainda</p>';
      els.btnProjectsMore?.classList.add("hidden");
      return;
    }
    const limit = state.projectsShowAll ? state.projects.length : 8;
    const visible = state.projects.slice(0, limit);
    visible.forEach((p) => {
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
        setSurfaceMode("work");
        selectProject(p.id);
        closeSidebar();
      });
      item.querySelector(".project-menu-btn")?.addEventListener("click", (event) => {
        event.stopPropagation();
        openProjectMenu(p, event.currentTarget);
      });
      els.projectList.appendChild(item);
    });
    if (els.btnProjectsMore) {
      const more = state.projects.length > 8;
      els.btnProjectsMore.classList.toggle("hidden", !more);
      els.btnProjectsMore.textContent = state.projectsShowAll ? "Ver menos" : "Ver mais";
    }
  }

  function closeProjectMenu() {
    document.querySelectorAll(".project-menu").forEach((menu) => menu.remove());
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
    loadChats().catch(() => {});
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
    syncComposerProjectLabel();
    renderChatList();
    try {
      localStorage.setItem(LAST_PROJECT_KEY, id);
    } catch {
      /* private mode */
    }
    renderProjectList();
    closeSidebar();
    await loadChat();
    await loadRunHistory();
    await loadChats().catch(() => {});
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

  const SIDEBAR_COLLAPSED_KEY = "forge_sidebar_collapsed";

  function isSidebarCollapsed() {
    return !!els.sidebar?.classList.contains("collapsed");
  }

  function setSidebarCollapsed(collapsed) {
    if (!els.sidebar) return;
    els.sidebar.classList.toggle("collapsed", !!collapsed);
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
    } catch (_) {
      /* ignore */
    }
    if (els.btnCollapseSidebar) {
      els.btnCollapseSidebar.title = collapsed ? "Expandir menu" : "Recolher menu";
      els.btnCollapseSidebar.setAttribute("aria-expanded", collapsed ? "false" : "true");
    }
  }

  function toggleSidebarCollapsed() {
    setSidebarCollapsed(!isSidebarCollapsed());
  }

  function restoreSidebarCollapsed() {
    try {
      if (localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1") {
        setSidebarCollapsed(true);
        return;
      }
    } catch (_) {
      /* ignore */
    }
    setSidebarCollapsed(false);
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
    const mobile = isMobileLayout();
    els.btnToggleSidebar?.classList.toggle("hidden", !mobile);
    if (!mobile) closeSidebar();
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

  function resetLiveCodeViewer() {
    state.liveCode = { current: null, history: [], autoOpened: false };
    if (els.liveCodeBadge) {
      els.liveCodeBadge.textContent = "aguardando";
      els.liveCodeBadge.className = "live-code-badge";
    }
    if (els.liveCodePath) els.liveCodePath.textContent = "Nenhuma edição ainda";
    if (els.liveCodeStats) els.liveCodeStats.textContent = "";
    if (els.liveCodeBody) {
      els.liveCodeBody.innerHTML =
        "Quando o agente ler ou editar arquivos, o código aparece aqui linha a linha — como no ChatGPT.";
    }
    if (els.liveCodeTimeline) els.liveCodeTimeline.innerHTML = "";
  }

  function liveOpLabel(op, status) {
    if (status === "error") return "erro";
    const map = {
      read: "lendo",
      write: "escrevendo",
      edit: "editando",
      patch: "patch",
      delete: "apagando",
      search: "buscando",
      list: "listando",
      git: "git",
      tool: "ferramenta",
    };
    return map[op] || op || "ação";
  }

  function renderLiveCodeLines(lines) {
    if (!lines || !lines.length) {
      return `<div class="live-code-line is-context"><span class="ln"></span><span class="mark"></span><span>Sem preview de código nesta etapa.</span></div>`;
    }
    return lines
      .map((line) => {
        const kind = line.kind || "context";
        const mark = kind === "add" ? "+" : kind === "del" ? "−" : kind === "focus" ? "›" : kind === "hunk" ? "@" : " ";
        return `<div class="live-code-line is-${escapeHtml(kind)}"><span class="ln">${escapeHtml(String(line.n ?? ""))}</span><span class="mark">${mark}</span><span>${escapeHtml(line.text || "")}</span></div>`;
      })
      .join("");
  }

  function renderLiveCodeTimeline() {
    if (!els.liveCodeTimeline) return;
    const items = (state.liveCode.history || []).slice().reverse().slice(0, 12);
    els.liveCodeTimeline.innerHTML = items
      .map((item) => {
        const label = liveOpLabel(item.op, item.status);
        return `<li><em>${escapeHtml(label)}</em><strong>${escapeHtml(item.path || item.tool || "—")}</strong><span>${escapeHtml(item.headline || "")}</span></li>`;
      })
      .join("");
  }

  function updateLiveCodeViewer(ev, activity) {
    if (!ev || ev.type !== "file_op") return;
    const current = {
      op: ev.op || "tool",
      tool: ev.tool || "",
      path: ev.path || "",
      status: ev.status || "start",
      ok: ev.ok !== false,
      language: ev.language || "text",
      headline: ev.headline || "",
      lines: Array.isArray(ev.lines) ? ev.lines : [],
      stats: ev.stats || {},
      error: ev.error || "",
      at: Date.now(),
    };
    state.liveCode.current = current;
    // Keep a history entry per start/done pair keyed by tool+path+status.
    state.liveCode.history = [...(state.liveCode.history || []), current].slice(-40);

    if (activity) {
      activity.liveOp = current;
      activity.liveOps = state.liveCode.history.slice(-8);
    }

    const badge = liveOpLabel(current.op, current.status);
    if (els.liveCodeBadge) {
      els.liveCodeBadge.textContent = badge;
      els.liveCodeBadge.className = `live-code-badge is-${current.status === "error" ? "error" : current.op}`;
    }
    if (els.liveCodePath) {
      els.liveCodePath.textContent = current.path || current.headline || current.tool || "operação";
    }
    if (els.liveCodeStats) {
      const st = current.stats || {};
      const bits = [];
      if (st.added != null) bits.push(`+${st.added}`);
      if (st.removed != null) bits.push(`−${st.removed}`);
      if (st.total_lines != null) bits.push(`${st.total_lines} linhas`);
      if (current.error) bits.push(current.error);
      els.liveCodeStats.textContent = bits.join(" · ");
    }
    if (els.liveCodeBody) {
      els.liveCodeBody.innerHTML = renderLiveCodeLines(current.lines);
      const view = $("liveCodeView");
      if (view) view.scrollTop = view.scrollHeight;
    }
    renderLiveCodeTimeline();

    if (!state.liveCode.autoOpened && state.surfaceMode === "work") {
      state.liveCode.autoOpened = true;
      switchTab("live");
    }
  }

  function renderActivityLiveMini(activity) {
    const op = activity?.liveOp;
    if (!op) return "";
    const st = op.stats || {};
    const stats = [
      st.added != null ? `+${st.added}` : "",
      st.removed != null ? `−${st.removed}` : "",
      op.path || "",
    ]
      .filter(Boolean)
      .join(" · ");
    return `
      <div class="activity-live-code">
        <div class="live-mini-head">
          <strong>${escapeHtml(op.headline || liveOpLabel(op.op, op.status))}</strong>
          <span>${escapeHtml(stats)}</span>
        </div>
        <pre>${renderLiveCodeLines((op.lines || []).slice(0, 24))}</pre>
      </div>`;
  }

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
      liveOp: null,
      liveOps: [],
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
        ${renderActivityLiveMini(activity)}
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
    hideBusyBanner();
    const runId = state.runId;
    const projectId = state.current?.id;
    const payload = { force: true };
    if (runId) payload.run_id = runId;
    else if (projectId) payload.workspace = `projects/${projectId}`;
    if (runId || projectId) {
      try {
        await fetch("/api/run/cancel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } catch (_) {
        /* ignore */
      }
    }
    if (state.abortController) {
      state.abortController.abort();
    }
    showToast("Execução cancelada — fila liberada.", "info");
  }

  async function sendPrompt() {
    let prompt = els.promptInput.value.trim();
    if ((!prompt && !state.attachments.length) || state.running) return;

    if (!state.current) {
      if (state.surfaceMode === "work" || state.attachments.length) {
        showToast("Escolha ou crie um projeto para continuar no Work / anexos.", "info");
        openNewProjectModal(state.selectedTemplate || "blank");
        return;
      }
      // Chat without project: create a quick inbox-style project.
      const name = `chat-${new Date().toISOString().slice(0, 10).replace(/-/g, "")}-${Math.random().toString(36).slice(2, 6)}`;
      await createProject(name, "blank");
      if (!state.current) return;
    }

    let uploaded = [];
    try {
      uploaded = await uploadAttachmentsForSend();
    } catch (err) {
      showToast(err.message || "Falha ao enviar anexos", "err");
      return;
    }
    if (uploaded.length) {
      prompt = buildPromptWithAttachments(prompt || "Analise os arquivos anexados.", uploaded);
      state.attachments = [];
      renderAttachmentChips();
      loadFiles().catch(() => {});
      showToast(`${uploaded.length} arquivo(s) anexado(s) ao projeto.`, "ok");
    }

    if (!prompt || state.running || !state.current) return;

    // Capture model once and keep selectors in sync before any routing.
    syncModelSelectorsFromCanonical();
    let selectedModel = resolveModelForRequest();
    if (selectedModel && !modelFitsHardware(selectedModel)) {
      warnIfModelTooLarge(selectedModel);
      const fallback = pickFittingInstalledModel(selectedModel);
      if (fallback) {
        showToast(
          `Modelo ${escapeHtml(selectedModel)} pode falhar por memória. Usando ${escapeHtml(fallback)} nesta execução.`,
          "info",
          6500
        );
        setModelSelection(fallback);
        rememberModelPreference(fallback);
        selectedModel = fallback;
      }
    }

    // Keep surface mode and modeSelect aligned.
    if (state.surfaceMode === "work" && els.modeSelect?.value === "chat") {
      els.modeSelect.value = "execute";
      syncModeControls();
    }
    if (state.surfaceMode === "chat" && els.modeSelect?.value === "execute") {
      // Stay chat unless strong create intent below flips it.
    }

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

    // Follow-ups like "implemente as melhorias" need prior chat suggestions attached.
    const enrichedPrompt = enrichImplementPrompt(prompt);

    const mode = els.modeSelect?.value || "chat";
    const explicitWork =
      state.surfaceMode === "work" || mode === "execute" || mode === "plan" || mode === "dry";

    if (mode === "chat") {
      if (
        looksLikeImplementFollowUp(prompt) ||
        looksLikeStrongCreateIntent(prompt) ||
        (offlineScaffold && looksLikeCodeRequest(prompt))
      ) {
        if (els.modeSelect) els.modeSelect.value = "execute";
        syncModeControls();
        if (state.surfaceMode !== "work") setSurfaceMode("work");
        addMessage(
          looksLikeImplementFollowUp(prompt)
            ? "Pedido para aplicar melhorias — executando no projeto e editando arquivos."
            : "Pedido claro de criação — executando no projeto.",
          "system"
        );
        return sendAgentPrompt(enrichedPrompt, "execute", { displayPrompt: prompt, model: selectedModel });
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
      return sendChatPrompt(prompt, { model: selectedModel });
    }

    // Explicit Executar / Work: never bounce short implement prompts back to Chat.
    if (looksLikeConversationOnly(prompt) && !looksLikeImplementFollowUp(prompt) && !explicitWork) {
      if (els.modeSelect) els.modeSelect.value = "chat";
      syncModeControls();
      addMessage(
        "Isso parece só uma conversa — mudei para Chat (rápido). Use Executar código quando quiser alterar arquivos.",
        "system"
      );
      return sendChatPrompt(prompt, { model: selectedModel });
    }
    if (looksLikeConversationOnly(prompt) && explicitWork && looksLikePureGreeting(prompt)) {
      if (els.modeSelect) els.modeSelect.value = "chat";
      syncModeControls();
      addMessage("Saudação detectada — respondendo no Chat.", "system");
      return sendChatPrompt(prompt, { model: selectedModel });
    }

    return sendAgentPrompt(enrichedPrompt, mode, { displayPrompt: prompt, model: selectedModel });
  }

  function looksLikePureGreeting(text) {
    const lower = String(text || "").trim().toLowerCase();
    if (!lower) return false;
    return /^(oi|ol[aá]|iae|e a[ií]|hey|hi|hello|bom dia|boa tarde|boa noite|tudo bem|como vai|obrigad[oa]|valeu|ok|beleza)[\s!.?]*$/i.test(
      lower
    );
  }

  function looksLikeImplementFollowUp(text) {
    const t = String(text || "").toLowerCase().trim();
    if (!t) return false;
    if (
      /\b(implement(e|ar)?|aplique|aplica|realize|execute|adicione|fa[cç]a|coloque|traga|ponha)\b/i.test(t) &&
      /\b(isso|ess[ea]s?|aquilo|melhorias?|sugest\w*|altera[cç]\w*|mudan[cç]\w*|pedido|no projeto|no c[oó]digo|no chat|o que (voc[eê]|vc) (suger|falou|disse|propôs))\b/i.test(
        t
      )
    ) {
      return true;
    }
    // Common short imperatives from users after a Chat suggestion.
    if (/^implemente(\s+(vc|voc[eê]|as|isso|essas?))?/i.test(t)) return true;
    if (/^(aplica|aplique|fa[cç]a)\s+(as\s+)?(melhorias|sugest|mudan|altera)/i.test(t)) return true;
    return false;
  }

  function lastAgentSuggestionText() {
    if (!els.chatMessages) return "";
    const msgs = [...els.chatMessages.querySelectorAll(".msg.agent")];
    for (let i = msgs.length - 1; i >= 0; i -= 1) {
      const el = msgs[i];
      if (el.classList.contains("live") || el.classList.contains("error")) continue;
      const text = (el.innerText || el.textContent || "").trim();
      if (text.length > 60 && !/^erro:/i.test(text)) return text.slice(0, 4000);
    }
    return "";
  }

  function enrichImplementPrompt(prompt) {
    if (!looksLikeImplementFollowUp(prompt)) return prompt;
    const prior = lastAgentSuggestionText();
    if (!prior) {
      return (
        `${prompt}\n\n` +
        "Instrução: aplique no código do projeto atual as melhorias discutidas no chat. " +
        "Edite os arquivos necessários (HTML/CSS/JS etc.); não responda só com texto."
      );
    }
    return (
      `${prompt}\n\n` +
      "--- Contexto: última sugestão do assistente no chat (APLIQUE isto editando arquivos do projeto) ---\n" +
      `${prior}\n` +
      "--- Fim do contexto ---\n" +
      "Faça as alterações de código agora. Não limite a resposta a explicações."
    );
  }

  function looksLikeConversationOnly(text) {
    const t = String(text || "").trim();
    if (!t) return false;
    const lower = t.toLowerCase();
    if (looksLikeImplementFollowUp(t) || looksLikeCodeRequest(t)) return false;
    // Meta questions about the agent itself should stay in Chat.
    if (
      /\b(descreva|objetivo|projetad[oa]|para que (voc[eê]|vc)|capaz de|voc[eê] (consegue|pode|foi)|seu (prop[oó]sito|objetivo)|o que (voc[eê]|vc) (é|e|faz))\b/i.test(
        lower
      )
    ) {
      return true;
    }
    if (t.length <= 120) {
      if (looksLikePureGreeting(t)) return true;
      if (
        /\b(pergunt|d[uú]vida|s[oó] (quero )?pergunt|conversar|me explica|explique|o que (é|e)|como funciona|por\s*qu[eê]|voc[eê] (é|e|pode))\b/i.test(
          lower
        )
      ) {
        return true;
      }
    }
    // Do NOT treat every short imperative as chat — that blocked "implemente as melhorias".
    return false;
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
    if (t.length < 8) return false;
    if (looksLikeImplementFollowUp(t)) return true;
    // Capability / purpose questions are conversation, not build requests.
    if (
      /\b(descreva|objetivo|projetad[oa]|para que (voc[eê]|vc)|capaz de|voc[eê] (consegue|pode|foi)|seu (prop[oó]sito|objetivo))\b/i.test(
        t
      )
    ) {
      return false;
    }
    // Pure questions / explanations stay in Chat even if they mention "site"/"app".
    if (
      /^(me )?(explica|explique|o que|qual|como funciona|por\s*qu[eê]|pode (me )?(dizer|explicar))\b/i.test(t) ||
      (/\b(me explica|o que (é|e|significa)|s[oó] (uma )?pergunt|como funciona)\b/i.test(t) &&
        !/\b(cri(e|ar)|implement|adicion|alter|edit|corrig|refator|melhor(e|ar)|faz(er)?)\b/i.test(t))
    ) {
      return false;
    }
    const hasAction =
      /\b(cri(e|ar)|faz(er)?|implement(e|ar)?|adicion(e|ar)?|alter(e|ar)?|edit(e|ar)?|corrig(a|ir)?|refator(e|ar)?|melhor(e|ar)|redesenh(e|ar)?|build|gera(r)?|escrev(a|er)|mont(e|ar)|atualiz(e|ar)|aplique|aplica)\b/i.test(
        t
      );
    const hasTarget =
      /\b(landing|website|site|app|aplicativ|html|css|react|vite|api|arquivo|c[oó]digo|componente|p[aá]gina|endpoint|fun[cç][aã]o|layout|ui|ux|dashboard|backend|frontend|visual|estilo|navbar|hero|formul[aá]rio|melhorias?|sugest\w*|mudan[cç]\w*|altera[cç]\w*|projeto)\b/i.test(
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

  async function sendChatPrompt(prompt, opts = {}) {
    state.pendingPrompt = null;
    hideBusyBanner();
    addMessage(prompt, "user");
    els.promptInput.value = "";
    updateChatHeroVisibility();
    state.running = true;
    state.runId = null;
    state.abortController = new AbortController();
    els.btnSend.disabled = true;
    els.btnCancel?.classList.remove("hidden");
    if (els.btnCancel) els.btnCancel.disabled = false;

    const statusEl = addMessage("pensando...", "progress");
    const agentEl = addMessage("", "agent live");
    setThinkingState(agentEl);
    let wasAbort = false;
    let fullText = "";
    let elapsed = 0;
    const waitTimer = window.setInterval(() => {
      elapsed += 1;
      if (statusEl.isConnected && !fullText) {
        statusEl.textContent = `Chat · carregando resposta… ${elapsed}s (pode demorar se o modelo estiver frio)`;
      }
    }, 1000);
    const modelForRequest = opts.model !== undefined ? opts.model : resolveModelForRequest();

    try {
      await persistMessage("user", prompt);
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: state.abortController.signal,
        body: JSON.stringify({
          prompt,
          workspace: state.current.path,
          model: modelForRequest || "",
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
            if (els.btnCancel) els.btnCancel.disabled = false;
            statusEl.textContent = `Chat · ${ev.model || "auto"} · ${elapsed}s`;
          } else if (ev.type === "chat_chunk" && ev.text) {
            if (statusEl.isConnected) statusEl.textContent = `Chat · respondendo… ${elapsed}s`;
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
      clearThinkingState(agentEl);
      agentEl.classList.remove("live", "thinking");
      if (e.status === 409 || e.data?.busy) {
        agentEl.textContent = e.message || "Já existe uma execução neste projeto.";
        agentEl.classList.add("error");
        showBusyBanner(e.data || {});
        showToast("Projeto ocupado — clique em Cancelar e liberar.", "err", 6000);
      } else if (e.name === "AbortError") {
        wasAbort = true;
        agentEl.textContent = "Chat cancelado.";
        agentEl.classList.add("error");
        hideBusyBanner();
      } else if (e.status === 503 || e.data?.ollama_offline) {
        const ready = await ensureEnvironment({ pullRecommended: true, showProgress: true });
        if (ready) {
          els.promptInput.value = prompt;
          state.running = false;
          window.clearInterval(waitTimer);
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
      window.clearInterval(waitTimer);
      state.running = false;
      state.runId = null;
      state.abortController = null;
      els.btnSend.disabled = false;
      if (!els.busyBanner || els.busyBanner.classList.contains("hidden")) {
        els.btnCancel?.classList.add("hidden");
      }
      if (els.btnCancel) els.btnCancel.disabled = false;
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
    const displayPrompt = opts.displayPrompt || prompt;
    resetLiveCodeViewer();
    addMessage(displayPrompt, "user");
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
    const activity = createRunActivity(displayPrompt);
    startActivityTimer(progressEl, activity);
    const agentEl = addMessage("", "agent live");
    let wasAbort = false;
    const modelForRequest =
      opts.model !== undefined ? opts.model : resolveModelForRequest();

    try {
      await persistMessage("user", displayPrompt);

      const res = await fetch("/api/run/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: state.abortController.signal,
        body: JSON.stringify({
          prompt,
          workspace: state.current.path,
          model: modelForRequest,
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
      let streamError = null;

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
          if (ev.type === "error") {
            streamError = ev.error || ev.message || "Erro na execução";
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
      } else if (streamError) {
        const err = new Error(String(streamError));
        err.streamError = true;
        throw err;
      } else {
        agentEl.textContent = agentEl.textContent || "Execução finalizada sem relatório.";
        agentEl.classList.add("error");
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
          looksLikeOfflineScaffoldGoal(displayPrompt) &&
          mode !== "plan" &&
          !state._offlineScaffoldRetried
        ) {
          state._offlineScaffoldRetried = true;
          state.ollamaOk = false;
          updateOllamaOfflineUI();
          els.promptInput.value = displayPrompt;
          state.running = false;
          removeMessage(agentEl);
          removeMessage(progressEl);
          addMessage(
            "Ollama offline — tentando scaffold determinístico (HTML/React/API)…",
            "system"
          );
          return sendAgentPrompt(prompt, mode, {
            offlineRetry: true,
            displayPrompt,
            model: modelForRequest,
          });
        }
        state._offlineScaffoldRetried = false;
        const ready = await ensureEnvironment({ pullRecommended: true, showProgress: true });
        if (ready) {
          els.promptInput.value = displayPrompt;
          state.running = false;
          removeMessage(agentEl);
          removeMessage(progressEl);
          return sendAgentPrompt(prompt, mode, { displayPrompt, model: modelForRequest });
        }
        state.ollamaOk = false;
        updateOllamaOfflineUI();
        const err = e.message || "Ollama offline.";
        agentEl.textContent = "Erro: " + err;
        agentEl.classList.add("error");
        openModelsModal();
      } else {
        const raw = String(e.message || "erro desconhecido");
        const isOom =
          /insufficient memory|n[aã]o cabe na mem[oó]ria|mem[oó]ria insuficiente|failed to allocate|out of memory|http error 500/i.test(
            raw
          );
        if (isOom && !opts.oomRetried) {
          const fallback = pickFittingInstalledModel(modelForRequest);
          if (fallback && fallback !== modelForRequest) {
            setModelSelection(fallback);
            rememberModelPreference(fallback);
            state.running = false;
            removeMessage(agentEl);
            addMessage(
              `Modelo sem memória suficiente — repetindo a execução com <strong>${escapeHtml(fallback)}</strong>.`,
              "system"
            );
            return sendAgentPrompt(prompt, mode, {
              displayPrompt,
              model: fallback,
              oomRetried: true,
            });
          }
        }
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
              els.promptInput.value = displayPrompt;
              state.running = false;
              removeMessage(agentEl);
              removeMessage(progressEl);
              return sendAgentPrompt(prompt, mode, { displayPrompt, model: e.data.model });
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
          detail: "Aguardando o Ollama decidir o que ler ou editar no projeto.",
          llmChars: (activity.llmChars || 0) + (ev.text ? ev.text.length : 0),
        });
        // Don't dump raw JSON tool-calls into the chat — the Ao vivo panel shows code instead.
        break;
      case "file_op": {
        updateLiveCodeViewer(ev, activity);
        const verb = liveOpLabel(ev.op, ev.status);
        updateActivity(activity, {
          phaseId: "work",
          stage: ev.headline || `${verb} código`,
          detail: ev.path
            ? `${verb}: ${ev.path}${ev.error ? ` — ${ev.error}` : ""}`
            : ev.headline || "Operação em arquivo",
        });
        if (agentEl) {
          clearThinkingState(agentEl);
          const st = ev.stats || {};
          const bits = [
            ev.headline || verb,
            ev.path || "",
            st.added != null ? `+${st.added}` : "",
            st.removed != null ? `−${st.removed}` : "",
          ].filter(Boolean);
          agentEl.innerHTML = `<div class="live-inline-status"><strong>${escapeHtml(bits[0] || "Trabalhando no código")}</strong>${bits[1] ? `<span>${escapeHtml(bits.slice(1).join(" · "))}</span>` : ""}</div>`;
        }
        if (ev.path && (ev.op === "write" || ev.op === "edit" || ev.op === "patch") && ev.status === "done") {
          markChangedFiles([ev.path]);
          scheduleFileRefresh(activity);
          if (isUiPath(ev.path)) {
            window.setTimeout(() => updatePreview(/\.(html?)$/i.test(ev.path) ? ev.path : findPreviewPath()), 600);
          }
        }
        break;
      }
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
    if (document.hidden) return;
    if (state.current && state.previewMode === "dev") {
      state.devPollTimer = setInterval(() => {
        if (document.hidden) {
          stopDevPolling();
          return;
        }
        if (state.current && state.previewMode === "dev") {
          refreshDevStatus()
            .then(() => {
              if (state.devStatus?.running) updatePreview();
            })
            .catch(() => {});
        }
      }, 5000);
    }
  }

  function abortPreviewPoll() {
    if (state.previewPollAbort) {
      try {
        state.previewPollAbort.abort();
      } catch (_) {
        /* ignore */
      }
      state.previewPollAbort = null;
    }
    state.previewPollInFlight = false;
  }

  function stopPreviewPolling() {
    if (state.previewPollTimer) {
      clearInterval(state.previewPollTimer);
      state.previewPollTimer = null;
    }
    abortPreviewPoll();
  }

  async function pollPreviewRevisionOnce() {
    if (document.hidden || state.previewPollInFlight) return;
    if (!state.current || state.previewMode !== "static") return;
    if ($("panelPreview")?.classList.contains("hidden")) return;

    abortPreviewPoll();
    const controller = new AbortController();
    state.previewPollAbort = controller;
    state.previewPollInFlight = true;
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/preview-revision`, {
        signal: controller.signal,
      });
      if (controller.signal.aborted || document.hidden) return;
      const rev = d.revision || null;
      if (state.previewRevision && rev && rev !== state.previewRevision) {
        updatePreview(findPreviewPath());
      }
      state.previewRevision = rev;
    } catch (err) {
      if (err?.name === "AbortError") return;
      /* network suspended / offline — ignore */
    } finally {
      if (state.previewPollAbort === controller) {
        state.previewPollAbort = null;
        state.previewPollInFlight = false;
      }
    }
  }

  function syncPreviewPolling() {
    stopPreviewPolling();
    if (document.hidden) return;
    const previewOpen = !$("panelPreview")?.classList.contains("hidden");
    if (!state.current || state.previewMode !== "static" || !previewOpen) return;
    // Immediate quiet refresh when becoming visible, then slow poll while focused.
    pollPreviewRevisionOnce();
    state.previewPollTimer = setInterval(() => {
      if (document.hidden) {
        stopPreviewPolling();
        return;
      }
      pollPreviewRevisionOnce();
    }, 5000);
  }

  function onDocumentVisibilityChange() {
    if (document.hidden) {
      stopPreviewPolling();
      stopDevPolling();
      return;
    }
    if (state.current && state.previewMode === "static") syncPreviewPolling();
    if (state.current && state.previewMode === "dev") syncDevPolling();
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
    $("panelLive")?.classList.toggle("hidden", name !== "live");
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
  document.addEventListener("visibilitychange", onDocumentVisibilityChange);
  window.addEventListener("pagehide", () => {
    stopPreviewPolling();
    stopDevPolling();
  });
  window.addEventListener("freeze", () => {
    stopPreviewPolling();
    stopDevPolling();
  });

  els.btnToggleSidebar?.addEventListener("click", () => {
    if (isMobileLayout()) {
      if (els.sidebar?.classList.contains("sidebar-open")) closeSidebar();
      else openSidebar();
      return;
    }
    toggleSidebarCollapsed();
  });
  els.btnCollapseSidebar?.addEventListener("click", () => {
    if (isMobileLayout()) closeSidebar();
    else toggleSidebarCollapsed();
  });
  els.sidebar?.querySelector(".logo")?.addEventListener("click", () => {
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
  });
  els.btnSidebarSearch?.addEventListener("click", () => {
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
    requestAnimationFrame(() => {
      els.projectSearch?.focus();
      els.projectSearch?.select?.();
    });
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
  els.btnForceCancel?.addEventListener("click", async () => {
    await cancelRun();
    hideBusyBanner();
  });
  els.modelSelect?.addEventListener("change", () => {
    const custom = els.modelSelect.value === "__custom__";
    els.modelCustomInput?.classList.toggle("hidden", !custom);
    if (custom) {
      els.modelCustomInput?.focus();
      showToast("Digite o nome do modelo Ollama personalizado.", "info");
      return;
    }
    syncModelSelectorsFromCanonical();
    const selected = resolveModelForRequest();
    rememberModelPreference(selected);
    if (!selected) {
      showToast("Modelo: Auto (escolhe conforme o perfil de hardware)", "ok");
      return;
    }
    if (!modelFitsHardware(selected)) {
      warnIfModelTooLarge(selected);
      return;
    }
    showToast(`Modelo selecionado: ${selected}`, "ok");
  });
  els.promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendPrompt();
    }
  });

  els.btnNewProject.addEventListener("click", () => openNewProjectModal("blank"));
  els.btnNewChat?.addEventListener("click", () => {
    setSurfaceMode("chat");
    openNewProjectModal("blank");
  });
  els.btnProjectsMore?.addEventListener("click", () => {
    state.projectsShowAll = !state.projectsShowAll;
    renderProjectList();
  });
  els.btnToggleChats?.addEventListener("click", () => {
    state.chatsExpanded = !state.chatsExpanded;
    els.btnToggleChats.closest(".sidebar-chats-section")?.classList.toggle("collapsed", !state.chatsExpanded);
    els.btnToggleChats.setAttribute("aria-expanded", state.chatsExpanded ? "true" : "false");
  });
  els.btnSurfaceChat?.addEventListener("click", () => setSurfaceMode("chat"));
  els.btnSurfaceWork?.addEventListener("click", () => setSurfaceMode("work"));
  els.btnChooseProjectEmpty?.addEventListener("click", () => {
    setSurfaceMode("work");
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
    openSidebar();
    els.projectSearch?.focus();
  });
  els.btnNewProjectEmpty?.addEventListener("click", () => openNewProjectModal("blank"));
  els.btnPickProject?.addEventListener("click", () => {
    setSurfaceMode("work");
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
    openSidebar();
    els.projectSearch?.focus();
  });
  els.btnComposerPlus?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleComposerMenu();
  });
  els.btnAttachFiles?.addEventListener("click", () => {
    closeComposerMenu();
    els.attachFileInput?.click();
  });
  els.attachFileInput?.addEventListener("change", async () => {
    await addLocalFiles(els.attachFileInput.files);
    els.attachFileInput.value = "";
  });
  document.addEventListener("click", (e) => {
    if (!els.composer?.contains(e.target)) closeComposerMenu();
  });
  els.composerModelSelect?.addEventListener("change", () => {
    const val = els.composerModelSelect.value;
    if (!val) {
      setModelSelection(null);
      rememberModelPreference(null);
      showToast("Modelo: Auto (escolhe conforme o perfil de hardware)", "ok");
      return;
    }
    setModelSelection(val);
    rememberModelPreference(val);
    if (!modelFitsHardware(val)) {
      warnIfModelTooLarge(val);
      return;
    }
    showToast(`Modelo selecionado: ${val}`, "ok");
  });
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
  els.btnRefreshHardware?.addEventListener("click", () => {
    if (els.btnRefreshHardware) els.btnRefreshHardware.disabled = true;
    loadModelRecommendations({ refresh: true })
      .catch((e) => {
        if (els.hardwareGrid) els.hardwareGrid.textContent = "Erro: " + e.message;
      })
      .finally(() => {
        if (els.btnRefreshHardware) els.btnRefreshHardware.disabled = false;
      });
  });
  els.hwModeDetected?.addEventListener("change", syncHwProfileFieldsEnabled);
  els.hwModeManual?.addEventListener("change", syncHwProfileFieldsEnabled);
  els.hwPreset?.addEventListener("change", () => {
    if (!els.hwPreset.value) return;
    if (els.hwModeManual) els.hwModeManual.checked = true;
    syncHwProfileFieldsEnabled();
    applyPresetToFields(els.hwPreset.value, state.userSettings?.presets);
  });
  els.btnSaveHwProfile?.addEventListener("click", () => {
    saveHardwareProfile().catch(() => {});
  });
  els.btnCopyLocalRun?.addEventListener("click", async () => {
    const text = els.localRunCommands?.textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      showModelFeedback("Comandos copiados. Cole no PowerShell na pasta do projeto no Windows.", "ok");
    } catch (_) {
      showModelFeedback("Não foi possível copiar automaticamente — selecione o bloco de comandos e copie (Ctrl+C).", "info");
    }
  });
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
    restoreSidebarCollapsed();
    syncSidebarToggle();
    try {
      const savedSurface = localStorage.getItem("forge_surface_mode");
      setSurfaceMode(savedSurface === "work" ? "work" : "chat");
    } catch (_) {
      setSurfaceMode("chat");
    }
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
