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
    deploying: false,
    mobilePanelOpen: false,
    runs: [],
    selectedRunId: null,
    fileSearchTimer: null,
    ollamaOk: false,
    previewDevice: "desktop",
    healthInFlight: false,
    setupInFlight: null,
    pendingPrompt: null,
    ollamaInstalled: true,
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    sidebar: $("sidebar"),
    sidebarBackdrop: $("sidebarBackdrop"),
    btnToggleSidebar: $("btnToggleSidebar"),
    fileSearchInput: $("fileSearchInput"),
    runHistoryList: $("runHistoryList"),
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
    btnClearChat: $("btnClearChat"),
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
    deployModalInner: $("deployModalInner"),
    deployBadge: $("deployBadge"),
    deploySpinner: $("deploySpinner"),
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
  };

  const SETUP_STEPS = [
    { id: "check", label: "Verificar ambiente" },
    { id: "install", label: "Instalar Ollama" },
    { id: "start", label: "Iniciar serviço Ollama" },
    { id: "hardware", label: "Analisar hardware" },
    { id: "model", label: "Baixar modelo IA" },
    { id: "config", label: "Configurar modelo" },
    { id: "done", label: "Pronto para usar" },
  ];

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
    if (!Object.keys(setupProgress.stepStatus).length) resetSetupProgress();
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

  function finishSetupError(message) {
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
    updateSetupProgress(setupProgress.lastPercent || 0, message || "Falha na configuração.");
    if (els.setupSubtitle) els.setupSubtitle.textContent = "Corrija o problema abaixo ou tente novamente.";
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
      if (state.ollamaInstalled === false) {
        els.ollamaOfflineText.textContent =
          "Ollama não detectado. Clique em Configurar automaticamente para instalar (winget), iniciar e baixar o modelo.";
      } else if (!state.models.length) {
        els.ollamaOfflineText.textContent =
          "Nenhum modelo instalado. Clique abaixo para baixar o recomendado para o seu hardware.";
      } else {
        els.ollamaOfflineText.textContent =
          "Clique abaixo para iniciar o Ollama e baixar o modelo recomendado automaticamente.";
      }
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
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) {
      if (showProgress) {
        if (res.status === 404) {
          finishSetupError(
            "Servidor desatualizado. Pare a plataforma (Ctrl+C) e execute novamente: .\\scripts\\run-platform.ps1"
          );
        } else {
          finishSetupError(data.error || "Falha ao configurar Ollama.");
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
        return ensureOllamaViaEnsureEndpoint(showProgress);
      }

      if (!res.ok || !res.body) {
        const errData = await res.json().catch(() => ({}));
        if (showProgress) finishSetupError(errData.error || "Falha ao configurar Ollama.");
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
        if (showProgress) finishSetupError(donePayload?.error || "Não foi possível configurar o Ollama.");
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

  async function ensureEnvironment(options = {}) {
    const { pullRecommended = false, showProgress = true } = options;
    if (showProgress) showSetupModal("Iniciando configuração...", 3);

    if (state.setupInFlight) return state.setupInFlight;

    let setupOk = false;

    const task = (async () => {
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
          if (showProgress) finishSetupError(`Falha ao baixar o modelo ${rec}.`);
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
      }
      return ok;
    })();

    state.setupInFlight = task;
    try {
      setupOk = await task;
      return setupOk;
    } finally {
      state.setupInFlight = null;
      if (showProgress && !setupOk) {
        /* mantém modal aberto para o usuário ver o erro */
      }
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
      updateModelOptions(state.models);
      applyRecommendedModel(d.recommended_model, state.models);
      const modelLabel = getSelectedModel() ? ` · ${getSelectedModel()}` : " · auto";
      els.healthStatus.innerHTML = `<span class="status-dot ${state.ollamaOk ? "ok" : "err"}"></span>${state.ollamaOk ? "Ollama pronto" : "Ollama offline?"}${modelLabel}`;
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
      item.addEventListener("click", () => {
        selectProject(p.id);
        closeSidebar();
      });
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
    state.selectedRunId = null;
    state.lastReport = "";
    state.previewMode = "static";
    els.previewMode.value = "static";
    els.fileViewer.classList.add("hidden");
    els.fileViewer.textContent = "";
    els.projectTitle.textContent = project.name;
    els.emptyView.classList.add("hidden");
    els.workspaceView.classList.remove("hidden");
    renderProjectList();
    closeSidebar();
    await loadChat();
    await loadRunHistory();
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
        return `<li data-run-id="${escapeHtml(run.id)}" class="${active.trim()}">
          <div class="run-status ${cls}">${status}</div>
          <div>${goal}</div>
          <div class="run-meta">${formatRunTime(run.ts)}</div>
        </li>`;
      })
      .join("");
    els.runHistoryList.querySelectorAll("[data-run-id]").forEach((item) => {
      item.addEventListener("click", () => selectRun(item.dataset.runId));
    });
  }

  function selectRun(runId) {
    const run = (state.runs || []).find((r) => r.id === runId);
    if (!run) return;
    state.selectedRunId = runId;
    state.lastReport = run.report || run.summary || "";
    setMessageContent(els.reportViewer, state.lastReport, "agent");
    renderRunHistory();
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
        setMessageContent(els.reportViewer, state.lastReport, "agent");
        renderRunHistory();
      }
    } catch {
      state.runs = [];
      renderRunHistory();
    }
  }

  async function searchProjectFiles(query) {
    if (!state.current || !query.trim()) {
      await loadFiles();
      return;
    }
    try {
      const d = await api(
        `/api/projects/${encodeURIComponent(state.current.id)}/search?q=${encodeURIComponent(query.trim())}`
      );
      state.files = (d.matches || []).map((m) => ({
        path: m.path,
        name: m.path.split("/").pop(),
        type: "file",
      }));
      renderFileTree();
    } catch (e) {
      els.fileTree.innerHTML = `<li class="file-error">${escapeHtml(e.message)}</li>`;
    }
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

  function addMessage(text, role, scroll = true) {
    const el = document.createElement("div");
    el.className = "msg " + role + (role === "agent" && /^Erro/i.test(text) ? " error" : "");
    setMessageContent(el, text, role);
    els.chatMessages.appendChild(el);
    if (scroll) els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
    if (role === "user" || role === "agent") updateChatHeroVisibility();
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

    const ready = await ensureEnvironment({ pullRecommended: true, showProgress: true });
    if (!ready) {
      addMessage(
        "Ambiente não configurado. Use Modelos IA → Configurar automaticamente (Ollama + modelo recomendado).",
        "system"
      );
      openModelsModal();
      state.pendingPrompt = prompt;
      return;
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

    const mode = els.modeSelect.value;
    const progressEl = addMessage("Iniciando agente...", "progress");
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
          max_steps: parseInt(els.maxStepsInput.value || "12", 10),
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
          handleStreamEvent(ev, progressEl, agentEl);
        }
      }

      removeMessage(progressEl);
      agentEl.classList.remove("live");

      if (donePayload) {
        const summary = donePayload.report || "(sem relatório)";
        setMessageContent(agentEl, summary, "agent");
        state.lastReport = summary;
        setMessageContent(els.reportViewer, summary, "agent");
        if (donePayload.status === "CANCELLED") {
          agentEl.classList.add("error");
        } else if (donePayload.created_files?.length || donePayload.modified_files?.length) {
          const changed = [...(donePayload.created_files || []), ...(donePayload.modified_files || [])];
          const note = `Arquivos alterados: ${changed.join(", ")}`;
          addMessage(note, "system");
          await persistMessage("system", note);
        }
        await loadProjects();
        await loadFiles();
        await loadRunHistory();
        await refreshDevStatus();
        updatePreview();
        switchTab("report");
      } else {
        agentEl.textContent = agentEl.textContent || "Execução finalizada sem relatório.";
      }
    } catch (e) {
      removeMessage(progressEl);
      agentEl.classList.remove("live");
      if (e.status === 409 || e.data?.busy) {
        agentEl.textContent = e.message || "Agente já em execução neste projeto.";
        agentEl.classList.add("error");
        addMessage("Aguarde a execução atual terminar ou cancele antes de enviar outro prompt.", "system");
      } else if (e.name === "AbortError") {
        wasAbort = true;
        agentEl.textContent = "Cancelando...";
        agentEl.classList.add("error");
      } else if (e.status === 503 || e.data?.ollama_offline) {
        const ready = await ensureEnvironment({ pullRecommended: true, showProgress: true });
        if (ready) {
          els.promptInput.value = prompt;
          state.running = false;
          removeMessage(agentEl);
          removeMessage(progressEl);
          return sendPrompt();
        }
        state.ollamaOk = false;
        updateOllamaOfflineUI();
        const err = e.message || "Ollama offline.";
        agentEl.textContent = "Erro: " + err;
        agentEl.classList.add("error");
        openModelsModal();
      } else {
        const err = "Erro: " + e.message;
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
              return sendPrompt();
            }
          }
        }
        await persistMessage("agent", err).catch(() => {});
      }
    } finally {
      state.running = false;
      state.runId = null;
      state.abortController = null;
      state.llmPreviewChars = 0;
      els.btnSend.disabled = false;
      els.btnCancel?.classList.add("hidden");
      els.btnCancel.disabled = false;
      updateChatHeroVisibility();
      if (wasAbort) {
        await new Promise((r) => setTimeout(r, 400));
        await loadChat().catch(() => {});
      }
      els.promptInput.focus();
    }
  }

  function handleStreamEvent(ev, progressEl, agentEl) {
    switch (ev.type) {
      case "started":
        if (ev.run_id) {
          state.runId = ev.run_id;
          if (els.btnCancel) els.btnCancel.disabled = false;
        }
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
        if (ev.text && agentEl) {
          state.llmPreviewChars = Math.min(state.llmPreviewChars + ev.text.length, 2000);
          agentEl.textContent = (agentEl.textContent + ev.text).slice(-2000);
        }
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
        ? "Apps React/Vite precisam de npm run dev — clique em Iniciar dev."
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
      els.devErrorLog?.classList.add("hidden");
    } else if (!s.npm_available) {
      els.devStatus.textContent = "Instale Node.js para dev server";
    } else if (s.last_error) {
      els.devStatus.textContent = "Último erro no dev server";
      if (els.devErrorLog) {
        els.devErrorLog.textContent = s.last_error;
        els.devErrorLog.classList.remove("hidden");
      }
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
  }

  function openDeployModal(text) {
    els.deployLog.textContent = text;
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
    els.deploySpinner?.classList.remove("hidden");
    openDeployModal("Preparando deploy...\n\nRequer VERCEL_TOKEN no ambiente para deploy automático.");
    try {
      const d = await api(`/api/projects/${encodeURIComponent(state.current.id)}/deploy`, {
        method: "POST",
        body: "{}",
      });
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
  els.btnAutoSetup?.addEventListener("click", async () => {
    try {
      showSetupModal("Iniciando configuração automática...", 3);
      const ok = await ensureEnvironment({ pullRecommended: true, showProgress: true });
      if (ok) {
        updateOllamaOfflineUI();
        await loadModelRecommendations().catch(() => {});
        if (state.pendingPrompt && state.current) {
          els.promptInput.value = state.pendingPrompt;
          state.pendingPrompt = null;
          sendPrompt();
        } else {
          closeModelsModal();
        }
      }
    } catch (e) {
      finishSetupError(e.message || "Erro inesperado na configuração.");
    }
  });
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
    ensureEnvironment({ pullRecommended: true, showProgress: true }).catch(() => {
      openModelsModal();
    });
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
