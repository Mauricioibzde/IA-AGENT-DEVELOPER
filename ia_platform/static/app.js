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
    busyStartedAt: null,
    busyTimer: null,
    selectedTemplate: "blank",
    models: [],
    modelRecommendations: null,
    recommendedModel: null,
    autoModel: null,
    suggestedDownload: null,
    activeModel: null,
    activeModelLive: false,
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
    visualApiOk: null,
    lastToolTab: null,
    activeToolGroup: "app",
    surfaceMode: "work", // chat | work
    attachments: [],
    chats: [],
    chatsExpanded: true,
    projectsShowAll: false,
    liveCode: {
      current: null,
      history: [],
      autoOpened: false,
    },
    lastCompareReport: null,
    lastSuiteReport: null,
    visualTargetSimilarity: 0.92,
    visualAutoCompare: false,
    visualReachInFlight: false,
    correctionJob: null,
    correctionTimer: null,
    compareView: "side",
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    sidebar: $("sidebar"),
    sidebarBackdrop: $("sidebarBackdrop"),
    btnToggleSidebar: $("btnToggleSidebar"),
    btnCollapseSidebar: $("btnCollapseSidebar"),
    btnMinimizePanels: $("btnMinimizePanels"),
    btnSidebarSearch: $("btnSidebarSearch"),
    fileSearchInput: $("fileSearchInput"),
    runHistoryList: $("runHistoryList"),
    projectList: $("projectList"),
    chatList: $("chatList"),
    btnToggleChats: $("btnToggleChats"),
    btnSidebarWork: $("btnSidebarWork"),
    btnSidebarChat: $("btnSidebarChat"),
    btnNewChat: $("btnNewChat"),
    btnProjectsMore: $("btnProjectsMore"),
    btnSurfaceChat: $("btnSurfaceChat"),
    btnSurfaceWork: $("btnSurfaceWork"),
    emptyTitle: $("emptyTitle"),
    emptySub: $("emptySub"),
    workHomeActions: $("workHomeActions"),
    emptyChatActions: $("emptyChatActions"),
    btnEmptyGoWork: $("btnEmptyGoWork"),
    btnEmptyNewProject: $("btnEmptyNewProject"),
    btnChooseProjectEmpty: $("btnChooseProjectEmpty"),
    btnNewProjectEmpty: $("btnNewProjectEmpty"),
    compareDropzone: $("compareDropzone"),
    btnUploadMockupPrimary: $("btnUploadMockupPrimary"),
    composerToolHint: $("composerToolHint"),
    mobileTabChat: $("mobileTabChat"),
    btnQuickMockup: $("btnQuickMockup"),
    btnPreviewOpenFiles: $("btnPreviewOpenFiles"),
    btnPreviewGoVisual: $("btnPreviewGoVisual"),
    compareFlow: $("compareFlow"),
    projectBadge: $("projectBadge"),
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
    btnResetProjectLayout: $("btnResetProjectLayout"),
    layoutPresetStatus: $("layoutPresetStatus"),
    btnDeploy: $("btnDeploy"),
    compareResults: $("compareResults"),
    fileEditorSaved: $("fileEditorSaved"),
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
    panelCompare: $("panelCompare"),
    compareViewport: $("compareViewport"),
    compareSuite: $("compareSuite"),
    compareFit: $("compareFit"),
    btnCompareNow: $("btnCompareNow"),
    btnPixelPerfect: $("btnPixelPerfect"),
    btnCapturePreview: $("btnCapturePreview"),
    btnCorrectAuto: $("btnCorrectAuto"),
    btnCorrectPrimary: $("btnCorrectPrimary"),
    btnReachResult: $("btnReachResult"),
    btnVisualAgentBrief: $("btnVisualAgentBrief"),
    comparePrimaryCta: $("comparePrimaryCta"),
    comparePrimaryHint: $("comparePrimaryHint"),
    compareAdvanced: $("compareAdvanced"),
    devErrorPanel: $("devErrorPanel"),
    devErrorSummary: $("devErrorSummary"),
    btnDevErrorRestart: $("btnDevErrorRestart"),
    btnCorrectCancel: $("btnCorrectCancel"),
    compareCorrection: $("compareCorrection"),
    compareCorrectionMeta: $("compareCorrectionMeta"),
    compareCorrectionAttempts: $("compareCorrectionAttempts"),
    btnUploadMockup: $("btnUploadMockup"),
    compareMockupFile: $("compareMockupFile"),
    compareStatus: $("compareStatus"),
    compareTargetUrl: $("compareTargetUrl"),
    compareMockupPath: $("compareMockupPath"),
    compareScore: $("compareScore"),
    compareSuitePanel: $("compareSuitePanel"),
    compareSuiteMeta: $("compareSuiteMeta"),
    compareSuiteList: $("compareSuiteList"),
    compareRouteId: $("compareRouteId"),
    btnBaselineApprove: $("btnBaselineApprove"),
    btnBaselineReject: $("btnBaselineReject"),
    btnBaselineCompare: $("btnBaselineCompare"),
    compareBaselineList: $("compareBaselineList"),
    compareViewTabs: $("compareViewTabs"),
    compareGallery: $("compareGallery"),
    compareRefImg: $("compareRefImg"),
    compareActImg: $("compareActImg"),
    compareDiffImg: $("compareDiffImg"),
    compareOverlayImg: $("compareOverlayImg"),
    compareSliderWrap: $("compareSliderWrap"),
    compareSliderTop: $("compareSliderTop"),
    compareSliderRange: $("compareSliderRange"),
    compareSliderBack: $("compareSliderBack"),
    compareSliderFront: $("compareSliderFront"),
    compareHistoryList: $("compareHistoryList"),
    compareRegionsMeta: $("compareRegionsMeta"),
    compareRegionsList: $("compareRegionsList"),
    workRail: $("workRail"),
    workStepper: $("workStepper"),
    workPlanList: $("workPlanList"),
    workPlanMeta: $("workPlanMeta"),
    workspaceDock: $("workspaceDock"),
    dockCompareStatus: $("dockCompareStatus"),
    dockCompareMeta: $("dockCompareMeta"),
    dockRunList: $("dockRunList"),
    dockMetricTotal: $("dockMetricTotal"),
    dockMetricSuccess: $("dockMetricSuccess"),
    dockMetricFail: $("dockMetricFail"),
    dockBtnReach: $("dockBtnReach"),
    dockBtnVisual: $("dockBtnVisual"),
    projectChanges: $("projectChanges"),
    projectChangesList: $("projectChangesList"),
    projectChangesMeta: $("projectChangesMeta"),
    sidebarResources: $("sidebarResources"),
    resCpuFill: $("resCpuFill"),
    resRamFill: $("resRamFill"),
    resGpuFill: $("resGpuFill"),
    resCpuLabel: $("resCpuLabel"),
    resRamLabel: $("resRamLabel"),
    resGpuLabel: $("resGpuLabel"),
    sidebarResourceHint: $("sidebarResourceHint"),
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
    activeModelBadge: $("activeModelBadge"),
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
    busyBannerTitle: $("busyBannerTitle"),
    busyBannerText: $("busyBannerText"),
    runStatusChip: $("runStatusChip"),
    btnForceCancel: $("btnForceCancel"),
    splitSidebar: $("splitSidebar"),
    splitPanel: $("splitPanel"),
    splitWorkRail: $("splitWorkRail"),
    btnCollapsePanel: $("btnCollapsePanel"),
    appShell: $("appShell"),
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

  function isRunnableModelName(name) {
    const lower = String(name || "").trim().toLowerCase();
    if (!lower) return false;
    return !(
      lower.includes("embed") ||
      lower.includes("embedding") ||
      lower.includes("nomic-embed") ||
      lower.endsWith("-base")
    );
  }

  function isAutoModelSelected() {
    return !resolveModelForRequest();
  }

  function expectedAutoModel() {
    if (state.autoModel && (state.models || []).includes(state.autoModel) && isRunnableModelName(state.autoModel)) {
      return state.autoModel;
    }
    const recommended = state.recommendedModel;
    if (recommended && (state.models || []).includes(recommended) && isRunnableModelName(recommended)) {
      return recommended;
    }
    // Never advertise a model that is not installed.
    return (
      pickFittingInstalledModel(null) ||
      (state.models || []).find((name) => isRunnableModelName(name)) ||
      null
    );
  }

  function updateActiveModelDisplay(model, opts = {}) {
    const live = !!opts.live;
    const source = opts.source || (isAutoModelSelected() ? "auto" : "manual");
    const resolved = (model || "").trim() || null;
    if (resolved) state.activeModel = resolved;
    else if (!live) state.activeModel = expectedAutoModel();
    state.activeModelLive = live && !!state.activeModel;

    const shown = state.activeModel;
    const auto = isAutoModelSelected() || source === "auto";
    const offline = state.ollamaOk === false;

    if (els.activeModelBadge) {
      els.activeModelBadge.classList.toggle("is-offline", offline);
      if (offline) {
        els.activeModelBadge.textContent = "Ollama offline";
        els.activeModelBadge.classList.remove("is-live", "is-manual");
        els.activeModelBadge.title = "Ollama offline · clique para configurar";
      } else if (!shown) {
        els.activeModelBadge.textContent = "Auto";
        els.activeModelBadge.classList.remove("is-live", "is-manual");
        els.activeModelBadge.title = "Auto · clique para abrir Modelos IA";
      } else if (auto) {
        els.activeModelBadge.textContent = live ? `Usando ${shown}` : `Auto → ${shown}`;
        els.activeModelBadge.classList.toggle("is-live", live);
        els.activeModelBadge.classList.remove("is-manual");
        els.activeModelBadge.title = live
          ? `Execução em andamento com ${shown}`
          : `No modo Auto o Forge usará: ${shown}`;
      } else {
        els.activeModelBadge.textContent = live ? `Usando ${shown}` : shown;
        els.activeModelBadge.classList.toggle("is-live", live);
        els.activeModelBadge.classList.add("is-manual");
        els.activeModelBadge.title = `Modelo selecionado: ${shown}`;
      }
    }

    const topAuto = els.modelSelect?.querySelector('option[value="__auto__"]');
    if (topAuto) {
      topAuto.textContent = shown ? `Auto → ${shown}` : "Auto (recomendado)";
    }
    const composerAuto = els.composerModelSelect?.querySelector('option[value=""]');
    if (composerAuto) {
      composerAuto.textContent = shown ? `Auto · ${shown}` : "Auto";
    }

    if (els.healthStatus && state.ollamaOk) {
      const modelLabel = auto
        ? shown
          ? ` · Auto → ${shown}`
          : " · Auto"
        : ` · ${shown || getSelectedModel() || "modelo"}`;
      const liveMark = state.activeModelLive ? " ●" : "";
      const serverOld = !state.platformVersion && !state.serverFeatures?.full_setup_stream;
      const serverHint = serverOld ? ' · <span class="status-warn">backend v1</span>' : "";
      els.healthStatus.innerHTML = `<span class="status-dot ok"></span>Ollama pronto${escapeHtml(modelLabel)}${liveMark}${serverHint}`;
      els.healthStatus.title = "Ollama ok · clique para abrir Modelos";
      els.healthStatus.classList.remove("is-offline");
    }
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
    if (top && !isRunnableModelName(top)) {
      setModelSelection(null);
      rememberModelPreference(null);
      showToast(`Modelo ${escapeHtml(top)} não serve para chat/execução. Usando Auto.`, "info", 6000);
      return null;
    }
    if (!top && composerVal && !isRunnableModelName(composerVal)) {
      els.composerModelSelect.value = "";
      rememberModelPreference(null);
      showToast(`Modelo ${escapeHtml(composerVal)} é de embeddings. Usando Auto.`, "info", 6000);
      return null;
    }
    // Prefer an explicit non-empty composer only when top is Auto.
    if (!top && composerVal) return composerVal;
    if (top) return top;
    return null;
  }

  function syncModelSelectorsFromCanonical() {
    const top = topBarModelValue();
    const composerVal = els.composerModelSelect?.value || "";
    // Composer is the primary picker (Lovable shell); keep hidden top select in sync.
    if (composerVal) {
      setModelSelection(composerVal, { skipComposer: true });
    } else if (top && els.composerModelSelect) {
      const opts = Array.from(els.composerModelSelect.options).map((o) => o.value);
      if (opts.includes(top)) els.composerModelSelect.value = top;
      else els.composerModelSelect.value = "";
    } else if (!top && els.composerModelSelect) {
      els.composerModelSelect.value = "";
    }
  }

  function pickFittingInstalledModel(avoidName) {
    const catalog = state.modelRecommendations?.catalog || [];
    const installed = (state.models || []).filter(isRunnableModelName);
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

  function isModelMemoryError(message) {
    return /insufficient memory|n[aã]o cabe na mem[oó]ria|mem[oó]ria insuficiente|failed to allocate|out of memory|http error 500|internal server error/i.test(
      String(message || "")
    );
  }

  function banAndSwitchFromBrokenModel(brokenName, reason) {
    const broken = String(brokenName || "").trim();
    const current = resolveModelForRequest();
    if (broken && current && current.toLowerCase() === broken.toLowerCase()) {
      rememberModelPreference(null);
    } else if (broken && readModelPreference()?.toLowerCase() === broken.toLowerCase()) {
      rememberModelPreference(null);
    }
    const fallback = pickFittingInstalledModel(broken);
    if (fallback) {
      setModelSelection(fallback);
      rememberModelPreference(fallback);
      showToast(
        `${reason || "Modelo sem memória"} — trocando para <strong>${escapeHtml(fallback)}</strong>.`,
        "info",
        7000
      );
      return fallback;
    }
    setModelSelection(null);
    rememberModelPreference(null);
    showToast(`${reason || "Modelo sem memória"} — usando Auto.`, "info", 7000);
    return null;
  }

  function modelNameFromError(message) {
    const m = String(message || "").match(/modelo ['"]([^'"]+)['"]/i);
    return m ? m[1] : resolveModelForRequest();
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

    const runnableInstalled = (installed || []).filter(isRunnableModelName);
    const installedSet = new Set(runnableInstalled);
    const recommendedNames = new Set();
    (catalog || []).forEach((entry) => {
      if (entry.recommended || entry.ollama_name === recommended) {
        recommendedNames.add(entry.ollama_name);
      }
    });

    const previousCanonical = resolveModelForRequest();

    if (els.modelGroupInstalled) {
      els.modelGroupInstalled.innerHTML = runnableInstalled
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
        .concat(runnableInstalled.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(modelOptionLabel(name, catalog))}</option>`));
      els.composerModelSelect.innerHTML = opts.join("");
    }

    // Restore a single canonical selection on both selectors.
    // Never resurrect a preferred model that does not fit this host (e.g. 32b on 16GB).
    const preferred = readModelPreference();
    const usablePreferred =
      preferred && runnableInstalled.includes(preferred) && modelFitsHardware(preferred, catalog)
        ? preferred
        : null;
    if (preferred && !usablePreferred) {
      rememberModelPreference(null);
    }
    const usablePrevious =
      previousCanonical &&
      runnableInstalled.includes(previousCanonical) &&
      modelFitsHardware(previousCanonical, catalog)
        ? previousCanonical
        : null;
    const restore = usablePrevious || usablePreferred || null;
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

    const list = (installed || state.models || []).filter(isRunnableModelName);
    const isInstalled = recommended && isRunnableModelName(recommended) && list.includes(recommended);
    const current = getSelectedModel();
    const preferred = readModelPreference();
    const isAuto = !els.modelSelect || els.modelSelect.value === "__auto__";

    // Never force-replace an explicit user choice — but drop oversized prefs (32b on 16GB).
    if (preferred && (!isRunnableModelName(preferred) || (list.includes(preferred) && !modelFitsHardware(preferred)))) {
      rememberModelPreference(null);
      if (!current || current === preferred || isAuto) {
        setModelSelection(null);
        showToast(
          `Preferência <strong>${escapeHtml(preferred)}</strong> exige mais memória. Usando Auto (${escapeHtml(recommended || "modelo menor")}).`,
          "info",
          7000
        );
      }
    } else if (preferred && isRunnableModelName(preferred) && list.includes(preferred)) {
      if (!current || isAuto) setModelSelection(preferred);
    } else if (isAuto) {
      // Stay on Auto — server picks a fitting model at request time.
      setModelSelection(null);
    }

    updateActiveModelDisplay(getSelectedModel() || expectedAutoModel(), {
      source: isAutoModelSelected() ? "auto" : "manual",
      live: !!state.activeModelLive,
    });

    if (els.modelHint) {
      const autoName = expectedAutoModel();
      const download = state.suggestedDownload;
      if (autoName && isAutoModelSelected()) {
        const extra =
          download && download !== autoName
            ? ` Para Chat geral mais natural, baixe ${download} em Modelos IA.`
            : "";
        els.modelHint.textContent = `Auto usará ${autoName} agora.${extra}`;
        els.modelHint.classList.remove("hidden");
      } else if (recommended && !isInstalled) {
        els.modelHint.textContent = `Recomendado: ${recommended} — clique em Modelos IA para baixar.`;
        els.modelHint.classList.remove("hidden");
      } else if (recommended) {
        const src = state.profileMode === "manual" ? "pelo perfil Meu PC" : "pelo hardware detectado";
        els.modelHint.textContent = `Sugestão ${src}: ${recommended}.`;
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
      state.autoModel = d.auto_model || null;
      state.suggestedDownload = d.suggested_download || null;
      updateModelOptions(state.models);
      applyRecommendedModel(d.recommended_model || d.auto_model, state.models);
      if (!state.ollamaOk) {
        els.healthStatus.innerHTML = '<span class="status-dot err"></span>Ollama offline · configurar';
        els.healthStatus.title = "Clique para configurar Ollama";
        els.healthStatus.classList.add("is-offline");
        updateActiveModelDisplay(null, { source: "auto", live: false });
      } else {
        updateActiveModelDisplay(getSelectedModel() || expectedAutoModel(), {
          source: isAutoModelSelected() ? "auto" : "manual",
          live: false,
        });
      }
      updateOllamaOfflineUI();
      syncWorkbenchForSurface();
    } catch {
      state.ollamaOk = false;
      els.healthStatus.innerHTML = '<span class="status-dot err"></span>offline · configurar';
      els.healthStatus.title = "Clique para configurar Ollama";
      els.healthStatus.classList.add("is-offline");
      updateActiveModelDisplay(null, { source: "auto", live: false });
      updateOllamaOfflineUI();
      syncWorkbenchForSurface();
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

  function syncRunChrome(opts = {}) {
    const running = !!state.running || opts.forceBusy;
    document.body.classList.toggle("is-running", running);
    els.composer?.classList.toggle("is-running", running);
    if (els.promptInput) els.promptInput.disabled = running;
    if (els.btnSend) els.btnSend.disabled = running;
    if (els.composerModelSelect) els.composerModelSelect.disabled = running;
    if (els.runStatusChip) {
      els.runStatusChip.classList.toggle("hidden", !running);
      if (running) {
        const label = opts.chip || els.busyBannerTitle?.textContent || "Em execução";
        els.runStatusChip.textContent = label;
      }
    }
    if (!running) els.btnForceCancel?.classList.add("hidden");
    updateChatHeroVisibility();
    syncWorkRailVisibility();
    syncComposerToolHint();
  }

  function showBusyBanner(info = {}) {
    if (!els.busyBanner) return;
    const goal = info.goal ? String(info.goal).slice(0, 80) : "";
    const started = info.started_at ? Math.max(0, Math.round(Date.now() / 1000 - Number(info.started_at))) : null;
    const wait = started != null ? ` · ${started}s` : "";
    if (els.busyBannerTitle) {
      els.busyBannerTitle.textContent = info.reconnect ? "Reconectando" : "Executando";
    }
    if (els.busyBannerText) {
      els.busyBannerText.textContent = goal
        ? `${goal}${wait}`
        : `Já existe uma execução neste projeto${wait}. Cancele se precisar.`;
    }
    els.busyBanner.classList.remove("hidden");
    if (els.btnCancel) els.btnCancel.disabled = false;
    els.btnForceCancel?.classList.add("hidden");
    if (info.run_id) state.runId = info.run_id;
    if (info.started_at) state.busyStartedAt = Number(info.started_at);
    else if (!state.busyStartedAt) state.busyStartedAt = Date.now() / 1000;
    startBusyElapsedTimer();
    syncRunChrome({ forceBusy: true, chip: info.reconnect ? "Reconectando…" : "Em execução" });
  }

  function hideBusyBanner() {
    els.busyBanner?.classList.add("hidden");
    stopBusyElapsedTimer();
    state.busyStartedAt = null;
    if (!state.running) syncRunChrome();
  }

  function startBusyElapsedTimer() {
    stopBusyElapsedTimer();
    state.busyTimer = window.setInterval(() => {
      if (!els.busyBanner || els.busyBanner.classList.contains("hidden")) return;
      const base = Number(state.busyStartedAt || 0);
      if (!base) return;
      const secs = Math.max(0, Math.round(Date.now() / 1000 - base));
      const text = els.busyBannerText?.textContent || "";
      const cleaned = text.replace(/\s·\s\d+s$/, "");
      if (els.busyBannerText) els.busyBannerText.textContent = `${cleaned} · ${secs}s`;
      if (els.runStatusChip && !els.runStatusChip.classList.contains("hidden")) {
        const title = els.busyBannerTitle?.textContent || "Em execução";
        els.runStatusChip.textContent = `${title} · ${secs}s`;
      }
      // Liberar fila só após ~25s — evita competir com Cancelar no início.
      if (secs >= 25) els.btnForceCancel?.classList.remove("hidden");
    }, 1000);
  }

  function stopBusyElapsedTimer() {
    if (state.busyTimer) {
      window.clearInterval(state.busyTimer);
      state.busyTimer = null;
    }
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

  function visualEngineAvailable() {
    if (state.serverFeatures && state.serverFeatures.visual_engine === false) return false;
    return state.visualApiOk !== false;
  }

  function setCompareFlowStep(step) {
    if (!els.compareFlow) return;
    const order = ["mockup", "compare", "correct"];
    const idx = order.indexOf(step);
    els.compareFlow.querySelectorAll(".compare-flow-step").forEach((el) => {
      const key = el.dataset.flow;
      const at = order.indexOf(key);
      el.classList.toggle("is-current", key === step);
      el.classList.toggle("is-done", idx >= 0 && at >= 0 && at < idx);
    });
  }

  function openVisualMockupFlow() {
    if (!state.current) {
      showToast("Escolha um projeto para enviar mockup.", "info", 4000);
      openNewProjectModal(state.selectedTemplate || "blank");
      return;
    }
    setSurfaceMode("work");
    showWorkspace();
    switchToolGroup("visual", "compare");
    setCompareFlowStep("mockup");
    requestAnimationFrame(() => els.compareMockupFile?.click());
  }

  function syncComposerToolHint() {
    if (!els.composerToolHint) return;
    if (state.running) {
      els.composerToolHint.textContent = "Executando — Preview e Arquivos atualizam ao concluir";
      return;
    }
    if (state.surfaceMode === "work") {
      els.composerToolHint.textContent = "Work: o agente edita o projeto · Preview à direita";
    } else {
      els.composerToolHint.textContent = "Chat: ideias e dúvidas · Work para construir";
    }
  }

  function syncCompareEmptyState() {
    const hasMockup = !!(els.compareMockupPath?.value || "").trim() || !!state.lastCompareReport;
    const hasReport = !!state.lastCompareReport;
    els.compareDropzone?.classList.toggle("hidden", hasMockup);
    els.compareResults?.classList.toggle("hidden", !hasReport);
    if (hasMockup && !hasReport) {
      els.comparePrimaryCta?.classList.remove("hidden");
      if (els.comparePrimaryHint) {
        els.comparePrimaryHint.textContent =
          "Mockup pronto. Alcançar resultado compara e corrige até a meta.";
      }
    } else if (!hasMockup) {
      els.comparePrimaryCta?.classList.add("hidden");
    }
  }

  function applySurfacePlaceholder() {
    if (!els.promptInput || state.running) return;
    els.promptInput.placeholder =
      state.surfaceMode === "work"
        ? "Peça uma mudança, um componente ou uma correção…"
        : "Pergunte ou converse sobre qualquer coisa…";
  }

  function syncWorkbenchForSurface() {
    const work = state.surfaceMode === "work";
    const visualOk = visualEngineAvailable();
    const hasProject = !!state.current;

    if (!hasProject) {
      els.templateGrid?.classList.remove("hidden");
      els.workHomeActions?.classList.toggle("hidden", !work);
      els.emptyChatActions?.classList.toggle("hidden", work);
    } else {
      els.templateGrid?.classList.add("hidden");
      els.workHomeActions?.classList.add("hidden");
      els.emptyChatActions?.classList.add("hidden");
    }

    if (els.projectBadge) {
      els.projectBadge.textContent = work ? "Work" : "Chat";
      els.projectBadge.dataset.surface = state.surfaceMode;
      els.projectBadge.title = work ? "Modo Work · clique para Chat" : "Modo Chat · clique para Work";
    }

    document.querySelectorAll('.tools-group[data-group="visual"]').forEach((btn) => {
      btn.classList.toggle("hidden", !work || !visualOk);
      btn.disabled = !work || !visualOk;
    });
    $("mobileTabVisual")?.classList.toggle("hidden", !work || !visualOk);

    if (!work && state.activeToolGroup === "visual") {
      switchToolGroup("app", "preview");
    }
    syncComposerToolHint();
    syncCompareEmptyState();
    renderWorkspaceDock();
  }

  function setSurfaceMode(mode) {
    state.surfaceMode = mode === "work" ? "work" : "chat";
    document.body.classList.toggle("surface-work", state.surfaceMode === "work");
    document.body.classList.toggle("surface-chat", state.surfaceMode === "chat");
    els.btnSurfaceChat?.classList.toggle("active", state.surfaceMode === "chat");
    els.btnSurfaceWork?.classList.toggle("active", state.surfaceMode === "work");
    els.btnSurfaceChat?.setAttribute("aria-selected", state.surfaceMode === "chat" ? "true" : "false");
    els.btnSurfaceWork?.setAttribute("aria-selected", state.surfaceMode === "work" ? "true" : "false");
    syncWorkRailVisibility();

    if (els.modeSelect) {
      if (state.surfaceMode === "work" && els.modeSelect.value === "chat") {
        els.modeSelect.value = "execute";
      } else if (state.surfaceMode === "chat" && els.modeSelect.value === "execute") {
        els.modeSelect.value = "chat";
      }
      syncModeControls({ preservePlaceholder: true });
    }

    if (els.emptyTitle) {
      els.emptyTitle.textContent =
        state.surfaceMode === "work" ? "No que vamos trabalhar?" : "No que você está pensando hoje?";
    }
    if (els.emptySub) {
      els.emptySub.textContent =
        state.surfaceMode === "work"
          ? "Escolha um template. Depois: pedir → Preview → Visual (mockup)."
          : "Chat livre para ideias. Quando for construir, crie um projeto e vá para Work.";
    }
    applySurfacePlaceholder();
    if (els.heroTitle) {
      els.heroTitle.textContent =
        state.surfaceMode === "work" ? "No que vamos trabalhar?" : "No que você está pensando?";
    }
    if (els.heroSub) {
      els.heroSub.textContent =
        state.surfaceMode === "work"
          ? "Peça mudanças no código. Use Preview, Arquivos ou Visual (mockup) à direita."
          : "Converse sobre qualquer assunto. Para criar/editar o app, use Work.";
    }
    document.querySelectorAll(".quick-card--chat").forEach((el) => {
      el.classList.toggle("hidden", state.surfaceMode === "work");
    });
    document.querySelectorAll(".quick-card--work").forEach((el) => {
      el.classList.toggle("hidden", state.surfaceMode === "chat");
    });
    syncSidebarNavState();
    syncWorkbenchForSurface();
    syncComposerProjectLabel();
    renderWorkspaceDock();
    restoreLayoutSizes();
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
    els.btnComposerPlus?.setAttribute("aria-expanded", "false");
  }

  function toggleComposerMenu() {
    const isOpen = !els.composerMenu?.classList.contains("hidden");
    if (isOpen) closeComposerMenu();
    else {
      els.composerMenu?.classList.remove("hidden");
      els.btnComposerPlus?.setAttribute("aria-expanded", "true");
    }
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
    state.projectChangeMap = {};
    if (els.projectChanges) els.projectChanges.classList.add("hidden");
    if (els.projectChangesList) els.projectChangesList.innerHTML = "";
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
    restoreLayoutSizes();
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
    syncWorkRailVisibility();
    syncWorkRail(null);
    await resumeActiveRunIfNeeded();
  }

  async function resumeActiveRunIfNeeded() {
    if (!state.current || state.running) return;
    try {
      const info = await api(`/api/projects/${encodeURIComponent(state.current.id)}/active-run`);
      if (!info?.active || !info.run_id) {
        hideBusyBanner();
        return;
      }
      showBusyBanner({ ...info, reconnect: true });
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
    showBusyBanner({ run_id: runId, goal, started_at: Date.now() / 1000, reconnect: true });
    syncRunChrome({ chip: "Reconectando…" });
    const progressEl = addMessage("", "progress");
    const activity = createRunActivity(goal);
    startActivityTimer(progressEl, activity);
    syncWorkRail(activity);
    const agentEl = addMessage("", "agent live");
    setWorkingState(agentEl, "Acompanhando execução", "Status ao vivo — leituras e diffs aparecem aqui", activity);
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
        syncWorkRail(activity);
        if (els.busyBannerText && goal) {
          const n = Number(data.event_count || after || 0);
          els.busyBannerText.textContent =
            n > 0
              ? `Execução em andamento (${n} eventos): ${String(goal).slice(0, 72)}`
              : `Execução em andamento: ${String(goal).slice(0, 80)}`;
        }
        if (donePayload || data.active === false) break;
        await new Promise((r) => setTimeout(r, 900));
      }
      stopActivityTimer(activity);
      finishRunActivity(progressEl, activity, donePayload);
      if (donePayload) {
        const fullReport = donePayload.report || "(sem relatório)";
        const chatSummary = donePayload.summary || fullReport;
        finalizeAgentMessage(agentEl, chatSummary, {
          activity,
          error: donePayload.status === "CANCELLED" || /^FAIL|FAILED|Erro/i.test(String(donePayload.status || "")),
        });
        state.lastReport = fullReport;
        await syncWorkspaceAfterRun(donePayload);
        renderRunArtifacts({
          report: fullReport,
          created_files: donePayload.created_files || [],
          modified_files: donePayload.modified_files || [],
          summary: chatSummary,
        });
        addMessage("Execução retomada e concluída.", "system");
        window.setTimeout(() => removeMessage(progressEl), 6500);
      } else {
        finalizeAgentMessage(agentEl, "Execução finalizada.", { error: true, activity });
        window.setTimeout(() => removeMessage(progressEl), 2500);
      }
    } catch (e) {
      stopActivityTimer(activity);
      finalizeAgentMessage(agentEl, "Falha ao reconectar: " + (e.message || String(e)), {
        error: true,
        activity,
      });
    } finally {
      state.running = false;
      state.runId = null;
      hideBusyBanner();
      syncRunChrome();
      syncWorkRail(null);
      syncModeControls();
    }
  }

  async function followBusyRun(info, { systemNote } = {}) {
    const runId = info?.run_id;
    if (!runId) return false;
    showBusyBanner(info);
    if (systemNote) addMessage(systemNote, "system");
    showToast("Projeto ocupado — acompanhando a execução atual.", "info", 5000);
    await pollActiveRun(runId, info.goal || "Execução em andamento");
    return true;
  }

  async function checkActiveRunStillAlive() {
    if (!state.current?.id) return null;
    try {
      const info = await api(`/api/projects/${encodeURIComponent(state.current.id)}/active-run`);
      if (info?.active && info.run_id) return info;
    } catch {
      /* ignore */
    }
    return null;
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
    renderWorkspaceDock();
    renderProjectList();
    syncWorkbenchForSurface();
    syncWorkRailVisibility();
  }

  function showWorkspace() {
    els.emptyView?.classList.add("hidden");
    els.workspaceView?.classList.remove("hidden");
    restoreLayoutSizes();
    syncWorkbenchForSurface();
    syncWorkRailVisibility();
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

  const LAYOUT_KEYS = {
    sidebarW: "forge.layout.sidebarW",
    panelWChat: "forge.layout.panelWChat",
    panelWWork: "forge.layout.panelWWork",
    panelCollapsedChat: "forge.layout.panelCollapsedChat",
    panelCollapsedWork: "forge.layout.panelCollapsedWork",
    workRailH: "forge.layout.workRailH",
  };
  const LAYOUT_DEFAULTS = {
    sidebarW: 268,
    panelWChat: 390,
    panelWWork: 640,
    workRailH: 112,
  };
  const LAYOUT_LIMITS = {
    sidebarMin: 200,
    sidebarMax: 440,
    panelMin: 260,
    panelMaxRatio: 0.62,
    workRailMin: 72,
    workRailMax: 280,
  };
  const LAYOUT_PRESETS = {
    chat: {
      label: "Foco Chat",
      sidebarW: 220,
      panelWChat: 300,
      panelWWork: 340,
      panelCollapsedChat: true,
      panelCollapsedWork: true,
      workRailH: 72,
    },
    preview: {
      label: "Foco Preview",
      sidebarW: 220,
      panelWChat: 520,
      panelWWork: 680,
      panelCollapsedChat: false,
      panelCollapsedWork: false,
      workRailH: 88,
    },
    balanced: {
      label: "Equilibrado",
      sidebarW: LAYOUT_DEFAULTS.sidebarW,
      panelWChat: LAYOUT_DEFAULTS.panelWChat,
      panelWWork: LAYOUT_DEFAULTS.panelWWork,
      panelCollapsedChat: true,
      panelCollapsedWork: false,
      workRailH: LAYOUT_DEFAULTS.workRailH,
    },
  };

  function layoutProjectKey(key) {
    const pid = state.current?.id;
    return pid ? `${key}::${pid}` : key;
  }

  function readLayoutNumber(key, fallback, { projectScoped = false } = {}) {
    try {
      if (projectScoped && state.current?.id) {
        const scoped = localStorage.getItem(layoutProjectKey(key));
        if (scoped != null && scoped !== "") {
          const n = Number(scoped);
          if (Number.isFinite(n)) return n;
        }
      }
      const raw = localStorage.getItem(key);
      if (raw == null || raw === "") return fallback;
      const n = Number(raw);
      return Number.isFinite(n) ? n : fallback;
    } catch {
      return fallback;
    }
  }

  function writeLayoutNumber(key, value, { projectScoped = false } = {}) {
    try {
      const out = String(Math.round(value));
      if (projectScoped && state.current?.id) {
        localStorage.setItem(layoutProjectKey(key), out);
      } else {
        localStorage.setItem(key, out);
      }
    } catch {
      /* ignore */
    }
  }

  function readLayoutFlag(key, fallback, { projectScoped = false } = {}) {
    try {
      if (projectScoped && state.current?.id) {
        const scoped = localStorage.getItem(layoutProjectKey(key));
        if (scoped != null) return scoped === "1" || scoped === "true";
      }
      const raw = localStorage.getItem(key);
      if (raw == null) return fallback;
      return raw === "1" || raw === "true";
    } catch {
      return fallback;
    }
  }

  function writeLayoutFlag(key, value, { projectScoped = false } = {}) {
    try {
      if (projectScoped && state.current?.id) {
        localStorage.setItem(layoutProjectKey(key), value ? "1" : "0");
      } else {
        localStorage.setItem(key, value ? "1" : "0");
      }
    } catch {
      /* ignore */
    }
  }

  function currentPanelWidthKey() {
    return state.surfaceMode === "work" ? LAYOUT_KEYS.panelWWork : LAYOUT_KEYS.panelWChat;
  }

  function currentPanelCollapsedKey() {
    return state.surfaceMode === "work" ? LAYOUT_KEYS.panelCollapsedWork : LAYOUT_KEYS.panelCollapsedChat;
  }

  function defaultPanelWidth() {
    return state.surfaceMode === "work" ? LAYOUT_DEFAULTS.panelWWork : LAYOUT_DEFAULTS.panelWChat;
  }

  function clamp(n, min, max) {
    return Math.min(max, Math.max(min, n));
  }

  function applySidebarWidth(px, { persist = false } = {}) {
    const width = clamp(px, LAYOUT_LIMITS.sidebarMin, LAYOUT_LIMITS.sidebarMax);
    document.documentElement.style.setProperty("--sidebar-w", `${width}px`);
    if (els.splitSidebar) {
      els.splitSidebar.setAttribute("aria-valuenow", String(Math.round(width)));
    }
    if (persist) writeLayoutNumber(LAYOUT_KEYS.sidebarW, width, { projectScoped: true });
    if (persist) syncLayoutPresetIndicator();
    return width;
  }

  function applyPanelWidth(px, { persist = false } = {}) {
    const body = document.querySelector(".workspace-body");
    const avail = body?.clientWidth || window.innerWidth;
    const max = Math.max(
      LAYOUT_LIMITS.panelMin,
      Math.floor(avail * LAYOUT_LIMITS.panelMaxRatio)
    );
    const width = clamp(px, LAYOUT_LIMITS.panelMin, max);
    document.documentElement.style.setProperty("--panel-w", `${width}px`);
    if (els.splitPanel) {
      els.splitPanel.setAttribute("aria-valuenow", String(Math.round(width)));
      els.splitPanel.setAttribute("aria-valuemax", String(max));
    }
    if (persist) writeLayoutNumber(currentPanelWidthKey(), width, { projectScoped: true });
    if (persist) syncLayoutPresetIndicator();
    return width;
  }

  function applyWorkRailHeight(px, { persist = false } = {}) {
    const height = clamp(px, LAYOUT_LIMITS.workRailMin, LAYOUT_LIMITS.workRailMax);
    document.documentElement.style.setProperty("--work-rail-h", `${height}px`);
    if (els.splitWorkRail) {
      els.splitWorkRail.setAttribute("aria-valuenow", String(Math.round(height)));
      els.splitWorkRail.setAttribute("aria-valuemax", String(LAYOUT_LIMITS.workRailMax));
    }
    if (persist) writeLayoutNumber(LAYOUT_KEYS.workRailH, height, { projectScoped: true });
    if (persist) syncLayoutPresetIndicator();
    return height;
  }

  function canResizeWorkRail() {
    return state.surfaceMode === "work" && !!state.current && !isMobileLayout();
  }

  function syncWorkRailSplitter() {
    if (!els.splitWorkRail) return;
    const show = canResizeWorkRail() && !els.workRail?.classList.contains("hidden");
    els.splitWorkRail.classList.toggle("hidden", !show);
  }

  function isPanelCollapsed() {
    return !!els.workspaceView?.classList.contains("panel-collapsed");
  }

  function setPanelCollapsed(collapsed, { persist = true } = {}) {
    if (!els.workspaceView) return;
    els.workspaceView.classList.toggle("panel-collapsed", !!collapsed);
    if (els.btnCollapsePanel) {
      els.btnCollapsePanel.setAttribute("aria-expanded", collapsed ? "false" : "true");
      els.btnCollapsePanel.title = collapsed
        ? "Expandir painel de ferramentas"
        : "Recolher painel de ferramentas";
    }
    if (els.splitPanel) {
      els.splitPanel.title = collapsed
        ? "Clique para expandir o painel de ferramentas"
        : "Arraste para redimensionar · duplo clique restaura";
      els.splitPanel.setAttribute(
        "aria-label",
        collapsed ? "Expandir painel de ferramentas" : "Redimensionar painel de ferramentas"
      );
    }
    if (persist) writeLayoutFlag(currentPanelCollapsedKey(), !!collapsed, { projectScoped: true });
    if (persist) syncLayoutPresetIndicator();
  }

  function togglePanelCollapsed() {
    setPanelCollapsed(!isPanelCollapsed());
  }

  function restoreLayoutSizes() {
    const sidebarW = readLayoutNumber(LAYOUT_KEYS.sidebarW, LAYOUT_DEFAULTS.sidebarW, {
      projectScoped: true,
    });
    applySidebarWidth(sidebarW);
    const panelKey = currentPanelWidthKey();
    const panelDefault = defaultPanelWidth();
    const panelW = readLayoutNumber(panelKey, panelDefault, { projectScoped: true });
    applyPanelWidth(panelW);
    const collapsedDefault = state.surfaceMode === "chat";
    const collapsed = readLayoutFlag(currentPanelCollapsedKey(), collapsedDefault, {
      projectScoped: true,
    });
    setPanelCollapsed(collapsed, { persist: false });
    const workRailH = readLayoutNumber(LAYOUT_KEYS.workRailH, LAYOUT_DEFAULTS.workRailH, {
      projectScoped: true,
    });
    applyWorkRailHeight(workRailH);
    syncWorkRailSplitter();
    els.workspaceView?.setAttribute("data-layout-ready", "1");
    syncLayoutPresetIndicator();
  }

  function resetSidebarWidth() {
    applySidebarWidth(LAYOUT_DEFAULTS.sidebarW, { persist: true });
    showToast("Largura do menu restaurada.", "info", 2200);
  }

  function resetPanelWidth() {
    applyPanelWidth(defaultPanelWidth(), { persist: true });
    setPanelCollapsed(false);
    showToast("Largura do painel restaurada.", "info", 2200);
  }

  function resetWorkRailHeight() {
    applyWorkRailHeight(LAYOUT_DEFAULTS.workRailH, { persist: true });
    showToast("Altura do fluxo restaurada.", "info", 2200);
  }

  function readProjectLayoutSnapshot() {
    return {
      sidebarW: readLayoutNumber(LAYOUT_KEYS.sidebarW, LAYOUT_DEFAULTS.sidebarW, { projectScoped: true }),
      panelWChat: readLayoutNumber(LAYOUT_KEYS.panelWChat, LAYOUT_DEFAULTS.panelWChat, { projectScoped: true }),
      panelWWork: readLayoutNumber(LAYOUT_KEYS.panelWWork, LAYOUT_DEFAULTS.panelWWork, { projectScoped: true }),
      panelCollapsedChat: readLayoutFlag(LAYOUT_KEYS.panelCollapsedChat, true, { projectScoped: true }),
      panelCollapsedWork: readLayoutFlag(LAYOUT_KEYS.panelCollapsedWork, false, { projectScoped: true }),
      workRailH: readLayoutNumber(LAYOUT_KEYS.workRailH, LAYOUT_DEFAULTS.workRailH, { projectScoped: true }),
    };
  }

  function detectActiveLayoutPreset() {
    if (!state.current?.id) return null;
    const snap = readProjectLayoutSnapshot();
    const EPS = 16;
    for (const [id, preset] of Object.entries(LAYOUT_PRESETS)) {
      const match =
        Math.abs(snap.sidebarW - preset.sidebarW) <= EPS &&
        Math.abs(snap.panelWChat - preset.panelWChat) <= EPS &&
        Math.abs(snap.panelWWork - preset.panelWWork) <= EPS &&
        snap.panelCollapsedChat === preset.panelCollapsedChat &&
        snap.panelCollapsedWork === preset.panelCollapsedWork &&
        Math.abs(snap.workRailH - preset.workRailH) <= EPS;
      if (match) return id;
    }
    return "custom";
  }

  function syncLayoutPresetIndicator() {
    const active = detectActiveLayoutPreset();
    document.querySelectorAll("[data-layout-preset]").forEach((btn) => {
      const on = !!active && btn.getAttribute("data-layout-preset") === active;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (!els.layoutPresetStatus) return;
    if (!state.current?.id) {
      els.layoutPresetStatus.textContent = "Abra um projeto para aplicar presets.";
      return;
    }
    if (active === "custom") {
      els.layoutPresetStatus.textContent = "Preset ativo: personalizado · atalhos Ctrl+Alt+1/2/3";
      return;
    }
    const label = LAYOUT_PRESETS[active]?.label || "Personalizado";
    els.layoutPresetStatus.textContent = `Preset ativo: ${label} · reset: Ctrl+Alt+0`;
  }

  function clearProjectLayoutPreferences() {
    if (!state.current?.id) {
      showToast("Abra um projeto para resetar o layout.", "info");
      return;
    }
    try {
      Object.values(LAYOUT_KEYS).forEach((key) => {
        localStorage.removeItem(layoutProjectKey(key));
      });
    } catch {
      /* ignore */
    }
    restoreLayoutSizes();
    syncLayoutPresetIndicator();
    showToast("Layout deste projeto restaurado ao padrão.", "info", 2600);
  }

  function applyLayoutPreset(presetId) {
    const preset = LAYOUT_PRESETS[presetId];
    if (!preset) return;
    if (!state.current?.id) {
      showToast("Abra um projeto para aplicar um preset de layout.", "info");
      return;
    }
    writeLayoutNumber(LAYOUT_KEYS.sidebarW, preset.sidebarW, { projectScoped: true });
    writeLayoutNumber(LAYOUT_KEYS.panelWChat, preset.panelWChat, { projectScoped: true });
    writeLayoutNumber(LAYOUT_KEYS.panelWWork, preset.panelWWork, { projectScoped: true });
    writeLayoutFlag(LAYOUT_KEYS.panelCollapsedChat, preset.panelCollapsedChat, { projectScoped: true });
    writeLayoutFlag(LAYOUT_KEYS.panelCollapsedWork, preset.panelCollapsedWork, { projectScoped: true });
    writeLayoutNumber(LAYOUT_KEYS.workRailH, preset.workRailH, { projectScoped: true });
    restoreLayoutSizes();
    syncLayoutPresetIndicator();
    document.getElementById("topbarMore")?.removeAttribute("open");
    showToast(`Layout aplicado: ${preset.label}`, "info", 2400);
  }

  function initLayoutPresets() {
    document.querySelectorAll("[data-layout-preset]").forEach((btn) => {
      btn.addEventListener("click", () => {
        applyLayoutPreset(btn.getAttribute("data-layout-preset"));
      });
    });
    els.btnResetProjectLayout?.addEventListener("click", () => {
      clearProjectLayoutPreferences();
      document.getElementById("topbarMore")?.removeAttribute("open");
    });
    document.addEventListener("keydown", (e) => {
      if (!(e.ctrlKey && e.altKey)) return;
      const tag = (e.target && e.target.tagName ? e.target.tagName : "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || e.target?.isContentEditable) return;
      if (e.key === "1") {
        e.preventDefault();
        applyLayoutPreset("chat");
      } else if (e.key === "2") {
        e.preventDefault();
        applyLayoutPreset("preview");
      } else if (e.key === "3") {
        e.preventDefault();
        applyLayoutPreset("balanced");
      } else if (e.key === "0") {
        e.preventDefault();
        clearProjectLayoutPreferences();
      }
    });
    syncLayoutPresetIndicator();
  }

  function bindVerticalSplitter(el, { onMove, onReset, onActivate, canDrag }) {
    if (!el) return;

    let dragging = false;
    let startX = 0;
    let startValue = 0;

    const endDrag = () => {
      if (!dragging) return;
      dragging = false;
      el.classList.remove("is-dragging", "is-active");
      els.appShell?.classList.remove("is-layout-resizing");
      els.appShell?.classList.remove("is-row-resizing");
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", endDrag);
      document.removeEventListener("pointercancel", endDrag);
    };

    const onPointerMove = (e) => {
      if (!dragging) return;
      onMove(e.clientX - startX, startValue, e);
    };

    el.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      if (isMobileLayout()) return;
      if (canDrag && !canDrag()) {
        onActivate?.();
        return;
      }
      dragging = true;
      startX = e.clientX;
      const cssVar = el === els.splitSidebar ? "--sidebar-w" : "--panel-w";
      startValue =
        Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue(cssVar)) ||
        Number(el.getAttribute("aria-valuenow") || 0);
      el.classList.add("is-dragging", "is-active");
      els.appShell?.classList.add("is-layout-resizing");
      els.appShell?.classList.remove("is-row-resizing");
      try {
        el.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", endDrag);
      document.addEventListener("pointercancel", endDrag);
      e.preventDefault();
    });

    el.addEventListener("dblclick", (e) => {
      e.preventDefault();
      onReset?.();
    });

    el.addEventListener("keydown", (e) => {
      if (isMobileLayout()) return;
      if (canDrag && !canDrag() && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        onActivate?.();
        return;
      }
      const step = e.shiftKey ? 24 : 12;
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        e.preventDefault();
        const dir = e.key === "ArrowLeft" ? -1 : 1;
        const current = Number.parseFloat(
          getComputedStyle(document.documentElement).getPropertyValue(
            el === els.splitSidebar ? "--sidebar-w" : "--panel-w"
          )
        ) || 0;
        // Sidebar grows to the right with ArrowRight; panel grows with ArrowLeft (drag from left edge of panel).
        if (el === els.splitSidebar) {
          onMove(dir * step, current);
        } else {
          onMove(-dir * step, current);
        }
      } else if (e.key === "Home") {
        e.preventDefault();
        onReset?.();
      }
    });
  }

  function bindHorizontalSplitter(el, { onMove, onReset, canDrag }) {
    if (!el) return;

    let dragging = false;
    let startY = 0;
    let startValue = 0;

    const endDrag = () => {
      if (!dragging) return;
      dragging = false;
      el.classList.remove("is-dragging", "is-active");
      els.appShell?.classList.remove("is-layout-resizing", "is-row-resizing");
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", endDrag);
      document.removeEventListener("pointercancel", endDrag);
    };

    const onPointerMove = (e) => {
      if (!dragging) return;
      onMove(e.clientY - startY, startValue, e);
    };

    el.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      if (canDrag && !canDrag()) return;
      dragging = true;
      startY = e.clientY;
      startValue =
        Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--work-rail-h")) ||
        Number(el.getAttribute("aria-valuenow") || 0);
      el.classList.add("is-dragging", "is-active");
      els.appShell?.classList.add("is-layout-resizing", "is-row-resizing");
      try {
        el.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", endDrag);
      document.addEventListener("pointercancel", endDrag);
      e.preventDefault();
    });

    el.addEventListener("dblclick", (e) => {
      e.preventDefault();
      onReset?.();
    });

    el.addEventListener("keydown", (e) => {
      if (canDrag && !canDrag()) return;
      const step = e.shiftKey ? 20 : 10;
      if (e.key === "ArrowUp" || e.key === "ArrowDown") {
        e.preventDefault();
        const dir = e.key === "ArrowUp" ? -1 : 1;
        const current =
          Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--work-rail-h")) || 0;
        onMove(dir * step, current);
      } else if (e.key === "Home") {
        e.preventDefault();
        onReset?.();
      }
    });
  }

  function initLayoutSplitters() {
    restoreLayoutSizes();

    bindVerticalSplitter(els.splitSidebar, {
      canDrag: () => !isSidebarCollapsed(),
      onMove: (delta, startW) => {
        applySidebarWidth(startW + delta, { persist: true });
      },
      onReset: resetSidebarWidth,
    });

    bindVerticalSplitter(els.splitPanel, {
      canDrag: () => !isPanelCollapsed(),
      onActivate: () => setPanelCollapsed(false),
      onMove: (delta, startW) => {
        // Dragging the left edge of the panel: moving right shrinks the panel.
        applyPanelWidth(startW - delta, { persist: true });
      },
      onReset: resetPanelWidth,
    });

    bindHorizontalSplitter(els.splitWorkRail, {
      canDrag: () => canResizeWorkRail(),
      onMove: (delta, startH) => {
        applyWorkRailHeight(startH + delta, { persist: true });
      },
      onReset: resetWorkRailHeight,
    });

    els.btnCollapsePanel?.addEventListener("click", () => {
      togglePanelCollapsed();
    });

    window.addEventListener("resize", () => {
      if (isMobileLayout()) return;
      // Re-clamp panel against new viewport.
      const current = Number.parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue("--panel-w")
      );
      if (Number.isFinite(current)) applyPanelWidth(current);
      const railCurrent = Number.parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue("--work-rail-h")
      );
      if (Number.isFinite(railCurrent)) applyWorkRailHeight(railCurrent);
      syncWorkRailSplitter();
    });
  }

  const SIDEBAR_COLLAPSED_KEY = "forge_sidebar_collapsed";
  const DESIGN_LAYOUT_VERSION_KEY = "forge.design.layoutVersion";
  const DESIGN_LAYOUT_VERSION = "2026-07-30-workspace-v3";

  function migrateDesignerLayoutOnce() {
    try {
      if (localStorage.getItem(DESIGN_LAYOUT_VERSION_KEY) === DESIGN_LAYOUT_VERSION) return;
      localStorage.setItem("forge_surface_mode", "work");
      localStorage.setItem(LAYOUT_KEYS.panelCollapsedWork, "0");
      localStorage.setItem(LAYOUT_KEYS.panelCollapsedChat, "0");
      localStorage.setItem(LAYOUT_KEYS.panelWWork, "640");
      localStorage.setItem(LAYOUT_KEYS.workRailH, "112");
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, "0");
      Object.keys(localStorage)
        .filter((key) => key.startsWith(`${LAYOUT_KEYS.panelCollapsedWork}::`))
        .forEach((key) => localStorage.setItem(key, "0"));
      Object.keys(localStorage)
        .filter((key) => key.startsWith(`${LAYOUT_KEYS.panelWWork}::`))
        .forEach((key) => localStorage.setItem(key, "640"));
      localStorage.setItem(DESIGN_LAYOUT_VERSION_KEY, DESIGN_LAYOUT_VERSION);
    } catch (_) {
      /* ignore */
    }
  }

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

  function syncSidebarNavState() {
    const workActive = state.surfaceMode === "work";
    els.btnSidebarWork?.classList.toggle("is-active", workActive);
    els.btnSidebarChat?.classList.toggle("is-active", !workActive);
  }

  function runStatusClass(status) {
    if (!status) return "";
    if (status === "SUCCESS") return "ok";
    if (status === "CANCELLED" || status === "PARTIAL_SUCCESS") return "warn";
    return "err";
  }

  function renderWorkspaceDock() {
    if (!els.workspaceDock) return;
    const show = !!state.current && state.surfaceMode === "work" && !isMobileLayout();
    els.workspaceDock.classList.toggle("hidden", !show);
    if (show) {
      els.workspaceDock.removeAttribute("hidden");
      els.workspaceDock.setAttribute("aria-hidden", "false");
    } else {
      els.workspaceDock.setAttribute("hidden", "");
      els.workspaceDock.setAttribute("aria-hidden", "true");
      return;
    }

    const report = state.lastCompareReport;
    const sim = reportSimilarity(report);
    const mockup = (els.compareMockupPath?.value || "").trim() || findProjectMockupPath();
    const compareText = (els.compareStatus?.textContent || "").trim();

    if (els.dockCompareStatus) {
      if (sim != null) {
        els.dockCompareStatus.textContent = `${(sim * 100).toFixed(1)}% similar`;
      } else if (mockup) {
        els.dockCompareStatus.textContent = "Mockup pronto";
      } else if (compareText && !/enviando|comparando/i.test(compareText)) {
        els.dockCompareStatus.textContent = compareText.slice(0, 48);
      } else {
        els.dockCompareStatus.textContent = "Sem comparações";
      }
    }
    if (els.dockCompareMeta) {
      const project = state.current?.name || "projeto";
      if (sim != null && !visualTargetReached(sim)) {
        els.dockCompareMeta.textContent = `Abaixo da meta · ${project}`;
      } else if (sim != null) {
        els.dockCompareMeta.textContent = `Meta ok · ${project}`;
      } else if (mockup) {
        els.dockCompareMeta.textContent = `${mockup.split("/").pop()} · ${project}`;
      } else {
        els.dockCompareMeta.textContent = `Envie um mockup · ${project}`;
      }
    }

    const canReach = !!mockup && visualEngineAvailable();
    els.dockBtnReach?.classList.toggle("hidden", !canReach);
    if (els.dockBtnVisual) {
      els.dockBtnVisual.textContent = mockup ? "Visual" : "Enviar";
    }

    const runs = state.runs || [];
    if (els.dockRunList) {
      if (!runs.length) {
        els.dockRunList.innerHTML = "<li class='muted'>Nenhuma execução</li>";
      } else {
        els.dockRunList.innerHTML = runs
          .slice(0, 2)
          .map((run) => {
            const label = String(run.status || "RUN").toUpperCase();
            const cls = runStatusClass(run.status);
            const goal = (run.goal || run.summary || "Execução").slice(0, 22);
            return `<li><span>${escapeHtml(goal)}</span><strong class="${cls}">${escapeHtml(label)}</strong></li>`;
          })
          .join("");
      }
    }

    const total = runs.length;
    const success = runs.filter((r) => String(r.status || "").toUpperCase() === "SUCCESS").length;
    const fail = runs.filter((r) => {
      const s = String(r.status || "").toUpperCase();
      return s === "FAILED" || s === "ERROR" || s === "FAIL";
    }).length;
    if (els.dockMetricTotal) els.dockMetricTotal.textContent = String(total);
    if (els.dockMetricSuccess) els.dockMetricSuccess.textContent = String(success);
    if (els.dockMetricFail) els.dockMetricFail.textContent = String(fail);
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
      renderWorkspaceDock();
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
    renderWorkspaceDock();
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

  function syncMobileTabs(name, group) {
    const g = group || TAB_TO_GROUP[name] || state.activeToolGroup || "app";
    const tabName = name || state.lastToolTab?.[g] || TOOL_GROUP_DEFAULT[g];
    document.querySelectorAll(".mobile-tab").forEach((tab) => {
      if (tab.dataset.surface === "chat") {
        tab.classList.toggle("active", !state.mobilePanelOpen && state.surfaceMode === "chat");
        return;
      }
      const sameGroup = tab.dataset.group === g;
      const sameTab = !tab.dataset.tab || tab.dataset.tab === tabName;
      tab.classList.toggle("active", state.mobilePanelOpen && sameGroup && sameTab);
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

  function setThinkingState(el, label = "pensando...") {
    if (!el) return;
    el.classList.add("live", "thinking");
    el.innerHTML = `
      <div class="thinking-indicator" aria-live="polite" aria-label="${escapeHtml(label)}">
        <svg class="thinking-brain" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M8.5 4.5c-1.7 0-3 1.4-3 3.1 0 .4.1.8.2 1.1A3.2 3.2 0 0 0 4 11.7c0 1.5 1 2.7 2.4 3.1v.2c0 1.9 1.4 3.5 3.3 3.5h.3c.6 1.1 1.8 1.8 3.1 1.8s2.5-.7 3.1-1.8h.2c1.9 0 3.4-1.6 3.4-3.5v-.1A3.3 3.3 0 0 0 22 11.5a3.2 3.2 0 0 0-2.1-3 3 3 0 0 0 .2-1.1c0-1.7-1.3-3.1-3-3.1-.6 0-1.1.2-1.6.4A3.8 3.8 0 0 0 12 3.5c-1.3 0-2.5.7-3.1 1.7-.5-.4-1.1-.7-1.4-.7Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M12 8.5v7M9.5 10.5c.8-.6 1.7-.9 2.5-.9s1.7.3 2.5.9M9.5 13.5c.8.6 1.7.9 2.5.9s1.7-.3 2.5-.9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <span class="thinking-label">${escapeHtml(label)}</span>
      </div>`;
  }

  function clearThinkingState(el) {
    if (!el) return;
    el.classList.remove("thinking");
    if (el.querySelector(".thinking-indicator")) {
      el.innerHTML = "";
    }
  }

  function ensureCursorWorkbench(el, activity) {
    if (!el) return null;
    el.classList.add("live", "cursor-mode");
    el.classList.remove("thinking");
    let bench = el.querySelector(".cursor-workbench");
    if (!bench) {
      el.innerHTML = `
        <div class="cursor-workbench" aria-live="polite">
          <div class="cursor-status-strip">
            <span class="cursor-pulse" aria-hidden="true"></span>
            <strong class="cursor-status-title">Preparando agente…</strong>
            <span class="cursor-stats">Explored 0 · Edited 0</span>
          </div>
          <div class="cursor-file-cards"></div>
        </div>`;
      bench = el.querySelector(".cursor-workbench");
    }
    if (activity) activity.workbenchEl = el;
    return bench;
  }

  function cursorOpVerb(op, status) {
    if (status === "error") return "Failed";
    if (status === "start") {
      return (
        {
          read: "Reading",
          write: "Writing",
          edit: "Editing",
          patch: "Patching",
          delete: "Deleting",
          search: "Searching",
          list: "Listing",
          git: "Git",
          tool: "Running",
        }[op] || "Working"
      );
    }
    return (
      {
        read: "Read",
        write: "Wrote",
        edit: "Edited",
        patch: "Patched",
        delete: "Deleted",
        search: "Searched",
        list: "Listed",
        git: "Git",
        tool: "Ran",
      }[op] || "Done"
    );
  }

  function updateCursorStats(el, activity) {
    const statsEl = el?.querySelector(".cursor-stats");
    if (!statsEl || !activity) return;
    const explored = activity.exploredFiles || 0;
    const edited = activity.editedFiles || 0;
    const added = activity.linesAdded || 0;
    const removed = activity.linesRemoved || 0;
    const diff = added || removed ? ` · +${added}/−${removed}` : "";
    statsEl.textContent = `Explored ${explored} · Edited ${edited}${diff}`;
  }

  function setWorkingState(el, title, detail = "", activity = null) {
    if (!el) return;
    const bench = ensureCursorWorkbench(el, activity);
    const titleEl = bench?.querySelector(".cursor-status-title");
    if (titleEl) titleEl.textContent = title || "Trabalhando no código";
    if (detail) {
      const cards = bench?.querySelector(".cursor-file-cards");
      // Keep a lightweight note only when there are no file cards yet.
      if (cards && !cards.children.length) {
        cards.innerHTML = `<div class="cursor-empty-note">${escapeHtml(detail)}</div>`;
      }
    }
    updateCursorStats(el, activity);
  }

  function upsertCursorFileCard(el, ev, activity) {
    const bench = ensureCursorWorkbench(el, activity);
    const cards = bench?.querySelector(".cursor-file-cards");
    if (!cards || !ev) return;

    // Remove empty placeholder.
    cards.querySelector(".cursor-empty-note")?.remove();

    const path = ev.path || ev.tool || "arquivo";
    const key = `${ev.tool || ev.op || "op"}::${path}`;
    let card =
      [...cards.querySelectorAll(".cursor-file-card")].find((n) => n.dataset.cardKey === key) || null;
    const isStart = ev.status === "start";
    const verb = cursorOpVerb(ev.op, ev.status);
    const st = ev.stats || {};
    const statsBits = [
      st.added != null ? `+${st.added}` : "",
      st.removed != null ? `−${st.removed}` : "",
      st.total_lines != null ? `${st.total_lines} lines` : "",
    ].filter(Boolean);

    if (!card) {
      card = document.createElement("details");
      card.className = "cursor-file-card";
      card.dataset.cardKey = key;
      card.open = true;
      cards.appendChild(card);
    }

    card.className = `cursor-file-card is-${ev.status === "error" ? "error" : ev.op || "tool"}${
      isStart ? " is-running" : " is-done"
    }`;
    const linesHtml =
      Array.isArray(ev.lines) && ev.lines.length
        ? `<pre class="cursor-diff">${renderLiveCodeLines(ev.lines)}</pre>`
        : isStart
          ? `<pre class="cursor-diff cursor-diff--pending"><div class="live-code-line is-focus"><span class="ln"></span><span class="mark">›</span><span>Aplicando alteração…</span></div></pre>`
          : ev.error
            ? `<pre class="cursor-diff"><div class="live-code-line is-del"><span class="ln"></span><span class="mark">!</span><span>${escapeHtml(ev.error)}</span></div></pre>`
            : `<pre class="cursor-diff"><div class="live-code-line is-context"><span class="ln"></span><span class="mark"></span><span>Sem preview de linhas neste passo.</span></div></pre>`;

    card.innerHTML = `
      <summary>
        <span class="cursor-op">${escapeHtml(verb)}</span>
        <code class="cursor-path">${escapeHtml(path)}</code>
        <span class="cursor-card-stats">${escapeHtml(statsBits.join(" "))}</span>
      </summary>
      ${linesHtml}
    `;

    // Keep latest cards visible.
    while (cards.children.length > 12) cards.removeChild(cards.firstChild);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;

    if (activity) {
      const pathKey = String(path);
      activity.seenPaths = activity.seenPaths || new Set();
      if (pathKey && (ev.op === "read" || ev.op === "search" || ev.op === "list")) {
        if (!activity.seenPaths.has(`r:${pathKey}`)) {
          activity.seenPaths.add(`r:${pathKey}`);
          activity.exploredFiles = (activity.exploredFiles || 0) + 1;
        }
      }
      if (pathKey && (ev.op === "write" || ev.op === "edit" || ev.op === "patch" || ev.op === "delete")) {
        if (!activity.seenPaths.has(`w:${pathKey}`)) {
          activity.seenPaths.add(`w:${pathKey}`);
          activity.editedFiles = (activity.editedFiles || 0) + 1;
        }
        if (ev.status === "done") {
          activity.linesAdded = (activity.linesAdded || 0) + Number(st.added || 0);
          activity.linesRemoved = (activity.linesRemoved || 0) + Number(st.removed || 0);
        }
      }
      const titleEl = bench.querySelector(".cursor-status-title");
      if (titleEl) {
        titleEl.textContent = `${verb} ${path}`;
      }
      updateCursorStats(el, activity);
    }
  }

  function finalizeAgentMessage(el, text, { error = false, activity = null } = {}) {
    if (!el) return;
    const cardsHtml = el.querySelector(".cursor-file-cards")?.innerHTML || "";
    const statsText = el.querySelector(".cursor-stats")?.textContent || "";
    const explored = activity?.exploredFiles || 0;
    const edited = activity?.editedFiles || 0;
    clearThinkingState(el);
    el.classList.remove("live", "thinking", "cursor-mode");
    const body = String(text || "").trim() || "Execução concluída.";
    const workbench =
      cardsHtml.trim() && !cardsHtml.includes("cursor-empty-note")
        ? `<div class="cursor-workbench is-done">
            <div class="cursor-status-strip">
              <strong class="cursor-status-title">${error ? "Falhou" : "Concluído"}</strong>
              <span class="cursor-stats">${escapeHtml(statsText || `Explored ${explored} · Edited ${edited}`)}</span>
            </div>
            <div class="cursor-file-cards">${cardsHtml}</div>
          </div>`
        : "";
    el.innerHTML = `${workbench}<div class="agent-final-report">${renderMarkdown(body)}</div>`;
    el.classList.toggle("error", !!error || /^Erro/i.test(body));
  }

  function addMessage(text, role, scroll = true) {
    const el = document.createElement("div");
    el.className = "msg " + role + (role === "agent" && /^Erro/i.test(text) ? " error" : "");
    if (/\blive\b/.test(role) && !String(text || "").trim()) {
      // Cursor-style empty workbench instead of a vague "pensando..."
      ensureCursorWorkbench(el, null);
      const title = el.querySelector(".cursor-status-title");
      if (title) title.textContent = "Iniciando agente…";
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
      exploredFiles: 0,
      editedFiles: 0,
      linesAdded: 0,
      linesRemoved: 0,
      seenPaths: new Set(),
      workbenchEl: null,
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
    if (activity?.finished || /conclu|finaliz|pronto/.test(stage)) return { cls: "ok", label: "pronto", phaseId: "done" };
    if (/erro|falha|ollama/.test(stage)) return { cls: "err", label: "precisa de atenção", phaseId: activity?.phaseId || "work" };
    if (/cancel/.test(stage)) return { cls: "warn", label: "cancelando", phaseId: "done" };
    if (/plano|planej|criando plano|estratégia/.test(stage)) return { cls: "think", label: "entendendo o pedido", phaseId: "plan" };
    if (/modelo|decidindo|gerando|pensando/.test(stage)) return { cls: "think", label: "pensando na próxima edição", phaseId: "think" };
    if (/lendo|leitura/.test(stage)) return { cls: "work", label: "lendo arquivos", phaseId: "work" };
    if (/edit|escrev|arquivo|ferrament/.test(stage)) return { cls: "work", label: "editando o projeto", phaseId: "work" };
    if (/valid|avaliando|reflet|chec/.test(stage)) return { cls: "check", label: "conferindo o resultado", phaseId: "check" };
    if (/iniciado|prepar|trocando/.test(stage)) return { cls: "work", label: "preparando", phaseId: "prepare" };
    return { cls: "work", label: "trabalhando no projeto", phaseId: activity?.phaseId || "work" };
  }

  function humanToolLabel(name) {
    const n = String(name || "").toLowerCase();
    if (/read|ler|list|glob|search/.test(n)) return "lendo arquivos";
    if (/write|edit|patch|create/.test(n)) return "editando arquivos";
    if (/run|shell|command|npm|test/.test(n)) return "rodando comando";
    return name || "ferramenta";
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
    syncWorkRail(activity);
  }

  const WORK_STEPS = ["plan", "work", "check", "done"];

  function mapPhaseToWorkStep(phaseId) {
    if (phaseId === "prepare" || phaseId === "plan" || phaseId === "think") return "plan";
    if (phaseId === "work") return "work";
    if (phaseId === "check") return "check";
    return "done";
  }

  function syncWorkRailVisibility() {
    if (!els.workRail) return;
    const hasActivity = !!state.running || !!(state.runActivity && !state.runActivity.finished);
    const show =
      state.surfaceMode === "work" &&
      !!state.current &&
      hasActivity &&
      !isMobileLayout();
    els.workRail.classList.toggle("hidden", !show);
    els.workRail?.classList.toggle("is-idle", !hasActivity);
    syncWorkRailSplitter();
  }

  function syncWorkRail(activity) {
    if (!els.workStepper) return;
    syncWorkRailVisibility();
    const phase = activityPhaseMeta(activity || state.runActivity || {});
    const step = mapPhaseToWorkStep(phase.phaseId);
    const idx = WORK_STEPS.indexOf(step);
    els.workStepper.querySelectorAll(".work-step").forEach((el) => {
      const id = el.dataset.step;
      const pos = WORK_STEPS.indexOf(id);
      el.classList.remove("is-active", "is-done");
      if (activity?.finished || phase.phaseId === "done") {
        el.classList.add("is-done");
      } else if (pos < idx) el.classList.add("is-done");
      else if (pos === idx) el.classList.add("is-active");
    });
    if (els.workPlanMeta) {
      els.workPlanMeta.textContent = activity?.finished
        ? "Concluído"
        : activity
          ? phase.label
          : "Aguardando execução";
    }
    if (activity?.planTasks && els.workPlanList) {
      renderWorkPlan(activity.planTasks, activity);
    }
  }

  function renderWorkPlan(tasks, activity) {
    if (!els.workPlanList) return;
    const list = Array.isArray(tasks) ? tasks : [];
    if (!list.length) {
      els.workPlanList.innerHTML = "<li class='muted'>Sem tarefas no plano.</li>";
      return;
    }
    const currentId = activity?.currentTaskId || "";
    els.workPlanList.innerHTML = list
      .slice(0, 6)
      .map((t) => {
        const id = t.id || "";
        const title = t.title || t.id || "Tarefa";
        let cls = "";
        let mark = "○";
        if (activity?.finished) {
          cls = "is-done";
          mark = "✓";
        } else if (id && id === currentId) {
          cls = "is-active";
          mark = "●";
        } else if (t.status === "done" || t.status === "completed") {
          cls = "is-done";
          mark = "✓";
        }
        return `<li class="${cls}"><span>${mark}</span><span>${escapeHtml(title)}</span></li>`;
      })
      .join("");
  }

  function updateProjectChanges(paths, kind = "changed") {
    if (!els.projectChanges || !els.projectChangesList) return;
    if (!state.projectChangeMap) state.projectChangeMap = {};
    (paths || []).forEach((p) => {
      const key = String(p || "").replace(/\\/g, "/");
      if (!key) return;
      state.projectChangeMap[key] = kind;
    });
    const entries = Object.entries(state.projectChangeMap).slice(-12);
    if (!entries.length) {
      els.projectChanges.classList.add("hidden");
      return;
    }
    els.projectChanges.classList.remove("hidden");
    if (els.projectChangesMeta) els.projectChangesMeta.textContent = `${entries.length} arquivo(s)`;
    els.projectChangesList.innerHTML = entries
      .map(([path]) => {
        const name = path.split("/").pop() || path;
        return `<li><span>${escapeHtml(name)}</span><span class="chg-add">+</span></li>`;
      })
      .join("");
  }

  function updateSidebarResources(payload) {
    if (!els.sidebarResources) return;
    // Live meters must use detected machine stats, not the manual "Meu PC" profile.
    const hw = payload?.detected || payload?.hardware || payload || {};
    const ramTotal = Number(hw.ram_total_gb ?? 0);
    const ramAvail = Number(hw.ram_available_gb ?? ramTotal);
    const ramUsed = Number(
      hw.ram_used_gb != null ? hw.ram_used_gb : ramTotal > 0 ? Math.max(0, ramTotal - ramAvail) : 0
    );
    const ramPct = Number(
      hw.ram_percent != null
        ? hw.ram_percent
        : ramTotal > 0
          ? (ramUsed / ramTotal) * 100
          : 0
    );
    const vramTotal = Number(hw.vram_total_gb ?? 0);
    const vramFree = Number(hw.vram_free_gb ?? vramTotal);
    const vramUsed = Number(
      hw.vram_used_gb != null ? hw.vram_used_gb : vramTotal > 0 ? Math.max(0, vramTotal - vramFree) : 0
    );
    const vramPct = Number(
      hw.vram_percent != null
        ? hw.vram_percent
        : vramTotal > 0
          ? (vramUsed / vramTotal) * 100
          : 0
    );
    const cores = Number(hw.cpu_cores ?? 0);
    const cpuPct =
      hw.cpu_percent != null && Number.isFinite(Number(hw.cpu_percent))
        ? Number(hw.cpu_percent)
        : null;
    const gpuUtil =
      hw.gpu_utilization_percent != null && Number.isFinite(Number(hw.gpu_utilization_percent))
        ? Number(hw.gpu_utilization_percent)
        : null;
    const gpuFill = gpuUtil != null ? gpuUtil : vramPct;

    if (els.resCpuFill) els.resCpuFill.style.width = `${Math.min(100, Math.max(0, cpuPct ?? 0))}%`;
    if (els.resCpuLabel) {
      if (cpuPct != null && cores) els.resCpuLabel.textContent = `${Math.round(cpuPct)}% · ${cores}c`;
      else if (cpuPct != null) els.resCpuLabel.textContent = `${Math.round(cpuPct)}%`;
      else if (cores) els.resCpuLabel.textContent = `${cores}c`;
      else els.resCpuLabel.textContent = "—";
    }
    if (els.resRamFill) els.resRamFill.style.width = `${Math.min(100, Math.max(0, ramPct))}%`;
    if (els.resRamLabel) {
      els.resRamLabel.textContent = ramTotal
        ? `${ramUsed.toFixed(1)}/${ramTotal.toFixed(1)}`
        : "—";
    }
    if (els.resGpuFill) els.resGpuFill.style.width = `${Math.min(100, Math.max(0, gpuFill))}%`;
    if (els.resGpuLabel) {
      if (vramTotal > 0) {
        els.resGpuLabel.textContent =
          gpuUtil != null
            ? `${Math.round(gpuUtil)}% · ${vramUsed.toFixed(1)}/${vramTotal.toFixed(1)}`
            : `${vramUsed.toFixed(1)}/${vramTotal.toFixed(1)}`;
      } else if (hw.has_gpu) {
        els.resGpuLabel.textContent = gpuUtil != null ? `${Math.round(gpuUtil)}%` : "GPU";
      } else {
        els.resGpuLabel.textContent = "CPU";
      }
    }
    if (els.sidebarResourceHint) {
      const gpuName = Array.isArray(hw.gpus) && hw.gpus[0]?.name ? hw.gpus[0].name : "";
      const host = hw.hostname ? String(hw.hostname) : "";
      const src = hw.source === "container" ? "container" : hw.source === "wsl" ? "WSL" : "";
      const bits = [gpuName || (hw.has_gpu ? "GPU" : "CPU"), host, src].filter(Boolean);
      els.sidebarResourceHint.textContent = bits.slice(0, 2).join(" · ") || "Ollama";
    }
  }

  async function refreshSidebarResources() {
    try {
      // Always refresh so RAM/CPU meters stay live (server cache is short).
      const data = await api("/api/system/hardware?refresh=1");
      updateSidebarResources(data);
    } catch {
      try {
        const data = await api("/api/hardware?refresh=1");
        updateSidebarResources(data);
      } catch {
        /* optional widget */
      }
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
    const usedModel = donePayload?.model || activity.model || state.activeModel;
    updateActivity(activity, {
      finished: true,
      phaseId: "done",
      stage: cancelled ? "Execução cancelada" : "Execução concluída",
      detail: cancelled
        ? "Parou a pedido. Nada mais será editado."
        : changed.length
          ? `Pronto · ${changed.slice(0, 3).join(", ")}${changed.length > 3 ? "…" : ""}${usedModel ? ` · ${usedModel}` : ""}`
          : `Pronto.${usedModel ? ` · ${usedModel}` : ""}`,
      step: activity.maxSteps || activity.step,
      model: usedModel || activity.model,
    });
    renderRunActivity(progressEl, activity);
    updateActiveModelDisplay(usedModel || expectedAutoModel(), {
      source: isAutoModelSelected() ? "auto" : "manual",
      live: false,
    });
  }

  async function cancelRun() {
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
    state.running = false;
    hideBusyBanner();
    syncRunChrome();
    syncWorkRail(null);
    showToast("Execução cancelada — fila liberada.", "info");
  }

  async function sendPrompt() {
    let prompt = els.promptInput.value.trim();
    if (/^voltar\s+ao\s+chat\.?$/i.test(prompt)) {
      setSurfaceMode("chat");
      if (els.modeSelect) els.modeSelect.value = "chat";
      syncModeControls();
      els.promptInput.value = "";
      addMessage("Voltei para Chat.", "system");
      return;
    }
    if ((!prompt && !state.attachments.length) || state.running) return;

    if (!state.current) {
      showToast("Crie ou escolha um projeto para continuar.", "info", 4500);
      openNewProjectModal(state.selectedTemplate || (state.surfaceMode === "work" ? "landing" : "blank"));
      return;
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
        // Auto handoff: build intents go to Work immediately (less friction).
        if (els.modeSelect) els.modeSelect.value = "execute";
        syncModeControls();
        if (state.surfaceMode !== "work") setSurfaceMode("work");
        addMessage(
          "Pedido de construção detectado — executei no Work. Se era só conversa, diga “voltar ao chat”.",
          "system"
        );
        return sendAgentPrompt(enrichedPrompt, "execute", { displayPrompt: prompt, model: selectedModel });
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
    if (/^m?implemente(\s+(vc|voc[eê]|as|isso|essas?))?/i.test(t)) return true;
    if (/implemente\s+vc\s+as\s+melhorias/i.test(t)) return true;
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
    const miniApp =
      /\b(calculadora|calculator|contador|counter|todo|to-?do|cron[oô]metro|timer|conversor|quiz)\b/.test(t);
    const plain =
      !/\b(react|vite|fastapi|flask|django)\b/.test(t) &&
      ((/\bhtml\b/.test(t) && /\b(css|javascript|\bjs\b)\b/.test(t)) ||
        /\b(html|css|javascript|site|p[aá]gina|landing|aplicat|app)\b/.test(t) ||
        miniApp) &&
      /\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?|pequena|simples|mini|melhor(e|ar)|adicion|alter|edit|quero)\b/.test(t);
    return react || api || plain;
  }

  function looksLikeStrongCreateIntent(text) {
    const t = String(text || "").toLowerCase().trim();
    if (t.length < 12) return false;
    return (
      /\b(cri(e|ar)|faz(er)?|mont(e|ar)|gera(r)?|quero)\b/.test(t) &&
      /\b(app|aplicat|site|landing|dashboard|api|react|html|p[aá]gina|calculadora|calculator|contador|todo)\b/.test(t)
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
      /\b(cri(e|ar)|faz(er)?|implement(e|ar)?|adicion(e|ar)?|alter(e|ar)?|edit(e|ar)?|corrig(a|ir)?|refator(e|ar)?|melhor(e|ar)|redesenh(e|ar)?|build|gera(r)?|escrev(a|er)|mont(e|ar)|atualiz(e|ar)|aplique|aplica|quero)\b/i.test(
        t
      );
    const hasTarget =
      /\b(landing|website|site|app|aplicativ|html|css|react|vite|api|arquivo|c[oó]digo|componente|p[aá]gina|endpoint|fun[cç][aã]o|layout|ui|ux|dashboard|backend|frontend|visual|estilo|navbar|hero|formul[aá]rio|melhorias?|sugest\w*|mudan[cç]\w*|altera[cç]\w*|projeto|calculadora|calculator|contador|todo|to-?do)\b/i.test(
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
      setSurfaceMode("work");
      if (els.modeSelect) els.modeSelect.value = "execute";
      syncModeControls();
      if (state.current) {
        showWorkspace();
        switchToolGroup("app", "preview");
      }
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
    state.running = true;
    state.runId = null;
    state.abortController = new AbortController();
    showBusyBanner({ goal: String(prompt).slice(0, 80), started_at: Date.now() / 1000 });
    if (els.busyBannerTitle) els.busyBannerTitle.textContent = "Chat";
    syncRunChrome({ chip: "Chat…" });

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
            if (ev.model) {
              updateActiveModelDisplay(ev.model, {
                source: modelForRequest ? "manual" : "auto",
                live: true,
              });
            }
            const modelLabel = ev.model
              ? modelForRequest
                ? ev.model
                : `Auto → ${ev.model}`
              : "auto";
            statusEl.textContent = `Chat · ${modelLabel} · ${elapsed}s`;
          } else if (ev.type === "chat_chunk" && ev.text) {
            if (statusEl.isConnected) {
              const live = state.activeModel
                ? `${modelForRequest ? "" : "Auto → "}${state.activeModel}`
                : "modelo";
              statusEl.textContent = `Chat · ${live} · respondendo… ${elapsed}s`;
            }
            clearThinkingState(agentEl);
            fullText += ev.text;
            agentEl.textContent = fullText;
            els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
          } else if (ev.type === "chat_replace" && ev.text != null) {
            clearThinkingState(agentEl);
            fullText = String(ev.text || "");
            setMessageContent(agentEl, fullText, "agent");
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
        showToast("Projeto ocupado — acompanhando ou use Cancelar e liberar.", "err", 6000);
        const busy = e.data || {};
        if (busy.run_id && state.surfaceMode === "work") {
          state.running = false;
          window.clearInterval(waitTimer);
          await followBusyRun(busy, {
            systemNote:
              "Há uma execução ativa — acompanhando o progresso no Work. Use «Cancelar e liberar» se estiver travada.",
          });
          return;
        }
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
        if (isModelMemoryError(raw) && !opts.oomRetried) {
          const broken = modelNameFromError(raw);
          const fallback = banAndSwitchFromBrokenModel(broken, `Chat falhou em ${broken || "modelo grande"}`);
          state.running = false;
          window.clearInterval(waitTimer);
          removeMessage(agentEl);
          removeMessage(statusEl);
          return sendChatPrompt(prompt, { model: fallback || "", oomRetried: true });
        }
        if (isNetwork) {
          // Often Ollama/host ran out of free RAM mid-stream — not a "wrong URL".
          const live = expectedAutoModel() || state.activeModel || "o modelo atual";
          agentEl.textContent =
            `Conexão interrompida durante o chat (comum com pouca memória livre). ` +
            `Confirme Auto → ${live}, feche outros apps pesados e tente de novo. ` +
            `Se continuar, reinicie a plataforma.`;
          showToast("Chat interrompido — tente de novo com Auto no modelo instalado.", "err", 7000);
        } else if (/404|n[aã]o encontrado|model.*not found/i.test(raw)) {
          agentEl.textContent =
            "Modelo indisponível no Ollama. Mude para Auto (recomendado) ou outro modelo instalado e tente de novo.";
        } else {
          agentEl.textContent = "Erro: " + raw;
        }
        agentEl.classList.add("error");
        await persistMessage("agent", agentEl.textContent).catch(() => {});
      }
    } finally {
      window.clearInterval(waitTimer);
      state.running = false;
      state.runId = null;
      state.abortController = null;
      hideBusyBanner();
      syncRunChrome();
      updateActiveModelDisplay(state.activeModel || expectedAutoModel(), {
        source: isAutoModelSelected() ? "auto" : "manual",
        live: false,
      });
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
    state.running = true;
    state.runId = null;
    state.abortController = new AbortController();
    state.llmPreviewChars = 0;
    showBusyBanner({ goal: String(displayPrompt).slice(0, 80), started_at: Date.now() / 1000 });
    if (els.busyBannerTitle) els.busyBannerTitle.textContent = "Work";
    syncRunChrome({ chip: "Work…" });
    if (els.btnCancel) els.btnCancel.disabled = false;

    const progressEl = addMessage("", "progress");
    const activity = createRunActivity(displayPrompt);
    startActivityTimer(progressEl, activity);
    syncWorkRail(activity);
    const agentEl = addMessage("", "agent live");
    setWorkingState(agentEl, "Iniciando agente…", "Como no Cursor: leituras e diffs aparecem aqui", activity);
    let wasAbort = false;
    let followBusy = null;
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

      if (donePayload) {
        const fullReport = donePayload.report || "(sem relatório)";
        const chatSummary = donePayload.summary || fullReport;
        finalizeAgentMessage(agentEl, chatSummary, {
          activity,
          error: donePayload.status === "CANCELLED" || /^FAIL|FAILED|Erro/i.test(String(donePayload.status || "")),
        });
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
        window.setTimeout(() => removeMessage(progressEl), 6500);
      } else if (streamError) {
        const err = new Error(String(streamError));
        err.streamError = true;
        throw err;
      } else {
        // Stream closed without done — often the UI dropped while the agent still runs.
        const stillActive = await checkActiveRunStillAlive();
        if (stillActive?.run_id) {
          stopActivityTimer(activity);
          removeMessage(progressEl);
          finalizeAgentMessage(
            agentEl,
            "Conexão do stream caiu — acompanhando a execução pelo status do servidor…",
            { activity }
          );
          followBusy = stillActive;
        } else {
          // Retry once with a fitting smaller model for create/scaffold goals.
          const createLike =
            looksLikeOfflineScaffoldGoal(displayPrompt) ||
            looksLikeStrongCreateIntent(displayPrompt) ||
            looksLikeCodeRequest(displayPrompt);
          if (createLike && !opts.noReportRetried && mode !== "plan") {
            const broken = modelForRequest || resolveModelForRequest();
            const fallback = banAndSwitchFromBrokenModel(broken, "Execução interrompida sem relatório");
            state.running = false;
            removeMessage(agentEl);
            removeMessage(progressEl);
            addMessage(
              fallback
                ? `Execução interrompida sem relatório — repetindo com <strong>${escapeHtml(fallback)}</strong> (scaffold se o modelo falhar).`
                : "Execução interrompida sem relatório — repetindo com Auto / scaffold determinístico…",
              "system"
            );
            return sendAgentPrompt(prompt, mode, {
              displayPrompt,
              model: fallback,
              noReportRetried: true,
              oomRetried: true,
            });
          }
          finalizeAgentMessage(agentEl, "Execução finalizada sem relatório.", { error: true, activity });
          window.setTimeout(() => removeMessage(progressEl), 2500);
        }
      }
    } catch (e) {
      stopActivityTimer(activity);
      removeMessage(progressEl);
      clearThinkingState(agentEl);
      agentEl.classList.remove("live", "thinking", "cursor-mode");
      if (e.status === 409 || e.data?.busy) {
        followBusy = e.data || {};
        showBusyBanner(followBusy);
        finalizeAgentMessage(agentEl, e.message || "Agente já em execução neste projeto.", {
          error: true,
          activity,
        });
        if (!followBusy.run_id && state.current?.id) {
          const alive = await checkActiveRunStillAlive();
          if (alive?.run_id) followBusy = alive;
        }
      } else if (e.name === "AbortError") {
        wasAbort = true;
        finalizeAgentMessage(agentEl, "Cancelando...", { error: true, activity });
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
        finalizeAgentMessage(agentEl, "Erro: " + err, { error: true, activity });
        openModelsModal();
      } else {
        const raw = String(e.message || "erro desconhecido");
        const isOom =
          /insufficient memory|n[aã]o cabe na mem[oó]ria|mem[oó]ria insuficiente|failed to allocate|out of memory|http error 500/i.test(
            raw
          );
        if (isOom && !opts.oomRetried) {
          const broken = modelNameFromError(raw) || modelForRequest;
          const fallback = banAndSwitchFromBrokenModel(broken, "Modelo sem memória suficiente");
          if (fallback && fallback !== modelForRequest) {
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
        finalizeAgentMessage(agentEl, err, { error: true, activity });
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
      state.abortController = null;
      state.llmPreviewChars = 0;
      if (followBusy?.run_id) {
        state.running = true;
        showBusyBanner({ ...followBusy, reconnect: true });
        syncRunChrome({ chip: "Acompanhando…" });
      } else {
        state.running = false;
        state.runId = null;
        hideBusyBanner();
        syncRunChrome();
        syncWorkRail(null);
      }
      syncModeControls();
      if (wasAbort) {
        await new Promise((r) => setTimeout(r, 400));
        await loadChat().catch(() => {});
      }
      els.promptInput.focus();
    }
    if (followBusy?.run_id) {
      await followBusyRun(followBusy, {
        systemNote:
          "Há uma execução ativa neste projeto — acompanhando o progresso. Use «Liberar fila» se estiver travada.",
      });
    }
  }

  function handleStreamEvent(ev, progressEl, agentEl, activity) {
    switch (ev.type) {
      case "started":
        if (ev.run_id) {
          state.runId = ev.run_id;
          if (els.btnCancel) els.btnCancel.disabled = false;
        }
        if (ev.model) {
          activity.model = ev.model;
          updateActiveModelDisplay(ev.model, {
            source: ev.model_mode === "manual" ? "manual" : "auto",
            live: true,
          });
          addActivityEvent(
            activity,
            "Modelo",
            ev.model_mode === "auto" || isAutoModelSelected()
              ? `Auto escolheu ${ev.model}`
              : `Usando ${ev.model}`
          );
        }
        updateActivity(activity, {
          runId: ev.run_id || activity.runId,
          phaseId: "prepare",
          stage: "Preparando o projeto",
          detail: ev.model
            ? `Usando ${ev.model}${ev.model_mode === "auto" ? " (Auto)" : ""} — abrindo o contexto do projeto.`
            : "Abrindo o contexto do projeto e da conversa.",
          model: ev.model || activity.model,
        });
        setWorkingState(
          agentEl,
          "Preparando o projeto",
          ev.model
            ? `${ev.model_mode === "auto" ? "Auto → " : ""}${ev.model}`
            : "Lendo o que já existe…",
          activity
        );
        break;
      case "cancelled":
        updateActivity(activity, {
          phaseId: "done",
          stage: "Cancelando",
          detail: "Pedido de cancelamento enviado. Aguardando o agente parar no próximo ponto seguro.",
        });
        setWorkingState(agentEl, "Cancelando…", "Parando no próximo ponto seguro", activity);
        break;
      case "model_fallback": {
        const fromModel = ev.from_model || "modelo grande";
        const toModel = ev.to_model || "modelo menor";
        const wasAuto = isAutoModelSelected();
        updateActivity(activity, {
          phaseId: "prepare",
          stage: "Trocando modelo",
          detail: `${fromModel} sem memória → usando ${toModel}`,
          model: toModel,
        });
        setWorkingState(
          agentEl,
          `Trocando para ${toModel}`,
          `${fromModel} falhou por memória no Ollama`,
          activity
        );
        showToast(
          `Modelo <strong>${escapeHtml(fromModel)}</strong> sem memória — continuando com <strong>${escapeHtml(toModel)}</strong>.`,
          "info",
          7000
        );
        if (toModel) {
          // Keep Auto selected when the user chose Auto; only show the live model.
          if (!wasAuto) {
            setModelSelection(toModel);
            rememberModelPreference(toModel);
          } else {
            rememberModelPreference(null);
            setModelSelection(null);
          }
          updateActiveModelDisplay(toModel, { source: wasAuto ? "auto" : "manual", live: true });
        }
        break;
      }
      case "planning":
        updateActivity(activity, {
          phaseId: "plan",
          stage: "Entendendo o pedido",
          detail: ev.message || "Analisando o projeto para decidir o que mudar.",
        });
        setWorkingState(agentEl, "Entendendo o pedido", "Analisando arquivos do projeto…", activity);
        break;
      case "plan":
        updateActivity(activity, {
          phaseId: "plan",
          stage: "Plano pronto",
          detail: `Vai fazer ${ev.task_count || "algumas"} etapa(s) no projeto.`,
          planSummary: ev.summary || "Plano criado",
          taskCount: ev.task_count || null,
          planTasks: Array.isArray(ev.tasks) ? ev.tasks : activity.planTasks || [],
        });
        setWorkingState(
          agentEl,
          "Plano pronto — começando a editar",
          `${ev.task_count || "?"} etapa(s)`,
          activity
        );
        break;
      case "step":
        updateActivity(activity, {
          phaseId: "think",
          stage: "Editando o projeto",
          detail: `${ev.step}/${ev.max_steps}: ${ev.task_title || ev.task_id || "próxima mudança"}`,
          step: ev.step || activity.step,
          currentTaskId: ev.task_id || activity.currentTaskId,
          maxSteps: ev.max_steps || activity.maxSteps,
          task: ev.task_title || ev.task_id || "",
          tools: [],
          okTools: 0,
          toolCount: 0,
          reflection: "",
        });
        setWorkingState(
          agentEl,
          ev.task_title || "Editando o projeto",
          `Etapa ${ev.step}/${ev.max_steps}`,
          activity
        );
        break;
      case "llm_chunk":
        updateActivity(activity, {
          phaseId: "think",
          stage: "Pensando na próxima edição",
          detail: "Escolhendo o próximo arquivo para ler ou alterar…",
          llmChars: (activity.llmChars || 0) + (ev.text ? ev.text.length : 0),
        });
        if (!activity.liveOp) {
          setWorkingState(
            agentEl,
            "Pensando na próxima edição",
            activity.task || "em andamento",
            activity
          );
        }
        break;
      case "file_op": {
        updateLiveCodeViewer(ev, activity);
        upsertCursorFileCard(agentEl, ev, activity);
        const verb = liveOpLabel(ev.op, ev.status);
        updateActivity(activity, {
          phaseId: "work",
          stage: ev.headline || `${verb} código`,
          detail: ev.path
            ? `${verb}: ${ev.path}${ev.error ? ` — ${ev.error}` : ""}`
            : ev.headline || "Operação em arquivo",
        });
        if (ev.path && (ev.op === "write" || ev.op === "edit" || ev.op === "patch") && ev.status === "done") {
          markChangedFiles([ev.path]);
          scheduleFileRefresh(activity);
          if (isUiPath(ev.path)) {
            window.setTimeout(() => {
              if (state.surfaceMode === "work") switchToolGroup("app", "preview");
              updatePreview(/\.(html?)$/i.test(ev.path) ? ev.path : findPreviewPath());
            }, 500);
          }
        }
        break;
      }
      case "tools_start": {
        const labels = (ev.tools || []).slice(0, 3).map(humanToolLabel);
        updateActivity(activity, {
          phaseId: "work",
          stage: labels[0] || "Trabalhando nos arquivos",
          detail: labels.length > 1 ? labels.join(" · ") : "Atualizando o projeto…",
          tools: ev.tools || [],
          toolCount: ev.count || 0,
          okTools: 0,
        });
        setWorkingState(
          agentEl,
          labels[0] || "Trabalhando nos arquivos",
          "As mudanças aparecem abaixo conforme terminam",
          activity
        );
        break;
      }
      case "tools":
        updateActivity(activity, {
          phaseId: "work",
          stage: "Mudanças aplicadas",
          detail: `${ev.ok || 0}/${ev.count || 0} operações concluídas.`,
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
          stage: paths.length === 1 ? "Arquivo atualizado" : "Arquivos atualizados",
          detail: paths.length
            ? paths.slice(0, 4).join(", ") + (paths.length > 4 ? "…" : "")
            : "O projeto foi atualizado.",
          files: unique,
        });
        scheduleFileRefresh(activity);
        if (paths.some(isUiPath)) {
          window.setTimeout(() => {
            switchToolGroup("app", "preview");
            updatePreview(paths.find((p) => /\.html?$/i.test(p)) || findPreviewPath());
          }, 500);
        }
        break;
      }
      case "validation_start":
        updateActivity(activity, {
          phaseId: "check",
          stage: "Conferindo o resultado",
          detail: `Checando: ${(ev.commands || []).slice(0, 2).join(", ") || "o que mudou"}.`,
        });
        setWorkingState(
          agentEl,
          "Conferindo o resultado",
          (ev.commands || []).slice(0, 2).join(", ") || "checagens",
          activity
        );
        break;
      case "validation":
        updateActivity(activity, {
          phaseId: "check",
          stage: "Conferência concluída",
          detail: `${ev.ok || 0}/${ev.count || 0} checagens ok.`,
          reflection: ev.summary || activity.reflection,
        });
        setWorkingState(
          agentEl,
          "Conferência concluída",
          `${ev.ok || 0}/${ev.count || 0} ok`,
          activity
        );
        break;
      case "reflection":
        updateActivity(activity, {
          phaseId: "check",
          stage: "Avaliando se ficou bom",
          detail: ev.status === "done" || ev.status === "success" ? "Parece suficiente." : "Pode precisar de mais um ajuste.",
          reflection: (ev.analysis || "").slice(0, 180),
        });
        setWorkingState(agentEl, "Avaliando se ficou bom", "", activity);
        break;
      case "error": {
        const errMsg = ev.message || ev.error || "Erro desconhecido durante a execução.";
        updateActivity(activity, {
          stage: /ollama|modelo|memory|memória/i.test(errMsg) ? "Problema com o modelo" : "Erro encontrado",
          detail: errMsg,
        });
        setWorkingState(agentEl, "Algo falhou", errMsg, activity);
        if (/ollama|offline|connection refused|econnrefused/i.test(errMsg)) {
          showToast("Ollama ficou offline no meio da execução. Abra Modelos para reconectar.", "err", 7000);
          updateOllamaOfflineUI();
        }
        break;
      }
      default:
        break;
    }
    renderRunActivity(progressEl, activity);
  }

  // ── Files ──

  function fileKind(name) {
    if (/\.html?$/i.test(name)) return { label: "HTML", cls: "html" };
    if (/\.(css|scss)$/i.test(name)) return { label: "#", cls: "css" };
    if (/\.(js|mjs|cjs)$/i.test(name)) return { label: "JS", cls: "js" };
    if (/\.(ts|tsx|jsx)$/i.test(name)) return { label: "TS", cls: "ts" };
    if (/\.py$/i.test(name)) return { label: "PY", cls: "py" };
    if (/favicon\.ico$/i.test(name)) return { label: "★", cls: "ico" };
    if (/\.json$/i.test(name)) return { label: "{}", cls: "json" };
    if (/\.md$/i.test(name)) return { label: "MD", cls: "md" };
    return { label: "FILE", cls: "file" };
  }

  function markChangedFiles(paths) {
    const clean = (paths || []).map((p) => String(p || "").replace(/\\/g, "/")).filter(Boolean);
    state.recentChangedFiles = Array.from(new Set([...(state.recentChangedFiles || []), ...clean])).slice(-24);
    updateProjectChanges(clean, "changed");
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
      li.dataset.depth = String(depth);
      li.style.setProperty("--file-depth", String(depth));
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
        li.className = "file-node";
        li.dataset.path = f.path;
        li.dataset.depth = String(depth);
        li.style.setProperty("--file-depth", String(depth));
        if (state.selectedFile === f.path) li.classList.add("selected");
        if (changed) li.classList.add("changed");
        li.innerHTML = `
          <span class="file-kind file-kind--${kind.cls}">${kind.label}</span>
          <span class="file-path">${escapeHtml(f.name)}</span>
          ${changed ? '<span class="file-changed">M</span>' : ""}`;
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
          ${changed ? '<span class="file-changed">M</span>' : ""}`;
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
            ${changed ? '<span class="file-changed">M</span>' : ""}`;
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
    if (dirty) els.fileEditorSaved?.classList.add("hidden");
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
        els.fileEditorPath.textContent = asCopy ? savePath : path;
      }
      if (els.fileEditorSaved) {
        els.fileEditorSaved.textContent = asCopy ? "cópia salva" : "salvo";
        els.fileEditorSaved.classList.remove("hidden");
        window.setTimeout(() => els.fileEditorSaved?.classList.add("hidden"), 2200);
      }
      showToast(asCopy ? `Salvo como ${savePath}` : "Arquivo salvo.", "ok", 2200);
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
      const on = btn.dataset.device === device;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
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
          ? "Ainda sem UI estática. Inicie o preview ao vivo para abrir /docs, ou peça uma landing HTML."
          : "Ainda sem página pronta. Clique em Iniciar preview ao vivo (React/Vite) ou peça uma landing."
        : "Ainda sem UI — peça no Work: “cria uma landing page com index.html”.";
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
    const created = donePayload?.created_files || [];
    const htmlPath = changed.find((p) => /\.html?$/i.test(p));
    const uiTouched = !!(htmlPath || changed.some(isUiPath));
    const actions = [];
    const hasDev = !!state.devStatus?.has_dev_script;
    const devRunning = !!state.devStatus?.running;
    const hasMockupHint = !!(ensureMockupPath() || "").trim();
    const failed = status && status !== "SUCCESS" && status !== "CANCELLED";

    // Cap: 1 primary + 2 secondary (golden path).
    if (failed) {
      actions.push({
        action: "prompt",
        label: "Corrigir o erro",
        primary: true,
        prompt:
          "Corrija o erro da última execução neste projeto. Leia o relatório e os logs, identifique a causa e aplique a correção mínima necessária.",
      });
      if (changed.length) actions.push({ action: "files", label: "Ver arquivos" });
      if (uiTouched) actions.push({ action: "preview", label: "Ver preview" });
    } else if (uiTouched || hasDev) {
      if (uiTouched) actions.push({ action: "preview", label: "Ver preview", primary: true });
      else if (hasDev && !devRunning) {
        actions.push({ action: "start-dev", label: "Iniciar preview ao vivo", primary: true });
      }
      if (visualEngineAvailable()) {
        actions.push({
          action: hasMockupHint ? "reach-result" : "visual",
          label: hasMockupHint ? "Alcançar resultado" : "Enviar mockup",
        });
      }
      if (changed.length) actions.push({ action: "files", label: "Arquivos" });
    } else {
      if (changed[0]) actions.push({ action: "open-file", label: "Abrir arquivo", path: changed[0], primary: true });
      else actions.push({ action: "files", label: "Ver arquivos", primary: true });
      if (visualEngineAvailable() && hasMockupHint) {
        actions.push({ action: "reach-result", label: "Alcançar resultado" });
      }
    }
    const capped = actions.slice(0, 3);

    const createdN = created.length;
    const editedN = Math.max(0, changed.length - createdN);
    const summaryBits = [];
    if (createdN) summaryBits.push(`${createdN} criado(s)`);
    if (editedN) summaryBits.push(`${editedN} editado(s)`);
    const title =
      status === "CANCELLED"
        ? "Execução cancelada"
        : changed.length
          ? `Pronto · ${summaryBits.join(" · ") || `${changed.length} arquivo(s)`}`
          : "Pronto para o próximo passo";

    el.innerHTML = `
      <div class="next-steps-card">
        <div class="next-steps-title">${escapeHtml(title)}</div>
        ${changed.length ? `<div class="next-steps-files">${changed.slice(0, 5).map((p) => {
          const tag = created.includes(p) ? "novo" : "editado";
          return `<button type="button" class="next-file" data-path="${escapeHtml(p)}"><span>${escapeHtml(p)}</span><em>${tag}</em></button>`;
        }).join("")}</div>` : ""}
        <div class="next-steps-actions">
          ${capped
            .map(
              (item) =>
                `<button type="button" class="btn ${item.primary ? "btn-primary btn-gradient" : "btn-ghost"} btn-sm next-action" data-action="${item.action}" ${
                  item.path ? `data-path="${escapeHtml(item.path)}"` : ""
                } ${item.prompt ? `data-prompt="${escapeHtml(item.prompt)}"` : ""}>${escapeHtml(item.label)}</button>`
            )
            .join("")}
        </div>
      </div>`;

    el.addEventListener("click", async (event) => {
      const fileBtn = event.target.closest(".next-file");
      if (fileBtn?.dataset.path) {
        await openFile(fileBtn.dataset.path, {
          switchToFiles: !/\.html?$/i.test(fileBtn.dataset.path),
          preferPreview: /\.html?$/i.test(fileBtn.dataset.path),
        });
        return;
      }
      const btn = event.target.closest(".next-action");
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === "preview") {
        setSurfaceMode("work");
        switchToolGroup("app", "preview");
        updatePreview(htmlPath || findPreviewPath());
      } else if (action === "start-dev") {
        setSurfaceMode("work");
        state.previewMode = "dev";
        if (els.previewMode) els.previewMode.value = "dev";
        syncDevPolling();
        startDevServer();
      } else if (action === "deploy") {
        runDeploy();
      } else if (action === "files") {
        setSurfaceMode("work");
        switchToolGroup("app", "files");
      } else if (action === "visual") {
        if (hasMockupHint) {
          setSurfaceMode("work");
          switchToolGroup("visual", "compare");
          setCompareFlowStep("compare");
          runCompareNow({ smartFollowUp: true });
        } else {
          openVisualMockupFlow();
        }
      } else if (action === "reach-result") {
        setSurfaceMode("work");
        switchToolGroup("visual", "compare");
        startReachResultFlow({ autoCorrect: true });
      } else if (action === "open-file" && btn.dataset.path) {
        await openFile(btn.dataset.path, {
          switchToFiles: !/\.html?$/i.test(btn.dataset.path),
          preferPreview: /\.html?$/i.test(btn.dataset.path),
        });
      } else if (action === "prompt" && btn.dataset.prompt) {
        els.promptInput.value = btn.dataset.prompt;
        els.promptInput.focus();
      }
    });

    els.chatMessages.appendChild(el);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    return el;
  }

  function findProjectMockupPath() {
    const current = (els.compareMockupPath?.value || "").trim();
    if (current) return current;
    const files = state.files || [];
    const mock = files.find(
      (f) => /mockup|referencia|reference|design/i.test(f.path || f.name || "") && /\.(png|jpe?g|webp)$/i.test(f.path || "")
    );
    return mock?.path || "";
  }

  function ensureMockupPath() {
    const path = findProjectMockupPath();
    if (path && els.compareMockupPath && !(els.compareMockupPath.value || "").trim()) {
      els.compareMockupPath.value = path;
    }
    return (els.compareMockupPath?.value || "").trim() || path;
  }

  function reportSimilarity(report) {
    if (!report) return null;
    const val =
      report.similarity ??
      report.best_similarity ??
      report.current_similarity ??
      report.minSimilarity ??
      report.min_similarity;
    if (val == null) return null;
    const n = Number(val);
    return Number.isFinite(n) ? n : null;
  }

  function visualTargetReached(sim) {
    const target = Number(state.visualTargetSimilarity) || 0.92;
    return sim != null && sim >= target;
  }

  function buildVisualAgentBrief(report, job) {
    const sim = reportSimilarity(report) ?? reportSimilarity(job);
    const pct = sim == null ? "—" : `${(sim * 100).toFixed(1)}%`;
    const target = `${((Number(state.visualTargetSimilarity) || 0.92) * 100).toFixed(0)}%`;
    const mockup = ensureMockupPath() || "mockup";
    const regions = Array.isArray(report?.regions) ? report.regions : [];
    const layout =
      report?.layoutChanges ||
      report?.layout_changes ||
      report?.layoutDiff?.layoutChanges ||
      [];
    const regionLines = regions
      .slice(0, 8)
      .map((r) => {
        const el = r.probableElement || r.probable_element || {};
        const sel = el.selector || "elemento desconhecido";
        return `- Região ${r.id || "?"}: ${r.category || "diff"} / ${r.severity || "?"} → ${sel}${
          r.diagnosis ? ` (${r.diagnosis})` : ""
        }`;
      })
      .join("\n");
    const layoutLines = (Array.isArray(layout) ? layout : [])
      .slice(0, 8)
      .map((c) => {
        const d = c.delta || {};
        return `- ${c.selector || "?"}: Δx=${d.x || 0} Δy=${d.y || 0} Δw=${d.width || 0} Δh=${d.height || 0}`;
      })
      .join("\n");
    const base = job?.baseline_similarity;
    const best = job?.best_similarity;
    const loopLine =
      base != null && best != null
        ? `Loop CSS: ${(Number(base) * 100).toFixed(1)}% → ${(Number(best) * 100).toFixed(1)}% (${job.status || "done"}).`
        : "";

    return [
      `Ajuste a UI para ficar visualmente parecida com o mockup "${mockup}".`,
      `Similaridade atual: ${pct} (meta ~${target}). ${loopLine}`.trim(),
      "Use o preview e os arquivos CSS/HTML existentes. Preserve estrutura e conteúdo; foque em layout, tipografia, espaçamento e cores.",
      regionLines ? `Regiões com diferença:\n${regionLines}` : "Não há regiões correlacionadas — compare o mockup e o preview e corrija as áreas mais óbvias.",
      layoutLines ? `Deltas de layout:\n${layoutLines}` : "",
      "Aplique mudanças mínimas e mensuráveis. Ao terminar, mantenha a página responsiva.",
    ]
      .filter(Boolean)
      .join("\n\n");
  }

  function updateVisualPrimaryCta(report) {
    const sim = reportSimilarity(report);
    const reached = visualTargetReached(sim);
    const hasMockup = !!(ensureMockupPath() || "").trim();
    els.comparePrimaryCta?.classList.toggle("hidden", !report && !hasMockup);
    els.btnVisualAgentBrief?.classList.toggle("hidden", !report || reached);
    els.btnCorrectPrimary?.classList.toggle("hidden", !report || reached);
    // Alcançar = primary; Só corrigir CSS = secondary after a score exists.
    if (els.btnReachResult) {
      els.btnReachResult.classList.toggle("btn-primary", !reached);
      els.btnReachResult.classList.toggle("btn-ghost", !!reached);
      els.btnReachResult.textContent = reached ? "Revalidar" : "Alcançar resultado";
    }
    if (els.comparePrimaryHint) {
      if (!report && hasMockup) {
        els.comparePrimaryHint.textContent =
          "Mockup pronto. Alcançar resultado compara e corrige até a meta.";
      } else if (!report) {
        els.comparePrimaryHint.textContent =
          "Um clique: compara → corrige CSS → se ainda ficar longe, prepara o brief para o agente.";
      } else if (reached) {
        els.comparePrimaryHint.textContent = `Meta atingida (${(sim * 100).toFixed(1)}%). Pode aprovar baseline ou pedir refinamentos.`;
      } else {
        els.comparePrimaryHint.textContent = `Ainda em ${(sim * 100).toFixed(1)}%. Alcançar fecha o loop; Pedir ao agente usa o brief do compare.`;
      }
    }
    syncCompareEmptyState();
  }

  function addVisualOutcomeCard(report, job) {
    if (!els.chatMessages) return;
    const sim = reportSimilarity(report) ?? reportSimilarity(job);
    const pct = sim == null ? "—" : `${(sim * 100).toFixed(1)}%`;
    const reached = visualTargetReached(sim);
    const el = document.createElement("div");
    el.className = "msg system next-steps visual-outcome";
    const title = reached
      ? `Visual próximo do mockup · ${pct}`
      : `Visual ainda longe do mockup · ${pct}`;
    const actions = [];
    if (!reached) {
      actions.push({ action: "reach", label: "Alcançar resultado", primary: true });
      actions.push({ action: "agent", label: "Pedir ao agente" });
    } else {
      actions.push({ action: "preview", label: "Ver preview", primary: true });
      actions.push({ action: "compare", label: "Ver comparação" });
    }

    el.innerHTML = `
      <div class="next-steps-card visual-outcome-card">
        <div class="next-steps-title">${escapeHtml(title)}</div>
        <p class="muted visual-outcome-copy">${
          reached
            ? "O motor de comparação indica que o resultado está na meta."
            : "Alcançar resultado fecha o loop CSS; se estabilizar abaixo da meta, use o brief no agente."
        }</p>
        <div class="next-steps-actions">
          ${actions
            .map(
              (item) =>
                `<button type="button" class="btn ${item.primary ? "btn-primary btn-gradient" : "btn-ghost"} btn-sm visual-outcome-action" data-action="${item.action}">${escapeHtml(item.label)}</button>`
            )
            .join("")}
        </div>
      </div>`;

    el.addEventListener("click", (event) => {
      const btn = event.target.closest(".visual-outcome-action");
      if (!btn) return;
      const action = btn.dataset.action;
      if (action === "reach" || action === "correct") {
        setSurfaceMode("work");
        switchToolGroup("visual", "compare");
        startReachResultFlow({ autoCorrect: true });
      } else if (action === "agent") {
        fillVisualAgentBrief(report, job, { send: false });
      } else if (action === "compare") {
        setSurfaceMode("work");
        switchToolGroup("visual", "compare");
      } else if (action === "preview") {
        setSurfaceMode("work");
        switchToolGroup("app", "preview");
        updatePreview();
      }
    });

    els.chatMessages.appendChild(el);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
  }

  function fillVisualAgentBrief(report, job, { send = false } = {}) {
    const brief = buildVisualAgentBrief(report || state.lastCompareReport, job || state.correctionJob);
    if (!brief || !els.promptInput) return;
    els.promptInput.value = brief;
    els.promptInput.focus();
    showToast(send ? "Enviando brief visual ao agente…" : "Brief visual pronto no composer.", "info", 4500);
    if (send && !state.running) sendPrompt();
  }

  async function suggestVisualIfMockupPresent({ autoCompare = false, uiChanged = false } = {}) {
    if (!state.current?.id || !visualEngineAvailable()) return null;
    const mock = ensureMockupPath();
    if (!mock) return null;
    if (autoCompare && uiChanged && !state.running && !state.visualReachInFlight) {
      showToast(`Mockup ${mock} — comparando com o preview…`, "info", 4500);
      state.visualAutoCompare = true;
      try {
        await runCompareNow({ smartFollowUp: true, quiet: true });
      } finally {
        state.visualAutoCompare = false;
      }
      return mock;
    }
    if (!autoCompare) {
      showToast(`Mockup encontrado (${mock}). Use “Alcançar resultado” no Visual.`, "info", 5500);
    }
    return mock;
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
    const success = donePayload?.status === "SUCCESS";

    if (hasDev && (packageTouched || uiChanged) && !state.devStatus?.running && canStartDevPreview()) {
      await maybeEnableDevPreview({ preferDev: true, autoStart: true });
    } else if (hasDev) {
      await maybeEnableDevPreview({ preferDev: true, autoStart: false });
    }

    if (donePayload?.status === "CANCELLED") {
      switchToolGroup("agent", "report");
    } else if (hasDev || uiChanged || htmlChanged) {
      if (state.surfaceMode !== "work") setSurfaceMode("work");
      switchToolGroup("app", "preview");
      updatePreview(htmlChanged || findPreviewPath());
    } else if (changed[0]) {
      if (state.surfaceMode !== "work") setSurfaceMode("work");
      await openFile(changed[0], { switchToFiles: true, preferPreview: false });
    } else {
      switchToolGroup("agent", "report");
      updatePreview();
    }

    addNextStepActions(changed, donePayload);
    await suggestVisualIfMockupPresent({
      autoCompare: success && !!(uiChanged || htmlChanged),
      uiChanged: !!(uiChanged || htmlChanged),
    });
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
      els.devErrorPanel?.classList.add("hidden");
    } else if (runtime === "uvicorn" && s.python_available === false) {
      els.devStatus.textContent = "Instale Python para rodar FastAPI";
      els.devErrorPanel?.classList.add("hidden");
    } else if (runtime !== "uvicorn" && !s.npm_available) {
      els.devStatus.textContent = "Instale Node.js para dev server";
      els.devErrorPanel?.classList.add("hidden");
    } else if (s.last_error) {
      const firstLine = String(s.last_error).split(/\r?\n/).map((l) => l.trim()).find(Boolean) || "Falha no preview ao vivo";
      els.devStatus.textContent = firstLine.slice(0, 90);
      if (els.devErrorLog) els.devErrorLog.textContent = s.last_error;
      if (els.devErrorSummary) els.devErrorSummary.textContent = firstLine.slice(0, 160);
      els.devErrorPanel?.classList.remove("hidden");
    } else if (runtime === "uvicorn") {
      els.devStatus.textContent = "Pronto: uvicorn main:app";
      els.devErrorPanel?.classList.add("hidden");
    } else {
      els.devStatus.textContent = `Pronto: npm run ${s.script}`;
      els.devErrorPanel?.classList.add("hidden");
    }
    if (s.running || !s.last_error) {
      if (!s.last_error) els.devErrorPanel?.classList.add("hidden");
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
    els.devErrorPanel?.classList.add("hidden");
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
      switchToolGroup("app", "preview");
    } catch (e) {
      const errText = e.data?.stderr || e.message || "Falha ao iniciar preview";
      const firstLine = String(errText).split(/\r?\n/).map((l) => l.trim()).find(Boolean) || "Falha ao iniciar preview";
      els.devStatus.textContent = firstLine.slice(0, 90);
      if (els.devErrorLog) els.devErrorLog.textContent = errText;
      if (els.devErrorSummary) els.devErrorSummary.textContent = firstLine.slice(0, 160);
      els.devErrorPanel?.classList.remove("hidden");
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

  // ── Tabs / tool groups (App · Agente · Visual) ──

  const TOOL_GROUP_DEFAULT = { app: "preview", agent: "live", visual: "compare" };
  const TAB_TO_GROUP = {
    preview: "app",
    files: "app",
    live: "agent",
    report: "agent",
    compare: "visual",
  };

  function switchToolGroup(group, preferredTab) {
    const g = TOOL_GROUP_DEFAULT[group] ? group : "app";
    const tab = preferredTab && TAB_TO_GROUP[preferredTab] === g
      ? preferredTab
      : (state.lastToolTab?.[g] || TOOL_GROUP_DEFAULT[g]);
    document.querySelectorAll(".tools-group").forEach((btn) => {
      const on = btn.dataset.group === g;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".tools-subrow").forEach((row) => {
      row.classList.toggle("hidden", row.dataset.groupPanel !== g);
    });
    switchTab(tab, { group: g });
  }

  function switchTab(name, opts = {}) {
    const tab = TAB_TO_GROUP[name] ? name : "preview";
    const group = opts.group || TAB_TO_GROUP[tab] || "app";
    if (!state.lastToolTab) state.lastToolTab = {};
    state.lastToolTab[group] = tab;
    state.activeToolGroup = group;

    document.querySelectorAll(".tools-group").forEach((btn) => {
      const on = btn.dataset.group === group;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".tools-subrow").forEach((row) => {
      row.classList.toggle("hidden", row.dataset.groupPanel !== group);
    });
    document.querySelectorAll(".panel-tab").forEach((el) => {
      el.classList.toggle("active", el.dataset.tab === tab);
    });
    const isAppPreview = group === "app" && tab === "preview";
    const isAppFiles = group === "app" && tab === "files";
    $("panelLive")?.classList.toggle("hidden", tab !== "live");
    $("panelFiles")?.classList.toggle("hidden", !isAppPreview && !isAppFiles);
    $("panelPreview")?.classList.toggle("hidden", tab !== "preview" && tab !== "files");
    $("panelCompare")?.classList.toggle("hidden", tab !== "compare");
    $("panelReport")?.classList.toggle("hidden", tab !== "report");
    const workbench = $("appWorkbench");
    workbench?.classList.toggle("workbench-focus-files", isAppFiles);
    workbench?.classList.toggle("workbench-focus-preview", isAppPreview);
    els.btnSidebarSearch?.classList.toggle("is-active", isAppFiles);
    syncMobileTabs(tab, group);
    if (opts.fromMobile && isMobileLayout()) openMobilePanel();
    else if (!isMobileLayout()) closeMobilePanel();
    if (tab === "preview" || tab === "files") updatePreview();
    else stopPreviewPolling();
    if (tab === "compare") {
      refreshComparePanel();
      syncCompareEmptyState();
    }
  }

  function parseCompareViewport() {
    const raw = els.compareViewport?.value || "1366x768";
    const [w, h] = raw.split("x").map((n) => parseInt(n, 10));
    return { width: w || 1366, height: h || 768, deviceScaleFactor: 1 };
  }

  function selectedCompareSuite() {
    return (els.compareSuite?.value || "").trim();
  }

  function renderSuiteReport(suite) {
    if (!suite || !els.compareSuitePanel) return;
    state.lastSuiteReport = suite;
    els.compareSuitePanel.classList.remove("hidden");
    const minPct = suite.minSimilarity == null ? "—" : `${(Number(suite.minSimilarity) * 100).toFixed(1)}%`;
    const avgPct = suite.avgSimilarity == null ? "—" : `${(Number(suite.avgSimilarity) * 100).toFixed(1)}%`;
    const targetPct = `${(Number(suite.targetSimilarity || 0.95) * 100).toFixed(0)}%`;
    if (els.compareSuiteMeta) {
      els.compareSuiteMeta.textContent =
        `${suite.suiteName || suite.suiteId || "Suite"} · ${suite.status || "?"} · ` +
        `min ${minPct} · média ${avgPct} · meta ${targetPct} · ` +
        `${suite.passedCount ?? 0}/${(suite.viewports || []).length} ok`;
    }
    if (!els.compareSuiteList) return;
    const rows = suite.viewports || [];
    if (!rows.length) {
      els.compareSuiteList.innerHTML = "<li class='muted'>Sem viewports na suite.</li>";
      return;
    }
    els.compareSuiteList.innerHTML = rows
      .map((row) => {
        const vp = row.viewport || {};
        const name = escapeHtml(vp.name || vp.id || `${vp.width}×${vp.height}`);
        const sim = row.similarity == null ? "—" : `${(Number(row.similarity) * 100).toFixed(1)}%`;
        const ok = row.passed ? "pass" : "fail";
        const err = row.error ? ` · ${escapeHtml(row.error)}` : "";
        return `<li class="compare-suite-item compare-suite-${ok}" data-cid="${escapeHtml(row.comparison_id || row.comparisonId || "")}">
          <span class="compare-suite-vp">${name}</span>
          <span class="compare-suite-sim">${escapeHtml(sim)}</span>
          <span class="compare-suite-badge">${row.passed ? "ok" : "falhou"}</span>${err}
        </li>`;
      })
      .join("");
  }

  function artifactUrl(comparisonId, file) {
    if (!state.current?.id || !comparisonId) return "";
    return `/api/projects/${encodeURIComponent(state.current.id)}/visual/comparisons/${encodeURIComponent(comparisonId)}/${encodeURIComponent(file)}?t=${Date.now()}`;
  }

  function setCompareView(view) {
    state.compareView = view || "side";
    els.compareViewTabs?.querySelectorAll(".compare-view-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.view === state.compareView);
    });
    const gallery = els.compareGallery;
    const slider = els.compareSliderWrap;
    if (!gallery || !slider) return;
    const mode = state.compareView;
    gallery.classList.toggle("hidden", mode === "slider");
    slider.classList.toggle("hidden", mode !== "slider");
    gallery.querySelectorAll(".compare-fig").forEach((fig) => {
      const isDiff = fig.classList.contains("compare-fig-diff");
      const isOverlay = fig.classList.contains("compare-fig-overlay");
      if (mode === "side") fig.classList.toggle("hidden", isDiff || isOverlay);
      else if (mode === "diff") fig.classList.toggle("hidden", !isDiff);
      else if (mode === "overlay") fig.classList.toggle("hidden", !isOverlay);
      else fig.classList.add("hidden");
    });
    if (mode === "slider") syncCompareSlider();
  }

  function syncCompareSlider() {
    const wrap = els.compareSlider;
    const top = els.compareSliderTop;
    const front = els.compareSliderFront;
    const range = els.compareSliderRange;
    if (!wrap || !top || !front || !range) return;
    const v = Number(range.value || 50);
    top.style.width = `${v}%`;
    const full = wrap.clientWidth || 1;
    front.style.width = `${full}px`;
    front.style.height = "100%";
  }

  function renderCompareReport(report) {
    if (!report) return;
    state.lastCompareReport = report;
    const pct = report.similarity == null ? "—" : `${(Number(report.similarity) * 100).toFixed(1)}%`;
    const fit = report.normalization?.fit || report.raw?.normalization?.fit || "";
    if (els.compareScore) {
      els.compareScore.classList.remove("hidden");
      els.compareScore.innerHTML = `<strong>${escapeHtml(pct)}</strong> similar · ${escapeHtml(report.mode || "")} · ${escapeHtml(fit)} · ${escapeHtml(report.status || "")}`;
    }
    const id = report.comparisonId || report.comparison_id;
    const artifacts = report.artifacts || report.raw?.artifacts || {};
    const refFile = artifacts.referenceNormalized ? "reference-normalized.png" : "reference.png";
    const actFile = artifacts.actualNormalized ? "actual-normalized.png" : "actual.png";
    if (els.compareRefImg) els.compareRefImg.src = artifactUrl(id, refFile);
    if (els.compareActImg) els.compareActImg.src = artifactUrl(id, actFile);
    if (els.compareDiffImg) els.compareDiffImg.src = artifactUrl(id, "diff.png");
    if (els.compareOverlayImg) els.compareOverlayImg.src = artifactUrl(id, "overlay.png");
    if (els.compareSliderBack) els.compareSliderBack.src = artifactUrl(id, actFile);
    if (els.compareSliderFront) els.compareSliderFront.src = artifactUrl(id, refFile);
    if (els.compareStatus) {
      const warns = (report.warnings || []).slice(0, 2).join(" · ");
      els.compareStatus.textContent = warns || `Comparação ${id} pronta.`;
    }
    // Prefer regions from promoted fields or raw bridge payload.
    if (!report.regions?.length && report.raw?.regions) {
      report = { ...report, regions: report.raw.regions };
      state.lastCompareReport = report;
    }
    renderCompareRegions(report);
    setCompareView(state.compareView || "side");
    setCompareFlowStep("correct");
    updateVisualPrimaryCta(report);
    syncCompareEmptyState();
    renderWorkspaceDock();
  }

  function renderCompareRegions(report) {
    const regions = report.regions || [];
    const summary = report.summary || {};
    const domTotal = summary.domChanges ?? report.domChanges?.total ?? 0;
    const layoutTotal = summary.layoutChanges ?? report.layoutDiff?.counts?.layout ?? 0;
    if (els.compareRegionsMeta) {
      els.compareRegionsMeta.textContent = `${regions.length} região(ões) · DOM ${domTotal} · layout ${layoutTotal} · style ${summary.styleChanges ?? 0}`;
    }
    if (!els.compareRegionsList) return;
    if (!regions.length) {
      els.compareRegionsList.innerHTML = "<li class='muted'>Nenhuma região agrupada (imagens iguais ou só pixel).</li>";
      return;
    }
    els.compareRegionsList.innerHTML = regions
      .slice(0, 16)
      .map((r) => {
        const el = r.probableElement;
        const conf = el?.confidence ? ` · ${el.confidence}` : "";
        const sel = el?.selector ? escapeHtml(el.selector) : "sem elemento provável";
        return `<li class="compare-region-item severity-${escapeHtml(r.severity || "low")}">
          <div><strong>${escapeHtml(r.id)}</strong> ${escapeHtml(r.category || "diff")} · ${escapeHtml(r.severity || "")}</div>
          <div class="muted">${r.width}×${r.height} @ ${r.x},${r.y}</div>
          <div>${sel}${escapeHtml(conf)}</div>
          <div class="muted">${escapeHtml(r.diagnosis || "")}</div>
        </li>`;
      })
      .join("");
  }

  function fileToPngBase64(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        try {
          const canvas = document.createElement("canvas");
          canvas.width = img.naturalWidth || img.width;
          canvas.height = img.naturalHeight || img.height;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(img, 0, 0);
          const dataUrl = canvas.toDataURL("image/png");
          URL.revokeObjectURL(url);
          resolve(dataUrl.split(",")[1] || "");
        } catch (err) {
          URL.revokeObjectURL(url);
          reject(err);
        }
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error("Não foi possível ler a imagem"));
      };
      img.src = url;
    });
  }

  async function uploadMockupFile(file) {
    if (!state.current?.id || !file) return;
    if (state.visualApiOk === false) {
      const msg = visualApiMissingMessage({ status: 404, message: "not found" });
      showToast(msg, "err");
      if (els.compareStatus) els.compareStatus.textContent = msg;
      return;
    }
    if (els.compareStatus) els.compareStatus.textContent = "Enviando mockup…";
    try {
      const b64 = await fileToPngBase64(file);
      const stem = (file.name || "mockup").replace(/\.[^.]+$/, "");
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/mockup`, {
        method: "POST",
        body: JSON.stringify({
          name: `${stem}.png`,
          mime: "image/png",
          content_base64: b64,
        }),
      });
      if (els.compareMockupPath) els.compareMockupPath.value = data.path;
      setCompareFlowStep("compare");
      syncCompareEmptyState();
      updateVisualPrimaryCta(null);
      showToast(`Mockup salvo. Use “Alcançar resultado” para fechar o loop.`, "ok", 5500);
      if (els.compareStatus) {
        els.compareStatus.textContent = `Mockup pronto: ${data.path}. Clique em Alcançar resultado.`;
      }
    } catch (e) {
      const msg = visualApiMissingMessage(e);
      showToast(msg, "err");
      if (els.compareStatus) els.compareStatus.textContent = msg;
      if (e?.status === 404) {
        state.visualApiOk = false;
        setVisualControlsEnabled(false);
      }
    }
  }

  function setVisualControlsEnabled(enabled) {
    [
      els.btnCompareNow,
      els.btnCapturePreview,
      els.btnPixelPerfect,
      els.btnCorrectAuto,
      els.btnUploadMockup,
      els.btnBaselineApprove,
      els.btnBaselineReject,
      els.btnBaselineCompare,
    ].forEach((btn) => {
      if (btn) btn.disabled = !enabled;
    });
  }

  function visualApiMissingMessage(err) {
    const msg = String(err?.message || err?.data?.error || "");
    if (err?.status === 404 && (!msg || /not found|não encontrado/i.test(msg))) {
      return (
        "API Visual ausente neste servidor. Pare o Forge e reinicie na branch com Visual Engine " +
        "(feature/visual-engine-integration ou cursor/ui-nav-simplify-40ee), depois atualize a página."
      );
    }
    if (err?.status === 404 && /project not found/i.test(msg)) {
      return "Projeto não encontrado no servidor. Reabra o projeto na sidebar.";
    }
    return msg || "Falha ao carregar Visual Engine.";
  }

  async function refreshComparePanel() {
    if (!state.current?.id) {
      if (els.compareStatus) els.compareStatus.textContent = "Abra um projeto para comparar.";
      return;
    }
    if (state.serverFeatures && state.serverFeatures.visual_engine === false) {
      if (els.compareStatus) {
        els.compareStatus.textContent = "Este servidor não inclui Visual Engine.";
      }
      setVisualControlsEnabled(false);
      return;
    }
    try {
      const st = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/status`);
      state.visualApiOk = true;
      setVisualControlsEnabled(true);
      if (els.compareStatus) {
        els.compareStatus.textContent = st.ok
          ? `Visual Engine pronto${st.bridge?.chrome ? " · Chrome detectado" : ""}.`
          : st.error || "Visual Engine indisponível (Node/Chrome). Instale: cd visual_engine && npm install";
      }
      const hist = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/comparisons`);
      const items = hist.comparisons || [];
      if (els.compareHistoryList) {
        els.compareHistoryList.innerHTML = items.length
          ? items
              .slice(0, 12)
              .map((item) => {
                const sim =
                  item.similarity == null ? "—" : `${(Number(item.similarity) * 100).toFixed(1)}%`;
                const id = item.comparisonId || item.id;
                return `<li><button type="button" class="compare-hist-btn" data-id="${escapeHtml(id)}"><span>${escapeHtml(sim)}</span> ${escapeHtml(item.mode || "")} · ${escapeHtml(id)}</button></li>`;
              })
              .join("")
          : "<li class='muted'>Nenhuma comparação ainda.</li>";
      }
      await refreshBaselinesList();
      if (items[0] && items[0].mode !== "pixel_perfect") renderCompareReport(items[0]);
    } catch (e) {
      state.visualApiOk = false;
      setVisualControlsEnabled(false);
      if (els.compareStatus) els.compareStatus.textContent = visualApiMissingMessage(e);
      if (els.compareHistoryList) {
        els.compareHistoryList.innerHTML = "<li class='muted'>Histórico indisponível até o servidor Visual estar ativo.</li>";
      }
    }
  }

  async function refreshBaselinesList() {
    if (!state.current?.id || !els.compareBaselineList) return;
    try {
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/baselines`);
      const items = data.baselines || [];
      els.compareBaselineList.innerHTML = items.length
        ? items
            .map((b) => {
              const st = escapeHtml(b.status || "");
              const label = escapeHtml(b.label || b.routeId);
              return `<li><button type="button" class="compare-baseline-btn" data-route="${escapeHtml(b.routeId)}"><span>${label}</span> · ${st}</button></li>`;
            })
            .join("")
        : "<li class='muted'>Nenhuma baseline aprovada.</li>";
    } catch {
      els.compareBaselineList.innerHTML = "<li class='muted'>Baselines indisponíveis.</li>";
    }
  }

  function currentRouteId() {
    return (els.compareRouteId?.value || "").trim() || "home";
  }

  async function approveBaseline() {
    if (!state.current?.id) return;
    const routeId = currentRouteId();
    const cid = state.lastCompareReport?.comparisonId || state.lastCompareReport?.comparison_id;
    const mockup = (els.compareMockupPath?.value || "").trim();
    if (!cid && !mockup) {
      showToast("Compare ou informe um mockup antes de aprovar.", "info");
      return;
    }
    try {
      const body = { routeId, label: routeId, viewport: parseCompareViewport() };
      if (cid) body.comparisonId = cid;
      else body.path = mockup;
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/baselines/approve`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      showToast(`Baseline aprovada: ${data.baseline?.routeId || routeId}`, "ok");
      await refreshBaselinesList();
    } catch (e) {
      showToast(e.message || "Falha ao aprovar baseline", "err");
    }
  }

  async function rejectBaseline() {
    if (!state.current?.id) return;
    const routeId = currentRouteId();
    const cid = state.lastCompareReport?.comparisonId || state.lastCompareReport?.comparison_id || "";
    try {
      await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/baselines/reject`, {
        method: "POST",
        body: JSON.stringify({ routeId, comparisonId: cid, notes: "rejected from UI" }),
      });
      showToast(`Baseline rejeitada: ${routeId}`, "info");
      await refreshBaselinesList();
    } catch (e) {
      showToast(e.message || "Falha ao rejeitar baseline", "err");
    }
  }

  async function compareAgainstBaseline() {
    if (!state.current?.id) return;
    const routeId = currentRouteId();
    if (els.compareStatus) els.compareStatus.textContent = `Comparando vs baseline ${routeId}…`;
    try {
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/baselines/compare`, {
        method: "POST",
        body: JSON.stringify({
          routeId,
          mode: els.previewMode?.value === "dev" ? "dev" : "auto",
          viewport: parseCompareViewport(),
          target_similarity: 0.95,
          options: { fit: els.compareFit?.value || "contain", threshold: 0.1 },
        }),
      });
      renderCompareReport(data.report);
      const bl = data.baseline;
      if (els.compareScore && bl) {
        const badge = bl.passed ? "PASS" : "FAIL";
        els.compareScore.innerHTML += ` · baseline <strong>${escapeHtml(badge)}</strong>`;
      }
      await refreshComparePanel();
      showToast(bl?.passed ? "Regressão OK vs baseline." : "Regressão detectada vs baseline.", bl?.passed ? "ok" : "info");
    } catch (e) {
      if (els.compareStatus) els.compareStatus.textContent = e.message || "Falha vs baseline";
      showToast(e.message || "Falha vs baseline", "err");
    }
  }

  async function runCapturePreview() {
    if (!state.current?.id) return;
    if (els.compareStatus) els.compareStatus.textContent = "Capturando preview…";
    els.btnCapturePreview && (els.btnCapturePreview.disabled = true);
    try {
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/capture`, {
        method: "POST",
        body: JSON.stringify({
          preview: true,
          mode: els.previewMode?.value === "dev" ? "dev" : "auto",
          viewport: parseCompareViewport(),
        }),
      });
      renderCompareReport(data.report);
      await refreshComparePanel();
      showToast("Screenshot do preview capturado.", "ok");
    } catch (e) {
      if (els.compareStatus) els.compareStatus.textContent = e.message || "Falha na captura";
      showToast(e.message || "Falha na captura", "err");
    } finally {
      if (els.btnCapturePreview) els.btnCapturePreview.disabled = false;
    }
  }

  function renderCorrectionJob(job) {
    if (!job) {
      els.compareCorrection?.classList.add("hidden");
      els.btnCorrectCancel?.classList.add("hidden");
      return;
    }
    els.compareCorrection?.classList.remove("hidden");
    const base = job.baseline_similarity == null ? "—" : `${(job.baseline_similarity * 100).toFixed(1)}%`;
    const best = job.best_similarity == null ? "—" : `${(job.best_similarity * 100).toFixed(1)}%`;
    const imp = job.improvement == null ? "—" : `${(job.improvement * 100).toFixed(1)} pp`;
    if (els.compareCorrectionMeta) {
      els.compareCorrectionMeta.textContent = `${job.status} · base ${base} → melhor ${best} · Δ ${imp}`;
    }
    if (els.compareCorrectionAttempts) {
      const attempts = job.attempts || [];
      els.compareCorrectionAttempts.innerHTML = attempts.length
        ? attempts
            .map((a) => {
              const sim = a.similarity == null ? "—" : `${(Number(a.similarity) * 100).toFixed(1)}%`;
              return `<li><strong>#${a.attempt}</strong> ${escapeHtml(sim)} · ${escapeHtml(a.status)} · ${escapeHtml(a.notes || "")}</li>`;
            })
            .join("")
        : "<li class='muted'>Aguardando tentativas…</li>";
    }
    const running = job.status === "queued" || job.status === "running";
    els.btnCorrectCancel?.classList.toggle("hidden", !running);
    els.btnCorrectAuto && (els.btnCorrectAuto.disabled = running);
  }

  function stopCorrectionPolling() {
    if (state.correctionTimer) {
      clearInterval(state.correctionTimer);
      state.correctionTimer = null;
    }
  }

  async function pollCorrection(jobId) {
    if (!state.current?.id || !jobId) return;
    try {
      const data = await api(
        `/api/projects/${encodeURIComponent(state.current.id)}/visual/correction/${encodeURIComponent(jobId)}`
      );
      const job = data.correction;
      state.correctionJob = job;
      renderCorrectionJob(job);
      if (job && (job.status === "queued" || job.status === "running")) return;
      stopCorrectionPolling();
      if (job?.status === "completed") {
        const best = reportSimilarity(job);
        const reached = visualTargetReached(best);
        showToast(
          reached
            ? `Correção concluída · ${(best * 100).toFixed(1)}% (meta atingida).`
            : `Correção concluída · ${best == null ? "—" : `${(best * 100).toFixed(1)}%`}. Ainda abaixo da meta.`,
          reached ? "ok" : "info",
          6000
        );
        refreshComparePanel();
        updatePreview();
        const synthetic = state.lastCompareReport
          ? { ...state.lastCompareReport, similarity: best ?? state.lastCompareReport.similarity }
          : { similarity: best, regions: [], layoutChanges: [] };
        if (best != null) {
          state.lastCompareReport = synthetic;
          updateVisualPrimaryCta(synthetic);
        }
        addVisualOutcomeCard(synthetic, job);
        if (!reached && state.visualReachInFlight) {
          fillVisualAgentBrief(synthetic, job, { send: false });
          showToast("CSS estabilizou abaixo da meta — brief visual pronto para o agente.", "info", 6500);
        }
        state.visualReachInFlight = false;
      } else if (job?.status === "cancelled") {
        state.visualReachInFlight = false;
        showToast("Correction loop interrompido.", "info");
      } else if (job?.status === "failed") {
        state.visualReachInFlight = false;
        showToast(job.error || "Correction loop falhou", "err");
      }
    } catch (e) {
      stopCorrectionPolling();
      state.visualReachInFlight = false;
      showToast(e.message || "Falha ao consultar correction", "err");
    }
  }

  async function startCorrectionLoop({ fromSmartFlow = false } = {}) {
    if (!state.current?.id) return;
    const mockup = ensureMockupPath();
    if (!mockup) {
      showToast("Envie ou informe um mockup antes de corrigir.", "info");
      return null;
    }
    stopCorrectionPolling();
    setCompareFlowStep("correct");
    if (els.compareStatus) els.compareStatus.textContent = "Iniciando correction loop…";
    els.btnCorrectAuto && (els.btnCorrectAuto.disabled = true);
    try {
      // Prefer single-viewport layout-aware correction unless the user chose a suite.
      const suite = fromSmartFlow ? "" : selectedCompareSuite();
      const target = Number(state.visualTargetSimilarity) || 0.92;
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/correction/start`, {
        method: "POST",
        body: JSON.stringify({
          mockup,
          preview_mode: els.previewMode?.value === "dev" ? "dev" : "auto",
          viewport: parseCompareViewport(),
          suite: suite || undefined,
          fit: els.compareFit?.value || "contain",
          options: { includeDomDiff: true, includeLayout: true, fit: els.compareFit?.value || "contain" },
          target_similarity: Math.max(target, 0.95),
          max_attempts: 5,
        }),
      });
      state.correctionJob = data.correction;
      renderCorrectionJob(data.correction);
      state.correctionTimer = setInterval(() => pollCorrection(data.correction.id), 1500);
      showToast("Correction loop em execução…", "info");
      return data.correction;
    } catch (e) {
      els.btnCorrectAuto && (els.btnCorrectAuto.disabled = false);
      state.visualReachInFlight = false;
      showToast(e.message || "Não foi possível iniciar a correção", "err");
      return null;
    }
  }

  async function startReachResultFlow({ autoCorrect = true } = {}) {
    if (!state.current?.id || state.visualReachInFlight) return;
    const mockup = ensureMockupPath();
    if (!mockup) {
      openVisualMockupFlow();
      showToast("Envie o mockup para o motor guiar o resultado.", "info", 5000);
      return;
    }
    state.visualReachInFlight = true;
    setSurfaceMode("work");
    switchToolGroup("visual", "compare");
    setCompareFlowStep("compare");
    try {
      const report = await runCompareNow({ smartFollowUp: false, quiet: true, layoutAware: true });
      const sim = reportSimilarity(report);
      if (visualTargetReached(sim)) {
        showToast(`Já está perto do mockup (${(sim * 100).toFixed(1)}%).`, "ok", 5000);
        addVisualOutcomeCard(report, null);
        state.visualReachInFlight = false;
        return;
      }
      if (!autoCorrect) {
        updateVisualPrimaryCta(report);
        addVisualOutcomeCard(report, null);
        state.visualReachInFlight = false;
        return;
      }
      showToast(
        `Similaridade ${sim == null ? "—" : `${(sim * 100).toFixed(1)}%`} — iniciando correção automática…`,
        "info",
        5500
      );
      const job = await startCorrectionLoop({ fromSmartFlow: true });
      if (!job) state.visualReachInFlight = false;
    } catch (e) {
      state.visualReachInFlight = false;
      showToast(e.message || "Falha ao alcançar resultado", "err");
    }
  }

  async function cancelCorrectionLoop() {
    const id = state.correctionJob?.id;
    if (!state.current?.id || !id) return;
    try {
      const data = await api(
        `/api/projects/${encodeURIComponent(state.current.id)}/visual/correction/${encodeURIComponent(id)}/cancel`,
        { method: "POST", body: "{}" }
      );
      renderCorrectionJob(data.correction);
      showToast("Cancelamento solicitado.", "info");
    } catch (e) {
      showToast(e.message || "Falha ao cancelar", "err");
    }
  }

  function buildCompareBody({ pixelPerfect = false, layoutAware = false } = {}) {
    const mockup = ensureMockupPath() || (els.compareMockupPath?.value || "").trim();
    const targetUrl = (els.compareTargetUrl?.value || "").trim();
    const fit = els.compareFit?.value || "contain";
    const suite = layoutAware ? "" : selectedCompareSuite();
    const wantLayout = layoutAware || !(pixelPerfect || !!suite);
    const body = {
      mode: els.previewMode?.value === "dev" ? "dev" : "auto",
      viewport: parseCompareViewport(),
      options: {
        threshold: 0.1,
        fit,
        includeDomDiff: wantLayout,
        includeLayout: wantLayout,
      },
      target_similarity: Number(state.visualTargetSimilarity) || 0.92,
    };
    if (mockup) body.mockup = mockup;
    else if (targetUrl) body.preview_vs_url = targetUrl;
    if (pixelPerfect || suite) {
      body.pixel_perfect = true;
      body.suite = suite || "responsive";
    }
    return { body, mockup, targetUrl };
  }

  async function runCompareNow({ smartFollowUp = false, quiet = false, layoutAware = false } = {}) {
    if (!state.current?.id) return null;
    const { body, mockup, targetUrl } = buildCompareBody({
      pixelPerfect: false,
      layoutAware: layoutAware || smartFollowUp,
    });
    if (!mockup && !targetUrl) {
      showToast("Informe uma URL alvo ou um caminho de mockup.", "info");
      return null;
    }
    if (els.compareStatus) els.compareStatus.textContent = "Comparando…";
    setCompareFlowStep("compare");
    els.btnCompareNow && (els.btnCompareNow.disabled = true);
    try {
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/compare`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (data.suite) renderSuiteReport(data.suite);
      else els.compareSuitePanel?.classList.add("hidden");
      renderCompareReport(data.report);
      await refreshComparePanel();
      setCompareFlowStep("correct");
      updateVisualPrimaryCta(data.report);
      if (els.compareAdvanced) els.compareAdvanced.open = false;
      const sim = reportSimilarity(data.report);
      const reached = visualTargetReached(sim);
      if (!quiet) {
        showToast(
          reached
            ? `Comparação pronta · ${(sim * 100).toFixed(1)}% (meta ok).`
            : data.suite
              ? "Suite concluída. Use “Alcançar resultado” ou corrija as diferenças."
              : `Comparação pronta · ${sim == null ? "—" : `${(sim * 100).toFixed(1)}%`}. Próximo: corrigir.`,
          reached ? "ok" : "info",
          5500
        );
      }
      if (smartFollowUp && data.report) {
        addVisualOutcomeCard(data.report, null);
      }
      return data.report;
    } catch (e) {
      if (els.compareStatus) els.compareStatus.textContent = e.message || "Falha na comparação";
      showToast(e.message || "Falha na comparação", "err");
      return null;
    } finally {
      if (els.btnCompareNow) els.btnCompareNow.disabled = false;
    }
  }

  async function runPixelPerfect() {
    if (!state.current?.id) return;
    if (!selectedCompareSuite() && els.compareSuite) els.compareSuite.value = "responsive";
    const { body, mockup, targetUrl } = buildCompareBody({ pixelPerfect: true });
    if (!mockup && !targetUrl) {
      showToast("Informe uma URL alvo ou um caminho de mockup.", "info");
      return;
    }
    if (els.compareStatus) els.compareStatus.textContent = "Pixel Perfect — multi-viewport…";
    els.btnPixelPerfect && (els.btnPixelPerfect.disabled = true);
    els.btnCompareNow && (els.btnCompareNow.disabled = true);
    try {
      const data = await api(`/api/projects/${encodeURIComponent(state.current.id)}/visual/compare`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (data.suite) renderSuiteReport(data.suite);
      renderCompareReport(data.report);
      await refreshComparePanel();
      const st = data.suite?.status || "done";
      showToast(st === "passed" ? "Pixel Perfect: meta atingida." : "Pixel Perfect: há viewports abaixo da meta.", st === "passed" ? "ok" : "info");
    } catch (e) {
      if (els.compareStatus) els.compareStatus.textContent = e.message || "Falha no Pixel Perfect";
      showToast(e.message || "Falha no Pixel Perfect", "err");
    } finally {
      if (els.btnPixelPerfect) els.btnPixelPerfect.disabled = false;
      if (els.btnCompareNow) els.btnCompareNow.disabled = false;
    }
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
  els.workspaceDock?.addEventListener("click", (e) => {
    const reach = e.target.closest("[data-dock-action='reach']");
    if (reach) {
      setSurfaceMode("work");
      switchToolGroup("visual", "compare");
      startReachResultFlow({ autoCorrect: true });
      return;
    }
    const btn = e.target.closest(".dock-open-btn");
    if (!btn) return;
    const group = btn.dataset.openGroup;
    const tab = btn.dataset.openTab;
    if (!group || !tab) return;
    setSurfaceMode("work");
    if (group === "visual" && !(els.compareMockupPath?.value || "").trim() && !state.lastCompareReport) {
      openVisualMockupFlow();
      return;
    }
    switchToolGroup(group, tab);
  });
  els.mobileTabs?.addEventListener("click", (e) => {
    const btn = e.target.closest(".mobile-tab");
    if (!btn) return;
    if (btn.dataset.surface === "chat") {
      closeMobilePanel();
      setSurfaceMode("chat");
      syncMobileTabs();
      return;
    }
    if (btn.dataset.group) {
      setSurfaceMode("work");
      switchToolGroup(btn.dataset.group, btn.dataset.tab);
      // switchToolGroup → switchTab: mark as mobile intent
      if (isMobileLayout()) openMobilePanel();
      syncMobileTabs(btn.dataset.tab, btn.dataset.group);
      return;
    }
    if (btn.dataset.tab) switchTab(btn.dataset.tab, { fromMobile: true });
  });

  document.getElementById("toolsGroups")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".tools-group");
    if (!btn?.dataset.group) return;
    switchToolGroup(btn.dataset.group);
  });

  document.addEventListener("click", (e) => {
    const more = document.getElementById("topbarMore");
    if (!more?.open) return;
    if (!more.contains(e.target)) more.open = false;
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
  els.btnMinimizePanels?.addEventListener("click", () => {
    if (!isMobileLayout()) {
      setSidebarCollapsed(true);
      setPanelCollapsed(true);
      return;
    }
    closeSidebar();
    closeMobilePanel();
  });
  els.sidebar?.querySelector(".logo")?.addEventListener("click", () => {
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
  });
  els.btnSidebarSearch?.addEventListener("click", () => {
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
    if (!state.current) {
      showToast("Escolha um projeto para abrir os arquivos.", "info", 4000);
      els.projectSearch?.focus();
      return;
    }
    showWorkspace();
    switchToolGroup("app", "files");
    requestAnimationFrame(() => {
      els.fileSearchInput?.focus();
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
      const expected = expectedAutoModel();
      updateActiveModelDisplay(expected, { source: "auto", live: false });
      showToast(
        expected
          ? `Modelo: Auto → <strong>${escapeHtml(expected)}</strong>`
          : "Modelo: Auto (escolhe conforme o hardware)",
        "ok"
      );
      return;
    }
    updateActiveModelDisplay(selected, { source: "manual", live: false });
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

  els.btnSidebarWork?.addEventListener("click", () => setSurfaceMode("work"));
  els.btnSidebarChat?.addEventListener("click", () => setSurfaceMode("chat"));
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
  els.btnEmptyGoWork?.addEventListener("click", () => setSurfaceMode("work"));
  els.btnEmptyNewProject?.addEventListener("click", () => {
    setSurfaceMode("work");
    openNewProjectModal(state.selectedTemplate || "landing");
  });
  els.btnChooseProjectEmpty?.addEventListener("click", () => {
    setSurfaceMode("work");
    if (!isMobileLayout() && isSidebarCollapsed()) setSidebarCollapsed(false);
    openSidebar();
    els.projectSearch?.focus();
  });
  els.btnNewProjectEmpty?.addEventListener("click", () => openNewProjectModal("blank"));
  els.btnUploadMockupPrimary?.addEventListener("click", () => els.compareMockupFile?.click());
  els.workStepper?.addEventListener("click", (e) => {
    const step = e.target.closest(".work-step")?.dataset?.step;
    if (!step || !state.current) return;
    setSurfaceMode("work");
    if (step === "check") {
      if (visualEngineAvailable() && (ensureMockupPath() || "").trim()) {
        switchToolGroup("visual", "compare");
      } else {
        switchToolGroup("app", "preview");
      }
    } else if (step === "work") {
      switchToolGroup("agent", "live");
    } else if (step === "done") {
      switchToolGroup("app", "preview");
    }
  });
  els.btnQuickMockup?.addEventListener("click", (e) => {
    e.preventDefault();
    openVisualMockupFlow();
  });
  els.btnPreviewOpenFiles?.addEventListener("click", () => {
    if (!state.current) {
      showToast("Escolha um projeto primeiro.", "info");
      return;
    }
    switchToolGroup("app", "files");
  });
  els.btnPreviewGoVisual?.addEventListener("click", () => openVisualMockupFlow());
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
      const expected = expectedAutoModel();
      updateActiveModelDisplay(expected, { source: "auto", live: false });
      showToast(
        expected
          ? `Modelo: Auto → <strong>${escapeHtml(expected)}</strong>`
          : "Modelo: Auto (escolhe conforme o hardware)",
        "ok"
      );
      return;
    }
    setModelSelection(val);
    rememberModelPreference(val);
    updateActiveModelDisplay(val, { source: "manual", live: false });
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
  els.activeModelBadge?.addEventListener("click", openModelsModal);
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

  els.btnCompareNow?.addEventListener("click", runCompareNow);
  els.btnPixelPerfect?.addEventListener("click", runPixelPerfect);
  els.btnCapturePreview?.addEventListener("click", runCapturePreview);
  els.btnCorrectAuto?.addEventListener("click", () => startCorrectionLoop());
  els.btnCorrectPrimary?.addEventListener("click", () => {
    if (els.compareAdvanced) els.compareAdvanced.open = true;
    startCorrectionLoop({ fromSmartFlow: true });
  });
  els.btnReachResult?.addEventListener("click", () => startReachResultFlow({ autoCorrect: true }));
  els.btnVisualAgentBrief?.addEventListener("click", () => {
    fillVisualAgentBrief(state.lastCompareReport, state.correctionJob, { send: false });
  });
  els.btnDevErrorRestart?.addEventListener("click", () => startDevServer());
  els.projectBadge?.addEventListener("click", () => {
    setSurfaceMode(state.surfaceMode === "work" ? "chat" : "work");
  });
  els.healthStatus?.addEventListener("click", () => {
    openModelsModal();
    if (!state.ollamaOk) {
      showToast("Configure o Ollama para voltar a gerar código.", "info", 4500);
    }
  });
  els.btnCorrectCancel?.addEventListener("click", cancelCorrectionLoop);
  els.btnBaselineApprove?.addEventListener("click", approveBaseline);
  els.btnBaselineReject?.addEventListener("click", rejectBaseline);
  els.btnBaselineCompare?.addEventListener("click", compareAgainstBaseline);
  els.compareBaselineList?.addEventListener("click", (e) => {
    const btn = e.target.closest(".compare-baseline-btn");
    if (!btn?.dataset.route || !els.compareRouteId) return;
    els.compareRouteId.value = btn.dataset.route;
  });
  els.compareMockupPath?.addEventListener("input", () => {
    syncCompareEmptyState();
    if ((els.compareMockupPath.value || "").trim()) updateVisualPrimaryCta(state.lastCompareReport);
  });
  els.btnUploadMockup?.addEventListener("click", () => els.compareMockupFile?.click());
  els.compareMockupFile?.addEventListener("change", () => {
    const file = els.compareMockupFile.files?.[0];
    if (file) uploadMockupFile(file);
    els.compareMockupFile.value = "";
  });
  els.compareViewTabs?.addEventListener("click", (e) => {
    const btn = e.target.closest(".compare-view-btn");
    if (!btn?.dataset.view) return;
    setCompareView(btn.dataset.view);
  });
  els.compareSliderRange?.addEventListener("input", syncCompareSlider);
  window.addEventListener("resize", () => {
    if (state.compareView === "slider") syncCompareSlider();
  });
  els.compareHistoryList?.addEventListener("click", async (e) => {
    const btn = e.target.closest(".compare-hist-btn");
    if (!btn?.dataset.id || !state.current?.id) return;
    try {
      const data = await api(
        `/api/projects/${encodeURIComponent(state.current.id)}/visual/comparisons/${encodeURIComponent(btn.dataset.id)}`
      );
      renderCompareReport(data.comparison);
    } catch (err) {
      showToast(err.message || "Não foi possível abrir a comparação", "err");
    }
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

  function syncModeControls(opts = {}) {
    const mode = els.modeSelect?.value || "chat";
    const isChat = mode === "chat";
    const isExecute = mode === "execute";
    document.getElementById("stepsControl")?.classList.toggle("hidden", isChat);
    document.querySelector('label[for="maxStepsInput"]')?.classList.toggle("hidden", isChat);
    if (els.modeChip) {
      els.modeChip.textContent = isExecute ? "Executar" : "Chat";
      els.modeChip.classList.toggle("mode-chip--execute", isExecute);
      els.modeChip.title = isExecute
        ? "Modo Executar — altera arquivos no projeto (usa o contexto do Chat)"
        : "Modo Chat — conversa livre sobre qualquer assunto";
    }
    // Placeholders follow Chat|Work surface, not the buried modeSelect.
    if (!opts.preservePlaceholder) applySurfacePlaceholder();
    else applySurfacePlaceholder();
    syncComposerToolHint();
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
    tab.addEventListener("click", () => {
      if (tab.dataset.group) switchToolGroup(tab.dataset.group, tab.dataset.tab);
      else switchTab(tab.dataset.tab);
    });
  });

  document.querySelectorAll(".quick-card").forEach((card) => {
    card.addEventListener("click", () => {
      if (card.id === "btnQuickMockup") return;
      const prompt = card.dataset.prompt;
      if (!prompt || !state.current || state.running) return;
      els.promptInput.value = prompt;
      els.promptInput.focus();
      if (card.dataset.send === "1" && !state.running) sendPrompt();
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeComposerMenu();
  });

  els.btnComposerPlus?.setAttribute("aria-expanded", "false");
  els.btnComposerPlus?.setAttribute("aria-haspopup", "menu");

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
    migrateDesignerLayoutOnce();
    restoreSidebarCollapsed();
    syncSidebarToggle();
    try {
      const savedSurface = localStorage.getItem("forge_surface_mode");
      // Sem projeto, Chat é a entrada mais clara; Work fica após criar template.
      setSurfaceMode(savedSurface === "work" ? "work" : "chat");
    } catch (_) {
      setSurfaceMode("chat");
    }
    initLayoutSplitters();
    initLayoutPresets();
    setPreviewDevice(state.previewDevice);
    checkHealth();
    setInterval(checkHealth, 30000);
    refreshSidebarResources();
    setInterval(refreshSidebarResources, 15000);
    syncWorkRailVisibility();
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
