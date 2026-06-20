    const tabButtons = document.querySelectorAll(".tab-button");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const scriptSelect = document.querySelector("#script-select");
    const scriptDetails = document.querySelector("#script-details");
    const dryRunCheckbox = document.querySelector("#dry-run-enabled");
    const colorInput = document.querySelector("#dry-run-color");
    const dryRunScreenStateInput = document.querySelector("#dry-run-screen-state");
    const screenStateSuggestions = document.querySelector("#screen-state-suggestions");
    const useProbedScreenStateButton = document.querySelector("#use-probed-screen-state");
    const useScriptScreenStateButton = document.querySelector("#use-script-screen-state");
    const statusEl = document.querySelector("#status");
    const outputEl = document.querySelector("#output");
    const runScriptButton = document.querySelector("#run-script");
    const stopScriptButton = document.querySelector("#stop-script");
    const runTestsButton = document.querySelector("#run-tests");
    const imageAssetSelect = document.querySelector("#image-asset-select");
    const imageAssetFolder = document.querySelector("#image-asset-folder");
    const refreshImagesButton = document.querySelector("#refresh-images");
    const clickImageButton = document.querySelector("#click-image");
    const captureScreenButton = document.querySelector("#capture-screen");
    const captureRegionDiagnosticsButton = document.querySelector("#capture-region-diagnostics");
    const captureProbeDiagnosticsButton = document.querySelector("#capture-probe-diagnostics");
    const captureRegionCropsButton = document.querySelector("#capture-region-crops");
    const captureProbeCropsButton = document.querySelector("#capture-probe-crops");
    const imageConfidenceInput = document.querySelector("#image-confidence");
    const debugPreview = document.querySelector("#debug-preview");
    const debugScreenshot = document.querySelector("#debug-screenshot");
    const screenStateConfidenceInput = document.querySelector("#screen-state-confidence");
    const screenStateIntervalInput = document.querySelector("#screen-state-interval");
    const screenStateConfigSummary = document.querySelector("#screen-state-config-summary");
    const screenStateCurrent = document.querySelector("#screen-state-current");
    const screenStateStats = document.querySelector("#screen-state-stats");
    const screenStateCandidates = document.querySelector("#screen-state-candidates");
    const screenStateLog = document.querySelector("#screen-state-log");
    const startScreenStateProbeButton = document.querySelector("#start-screen-state-probe");
    const stopScreenStateProbeButton = document.querySelector("#stop-screen-state-probe");
    let scriptRunPollTimer = null;
    let activeScriptRun = false;
    let screenStateProbePollTimer = null;
    let activeScreenStateProbe = false;
    let latestScreenState = "未知";
    let currentScriptDetailsPayload = null;
    let scriptStateDependencies = [];
    let scriptImageDependencies = [];

    function setBusy(isBusy) {
      runScriptButton.disabled = isBusy;
      runTestsButton.disabled = isBusy;
      refreshImagesButton.disabled = isBusy;
      captureScreenButton.disabled = isBusy;
      captureRegionDiagnosticsButton.disabled = isBusy;
      captureProbeDiagnosticsButton.disabled = isBusy;
      captureRegionCropsButton.disabled = isBusy;
      captureProbeCropsButton.disabled = isBusy;
      clickImageButton.disabled = isBusy || !imageAssetSelect.value;
      useProbedScreenStateButton.disabled = isBusy;
      useScriptScreenStateButton.disabled = isBusy;
      stopScriptButton.disabled = !activeScriptRun;
    }

    function setScreenStateBusy(isBusy) {
      startScreenStateProbeButton.disabled = isBusy;
      stopScreenStateProbeButton.disabled = !isBusy;
    }

    function setupTabs() {
      for (const button of tabButtons) {
        button.addEventListener("click", () => {
          const targetId = button.dataset.tabTarget;
          for (const candidate of tabButtons) {
            candidate.classList.toggle("active", candidate === button);
          }
          for (const panel of tabPanels) {
            panel.hidden = panel.id !== targetId;
          }
        });
      }
    }

    function renderResult(prefix, result) {
      statusEl.textContent = `${prefix}退出码：${result.exit_code}`;
      outputEl.textContent = `${result.stdout || ""}${result.stderr || ""}`;
      if (result.screenshot_url) {
        debugScreenshot.src = result.screenshot_url;
        debugPreview.style.display = "block";
      }
    }

    function renderScriptStatus(result) {
      if (result.running) {
        statusEl.textContent = "脚本运行中...";
      } else if (result.exit_code === null || result.exit_code === undefined) {
        statusEl.textContent = "脚本未运行";
      } else {
        statusEl.textContent = `脚本退出码：${result.exit_code}`;
      }
      outputEl.textContent = `${result.stdout || ""}${result.stderr || ""}`;
    }

    function renderScreenStateStatus(result) {
      const state = result.current_state || "未知";
      latestScreenState = state;
      if (result.running) {
        screenStateCurrent.textContent = `当前状态：${state}（探测中）`;
      } else if (result.exit_code === null || result.exit_code === undefined) {
        screenStateCurrent.textContent = `当前状态：${state}`;
      } else {
        screenStateCurrent.textContent = `当前状态：${state}，退出码：${result.exit_code}`;
      }
      screenStateStats.textContent = renderScreenStateStats(result.stats);
      screenStateCandidates.textContent = renderScreenStateCandidates(result.candidates);
      screenStateLog.textContent = `${result.stdout || ""}${result.stderr || ""}`;
      if (currentScriptDetailsPayload) {
        renderScriptDetails(currentScriptDetailsPayload);
      }
    }

    function renderScreenStateStats(stats) {
      const probeStats = stats || {};
      const rounds = probeStats.rounds || 0;
      const elapsed = probeStats.last_elapsed_ms === null || probeStats.last_elapsed_ms === undefined
        ? "无"
        : `${Number(probeStats.last_elapsed_ms).toFixed(2)}ms`;
      const matched = renderCountMap(probeStats.matched_counts);
      const skipped = renderCountMap(probeStats.skipped_counts);
      return `轮数：${rounds}；最近耗时：${elapsed}；命中次数：${matched}；跳过次数：${skipped}`;
    }

    function renderCountMap(counts) {
      if (!counts || Object.keys(counts).length === 0) {
        return "无";
      }
      return Object.entries(counts)
        .map(([name, count]) => `${name} ${count}`)
        .join("，");
    }

    function renderScreenStateCandidates(candidates) {
      const items = candidates || [];
      if (items.length === 0) {
        return "暂无候选结果";
      }
      return items.map((candidate) => {
        const elapsed = candidate.elapsed_ms === null || candidate.elapsed_ms === undefined
          ? "无"
          : `${Number(candidate.elapsed_ms).toFixed(2)}ms`;
        const confidence = formatConfidence(candidate.confidence);
        const bestConfidence = formatConfidence(candidate.best_confidence);
        const bestRect = formatRect(candidate.best_rect);
        return `${renderCandidateName(candidate)}：${renderCandidateStatus(candidate.status)}；耗时 ${elapsed}；置信度 ${confidence}；最佳置信度 ${bestConfidence}；最佳位置 ${bestRect}`;
      }).join("\n");
    }

    function formatRect(rect) {
      if (!rect) {
        return "无";
      }
      return `x=${rect.left},y=${rect.top},w=${rect.width},h=${rect.height}`;
    }

    function formatConfidence(confidence) {
      if (confidence === null || confidence === undefined) {
        return "无";
      }
      return Number(confidence).toFixed(3);
    }

    function renderCandidateName(candidate) {
      if (candidate.search_name) {
        return `${candidate.name} / ${candidate.search_name}`;
      }
      return candidate.name;
    }

    function renderCandidateStatus(status) {
      if (status === "matched") {
        return "命中";
      }
      if (status === "skipped") {
        return "跳过";
      }
      if (status === "missed") {
        return "未命中";
      }
      return "未知";
    }

    function useProbedScreenState() {
      if (!latestScreenState || latestScreenState === "未知") {
        statusEl.textContent = "没有可用探测状态";
        return;
      }
      dryRunScreenStateInput.value = latestScreenState;
      statusEl.textContent = `已使用探测状态：${latestScreenState}`;
    }

    function useScriptScreenState() {
      if (scriptStateDependencies.length === 0) {
        statusEl.textContent = "当前脚本没有状态依赖";
        return;
      }
      dryRunScreenStateInput.value = scriptStateDependencies[0];
      statusEl.textContent = `已使用脚本状态：${scriptStateDependencies[0]}`;
    }

    function scheduleScriptRunPoll() {
      if (scriptRunPollTimer) {
        window.clearTimeout(scriptRunPollTimer);
      }
      scriptRunPollTimer = window.setTimeout(pollScriptRun, 500);
    }

    async function pollScriptRun() {
      const response = await fetch("/api/script-run");
      const result = await response.json();
      renderScriptStatus(result);
      activeScriptRun = Boolean(result.running);
      setBusy(activeScriptRun);
      if (activeScriptRun) {
        scheduleScriptRunPoll();
      }
    }

    function scheduleScreenStateProbePoll() {
      if (screenStateProbePollTimer) {
        window.clearTimeout(screenStateProbePollTimer);
      }
      screenStateProbePollTimer = window.setTimeout(pollScreenStateProbe, 500);
    }

    async function pollScreenStateProbe() {
      const response = await fetch("/api/screen-state-probe");
      const result = await response.json();
      renderScreenStateStatus(result);
      activeScreenStateProbe = Boolean(result.running);
      setScreenStateBusy(activeScreenStateProbe);
      if (activeScreenStateProbe) {
        scheduleScreenStateProbePoll();
      }
    }

    async function loadScripts() {
      const response = await fetch("/api/scripts");
      const payload = await response.json();
      scriptSelect.innerHTML = "";
      for (const name of payload.scripts) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        scriptSelect.appendChild(option);
      }
      await loadScriptDetails();
    }

    async function loadScriptDetails() {
      if (!scriptSelect.value) {
        scriptDetails.textContent = "";
        currentScriptDetailsPayload = null;
        scriptStateDependencies = [];
        scriptImageDependencies = [];
        return;
      }
      const response = await fetch(`/api/script-details?name=${encodeURIComponent(scriptSelect.value)}`);
      const payload = await response.json();
      renderScriptDetails(payload);
    }

    function renderScriptDetails(payload) {
      currentScriptDetailsPayload = payload;
      scriptStateDependencies = [];
      scriptImageDependencies = [];
      if (payload.exit_code !== 0) {
        scriptDetails.textContent = payload.stderr || "脚本详情读取失败";
        return;
      }
      scriptStateDependencies = payload.state_dependencies || [];
      scriptImageDependencies = payload.image_dependencies || [];
      const lines = [`脚本：${payload.name}`, "步骤："];
      for (const step of payload.steps || []) {
        lines.push(`- ${step}`);
      }
      lines.push("状态决策：");
      if ((payload.state_decisions || []).length === 0) {
        lines.push("- 没有状态决策");
      } else {
        for (const decision of payload.state_decisions || []) {
          lines.push(`- 当状态为 ${decision.state}`);
          lines.push(`  ${renderStateDecisionPreview(decision)}`);
          lines.push(`  命中：${renderDecisionSteps(decision.matched_steps)}`);
          lines.push(`  未命中：${renderDecisionSteps(decision.unmatched_steps)}`);
        }
      }
      lines.push("依赖：");
      if ((payload.dependencies || []).length === 0) {
        lines.push("- 无");
      } else {
        for (const dependency of payload.dependencies || []) {
          lines.push(`- ${dependency}`);
        }
      }
      lines.push("依赖检查：");
      if ((payload.readiness || []).length === 0) {
        lines.push("- 无可检查依赖");
      } else {
        for (const item of payload.readiness || []) {
          lines.push(`- ${renderReadinessStatus(item.status)} ${item.label}：${item.message}`);
        }
      }
      scriptDetails.textContent = lines.join("\n");
    }

    function renderStateDecisionPreview(decision) {
      if (!latestScreenState || latestScreenState === "未知") {
        return "当前：未知";
      }
      if (latestScreenState === decision.state) {
        return "当前：命中";
      }
      return "当前：未命中";
    }

    function renderDecisionSteps(steps) {
      if (!steps || steps.length === 0) {
        return "无";
      }
      return steps.join("；");
    }

    function renderReadinessStatus(status) {
      if (status === "ok") {
        return "[OK]";
      }
      if (status === "missing") {
        return "[缺失]";
      }
      return "[未知]";
    }

    async function loadImageAssets() {
      const response = await fetch("/api/image-assets");
      const payload = await response.json();
      imageAssetFolder.textContent = payload.asset_folder || "assets";
      imageAssetSelect.innerHTML = "";
      for (const name of payload.assets || []) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        imageAssetSelect.appendChild(option);
      }
      setBusy(false);
    }

    async function loadScreenStateNames() {
      const response = await fetch("/api/screen-state-names");
      const payload = await response.json();
      screenStateSuggestions.innerHTML = "";
      for (const state of payload.states || []) {
        const option = document.createElement("option");
        option.value = state;
        screenStateSuggestions.appendChild(option);
      }
    }

    async function loadScreenStateConfigSummary() {
      const response = await fetch("/api/screen-state-config");
      const payload = await response.json();
      renderScreenStateConfigSummary(payload);
    }

    function renderScreenStateConfigSummary(payload) {
      if (payload.exit_code !== 0) {
        screenStateConfigSummary.textContent = payload.stderr || "状态识别配置读取失败";
        return;
      }
      const states = payload.states || [];
      if (states.length === 0) {
        screenStateConfigSummary.textContent = "未配置状态识别";
        return;
      }
      const lines = ["状态识别配置："];
      for (const state of states) {
        lines.push(`- ${state.state}`);
        for (const search of state.searches || []) {
          const confidence = search.min_confidence === null || search.min_confidence === undefined
            ? "默认"
            : search.min_confidence;
          lines.push(`  - ${search.name} / ${search.image} / ${search.region} / ${confidence}`);
        }
      }
      screenStateConfigSummary.textContent = lines.join("\n");
    }

    async function runScript() {
      activeScriptRun = true;
      setBusy(true);
      statusEl.textContent = "正在运行脚本...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/run-script", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            name: scriptSelect.value,
            dry_run: dryRunCheckbox.checked,
            dry_run_color: colorInput.value,
            dry_run_screen_state: dryRunScreenStateInput.value,
            dry_run_images: scriptImageDependencies
          })
        });
        const result = await response.json();
        renderScriptStatus(result);
        activeScriptRun = Boolean(result.running);
        setBusy(activeScriptRun);
        if (activeScriptRun) {
          scheduleScriptRunPoll();
        }
      } finally {
        setBusy(activeScriptRun);
      }
    }

    async function stopScript() {
      statusEl.textContent = "正在停止脚本...";
      try {
        const response = await fetch("/api/stop-script", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        const result = await response.json();
        renderScriptStatus(result);
        activeScriptRun = Boolean(result.running);
        setBusy(activeScriptRun);
        if (activeScriptRun) {
          scheduleScriptRunPoll();
        }
      } finally {
        stopScriptButton.disabled = !activeScriptRun;
      }
    }

    async function runTests() {
      setBusy(true);
      statusEl.textContent = "正在运行测试...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/run-tests", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({task: "all"})
        });
        renderResult("测试", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function clickImage() {
      setBusy(true);
      statusEl.textContent = "正在查找图片...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/click-image", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            asset: imageAssetSelect.value,
            dry_run: dryRunCheckbox.checked,
            min_confidence: Number.parseFloat(imageConfidenceInput.value)
          })
        });
        renderResult("图片点击", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function captureScreen() {
      setBusy(true);
      statusEl.textContent = "正在截屏...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/capture-screen", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        renderResult("截屏诊断", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function captureRegionDiagnostics() {
      setBusy(true);
      statusEl.textContent = "正在生成区域诊断...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/capture-region-diagnostics", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        renderResult("区域诊断", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function captureProbeDiagnostics() {
      setBusy(true);
      statusEl.textContent = "正在生成探测诊断...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/capture-probe-diagnostics", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            min_confidence: Number.parseFloat(screenStateConfidenceInput.value)
          })
        });
        renderResult("探测诊断", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function captureRegionCrops() {
      setBusy(true);
      statusEl.textContent = "正在导出区域裁剪...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/capture-region-crops", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        renderResult("区域裁剪", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function captureProbeCrops() {
      setBusy(true);
      statusEl.textContent = "正在导出候选裁剪...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/capture-probe-crops", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            min_confidence: Number.parseFloat(screenStateConfidenceInput.value)
          })
        });
        renderResult("候选裁剪", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function startScreenStateProbe() {
      activeScreenStateProbe = true;
      setScreenStateBusy(true);
      screenStateCurrent.textContent = "当前状态：启动中";
      screenStateStats.textContent = "";
      screenStateLog.textContent = "";
      try {
        const response = await fetch("/api/start-screen-state-probe", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            min_confidence: Number.parseFloat(screenStateConfidenceInput.value),
            interval_seconds: Number.parseFloat(screenStateIntervalInput.value)
          })
        });
        const result = await response.json();
        renderScreenStateStatus(result);
        activeScreenStateProbe = Boolean(result.running);
        setScreenStateBusy(activeScreenStateProbe);
        if (activeScreenStateProbe) {
          scheduleScreenStateProbePoll();
        }
      } finally {
        setScreenStateBusy(activeScreenStateProbe);
      }
    }

    async function stopScreenStateProbe() {
      screenStateCurrent.textContent = "当前状态：正在停止";
      try {
        const response = await fetch("/api/stop-screen-state-probe", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        const result = await response.json();
        renderScreenStateStatus(result);
        activeScreenStateProbe = Boolean(result.running);
        setScreenStateBusy(activeScreenStateProbe);
        if (activeScreenStateProbe) {
          scheduleScreenStateProbePoll();
        }
      } finally {
        stopScreenStateProbeButton.disabled = !activeScreenStateProbe;
      }
    }

    setupTabs();
    runScriptButton.addEventListener("click", runScript);
    stopScriptButton.addEventListener("click", stopScript);
    scriptSelect.addEventListener("change", loadScriptDetails);
    useProbedScreenStateButton.addEventListener("click", useProbedScreenState);
    useScriptScreenStateButton.addEventListener("click", useScriptScreenState);
    runTestsButton.addEventListener("click", runTests);
    refreshImagesButton.addEventListener("click", loadImageAssets);
    captureScreenButton.addEventListener("click", captureScreen);
    captureRegionDiagnosticsButton.addEventListener("click", captureRegionDiagnostics);
    captureProbeDiagnosticsButton.addEventListener("click", captureProbeDiagnostics);
    captureRegionCropsButton.addEventListener("click", captureRegionCrops);
    captureProbeCropsButton.addEventListener("click", captureProbeCrops);
    clickImageButton.addEventListener("click", clickImage);
    startScreenStateProbeButton.addEventListener("click", startScreenStateProbe);
    stopScreenStateProbeButton.addEventListener("click", stopScreenStateProbe);
    loadScripts();
    loadImageAssets();
    loadScreenStateNames();
    loadScreenStateConfigSummary();
