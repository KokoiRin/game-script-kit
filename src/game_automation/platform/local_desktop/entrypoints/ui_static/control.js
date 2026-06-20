    const tabButtons = document.querySelectorAll(".tab-button");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const scriptSelect = document.querySelector("#script-select");
    const dryRunCheckbox = document.querySelector("#dry-run-enabled");
    const colorInput = document.querySelector("#dry-run-color");
    const dryRunScreenStateInput = document.querySelector("#dry-run-screen-state");
    const screenStateSuggestions = document.querySelector("#screen-state-suggestions");
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
    const imageConfidenceInput = document.querySelector("#image-confidence");
    const debugPreview = document.querySelector("#debug-preview");
    const debugScreenshot = document.querySelector("#debug-screenshot");
    const screenStateConfidenceInput = document.querySelector("#screen-state-confidence");
    const screenStateIntervalInput = document.querySelector("#screen-state-interval");
    const screenStateCurrent = document.querySelector("#screen-state-current");
    const screenStateLog = document.querySelector("#screen-state-log");
    const startScreenStateProbeButton = document.querySelector("#start-screen-state-probe");
    const stopScreenStateProbeButton = document.querySelector("#stop-screen-state-probe");
    let scriptRunPollTimer = null;
    let activeScriptRun = false;
    let screenStateProbePollTimer = null;
    let activeScreenStateProbe = false;

    function setBusy(isBusy) {
      runScriptButton.disabled = isBusy;
      runTestsButton.disabled = isBusy;
      refreshImagesButton.disabled = isBusy;
      captureScreenButton.disabled = isBusy;
      captureRegionDiagnosticsButton.disabled = isBusy;
      clickImageButton.disabled = isBusy || !imageAssetSelect.value;
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
      if (result.running) {
        screenStateCurrent.textContent = `当前状态：${state}（探测中）`;
      } else if (result.exit_code === null || result.exit_code === undefined) {
        screenStateCurrent.textContent = `当前状态：${state}`;
      } else {
        screenStateCurrent.textContent = `当前状态：${state}，退出码：${result.exit_code}`;
      }
      screenStateLog.textContent = `${result.stdout || ""}${result.stderr || ""}`;
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
            dry_run_screen_state: dryRunScreenStateInput.value
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

    async function startScreenStateProbe() {
      activeScreenStateProbe = true;
      setScreenStateBusy(true);
      screenStateCurrent.textContent = "当前状态：启动中";
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
    runTestsButton.addEventListener("click", runTests);
    refreshImagesButton.addEventListener("click", loadImageAssets);
    captureScreenButton.addEventListener("click", captureScreen);
    captureRegionDiagnosticsButton.addEventListener("click", captureRegionDiagnostics);
    clickImageButton.addEventListener("click", clickImage);
    startScreenStateProbeButton.addEventListener("click", startScreenStateProbe);
    stopScreenStateProbeButton.addEventListener("click", stopScreenStateProbe);
    loadScripts();
    loadImageAssets();
    loadScreenStateNames();
