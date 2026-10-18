(() => {
  "use strict";
  const scriptSelect = document.querySelector("#script-select");
  const runButton = document.querySelector("#run-script");
  const stopButton = document.querySelector("#stop-script");
  const dryRun = document.querySelector("#dry-run-enabled");
  const colorInput = document.querySelector("#dry-run-color");
  const stateInput = document.querySelector("#dry-run-screen-state");
  const settings = document.querySelector("#simulation-settings");
  const modeBadge = document.querySelector("#run-mode");
  const modeDescription = document.querySelector("#mode-description");
  const statusEl = document.querySelector("#status");
  const outputEl = document.querySelector("#output");
  const detailsEl = document.querySelector("#script-details");
  const configErrors = document.querySelector("#script-config-errors");
  const connectionEl = document.querySelector("#connection-status");
  const connectionError = document.querySelector("#connection-error");
  const workspaceEl = document.querySelector("#workspace-path");
  let activeRun = false;
  let requestPending = false;
  let connectionLost = true;
  let scriptsLoaded = false;
  let loadingDetails = false;
  let currentDetails = null;
  let detailsVersion = 0;
  let activeMode = null;
  let pollTimer = null;
  let statusVersion = 0;

  async function request(path, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(path, {
        method: body === undefined ? "GET" : "POST",
        headers: body === undefined ? {} : {"Content-Type": "application/json"},
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  function syncControls() {
    const locked = activeRun || requestPending || connectionLost;
    scriptSelect.disabled = locked || !scriptsLoaded;
    dryRun.disabled = locked;
    colorInput.disabled = locked || !dryRun.checked;
    stateInput.disabled = locked || !dryRun.checked;
    runButton.disabled = locked || loadingDetails || !currentDetails || !scriptSelect.value;
    stopButton.disabled = !activeRun || requestPending;
    settings.hidden = !dryRun.checked;
    const simulated = activeRun ? activeMode : dryRun.checked;
    modeBadge.textContent = simulated === null ? "运行中" : simulated ? "模拟模式" : "真实模式";
    modeBadge.dataset.real = String(simulated === false);
    modeDescription.textContent = simulated === null
      ? "已有脚本正在运行，可停止或等待任务结束。"
      : simulated === false
      ? "真实运行会控制当前桌面的鼠标和键盘，可随时停止。"
      : "只输出计划动作；图片依赖在模拟中视为已找到。";
  }

  function showConnectionError(message) {
    connectionLost = true;
    connectionEl.textContent = "连接中断 · 自动重试";
    connectionEl.dataset.connected = "false";
    connectionError.textContent = message;
    connectionError.hidden = false;
    syncControls();
  }

  function renderStatus(result) {
    activeRun = Boolean(result.running);
    const started = (result.events || []).find(event => event.type === "run_started");
    if (started && started.details && started.details.dry_run !== undefined) {
      activeMode = started.details.dry_run === true || started.details.dry_run === "True";
    }
    const reasons = {
      completed: "脚本执行完成",
      stopped_unmet_condition: "条件未满足，已停止后续步骤",
      cancelled: "已取消",
      timed_out: "等待超时",
      failed: "运行失败",
      setup_failed: "运行环境不可用",
      configuration_failed: "配置错误",
      script_not_found: "脚本不存在",
      idle: "脚本未运行",
    };
    if (activeRun) {
      statusEl.textContent = activeMode === null ? "脚本运行中…" : activeMode ? "模拟运行中…" : "真实运行中…";
    } else {
      const reason = reasons[result.finish_reason] || result.finish_reason || "脚本未运行";
      statusEl.textContent = result.exit_code == null ? reason : `${reason} · 退出码 ${result.exit_code}`;
    }
    statusEl.dataset.result = activeRun ? "running" : result.finish_reason || "idle";
    // 结构化步骤事件已由状态展示，日志区只保留动作和识别结果。
    const logs = [(result.stdout || "").split("\n")
      .filter(line => !line.startsWith("script event ")).join("\n")];
    if (result.stderr) logs.push(`提示与错误：\n${result.stderr}`);
    const output = logs.filter(Boolean).join("\n");
    const nearBottom = outputEl.scrollHeight - outputEl.scrollTop - outputEl.clientHeight < 60;
    outputEl.textContent = output || "还没有运行记录。";
    if (nearBottom) outputEl.scrollTop = outputEl.scrollHeight;
    syncControls();
  }

  function schedulePoll(delay = 1000) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(pollStatus, delay);
  }

  async function pollStatus() {
    if (requestPending) {
      schedulePoll();
      return;
    }
    const version = statusVersion;
    try {
      const result = await request("/api/script-run");
      if (requestPending || version !== statusVersion) return;
      connectionLost = false;
      connectionEl.textContent = "本地服务已连接";
      connectionEl.dataset.connected = "true";
      connectionError.hidden = true;
      renderStatus(result);
      if (!scriptsLoaded) await loadScripts();
      else if (!currentDetails && !loadingDetails && scriptSelect.value) await loadScriptDetails();
    } catch (error) {
      showConnectionError(`无法读取运行状态（${error.message}），正在自动重试。连接恢复前不会启动新脚本。`);
    } finally {
      schedulePoll(connectionLost ? 2000 : 1000);
    }
  }

  async function loadScripts() {
    const [result, workspace] = await Promise.all([
      request("/api/scripts"), request("/api/workspace"),
    ]);
    workspaceEl.textContent = `工作区：${workspace.path}`;
    scriptSelect.replaceChildren();
    for (const name of result.scripts || []) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      scriptSelect.append(option);
    }
    scriptsLoaded = true;
    const errors = result.script_config_errors || [];
    configErrors.textContent = errors.map(error => `${error.file}：${error.message}`).join("\n");
    configErrors.hidden = errors.length === 0;
    if (!scriptSelect.value) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "暂无可运行脚本";
      scriptSelect.append(option);
      detailsEl.textContent = "在当前工作区的 scripts/ 目录添加脚本后重启控制台。";
    } else {
      await loadScriptDetails();
    }
    syncControls();
  }

  async function loadScriptDetails() {
    const version = ++detailsVersion;
    currentDetails = null;
    loadingDetails = true;
    syncControls();
    try {
      const result = await request(`/api/script-details?name=${encodeURIComponent(scriptSelect.value)}`);
      if (version !== detailsVersion) return;
      if (result.exit_code !== 0) {
        detailsEl.textContent = result.stderr || "脚本详情不可用";
        return;
      }
      currentDetails = result;
      const lines = [`脚本：${result.name}`, "", "步骤：", ...(result.steps || []).map(step => `  ${step}`)];
      if ((result.readiness || []).length) {
        lines.push("", "依赖检查：", ...result.readiness.map(item => `${item.status === "ok" ? "✓" : "!"} ${item.label}：${item.message}`));
      }
      detailsEl.textContent = lines.join("\n");
    } catch (error) {
      if (version === detailsVersion) detailsEl.textContent = `详情读取失败（${error.message}），正在自动重试。`;
    } finally {
      if (version === detailsVersion) {
        loadingDetails = false;
        syncControls();
      }
    }
  }

  async function runScript() {
    if (runButton.disabled || requestPending || activeRun) return;
    if (dryRun.checked && !/^#[0-9A-Fa-f]{6}$/.test(colorInput.value)) {
      settings.open = true;
      colorInput.reportValidity();
      colorInput.focus();
      return;
    }
    requestPending = true;
    statusVersion += 1;
    activeMode = dryRun.checked;
    clearTimeout(pollTimer);
    syncControls();
    statusEl.textContent = activeMode ? "正在启动模拟运行…" : "正在启动真实运行…";
    try {
      renderStatus(await request("/api/run-script", {
        name: scriptSelect.value,
        dry_run: dryRun.checked,
        dry_run_color: colorInput.value,
        dry_run_screen_state: stateInput.value || "未知",
        dry_run_images: currentDetails.image_dependencies || [],
      }));
    } catch (error) {
      // POST 可能已到达服务；只查询结果，避免重试造成重复执行。
      activeRun = true;
      showConnectionError(`运行请求未收到结果（${error.message}），正在重新确认状态。`);
    } finally {
      requestPending = false;
      syncControls();
      schedulePoll(100);
    }
  }

  async function stopScript() {
    if (stopButton.disabled || requestPending) return;
    requestPending = true;
    statusVersion += 1;
    clearTimeout(pollTimer);
    syncControls();
    statusEl.textContent = "正在请求停止…";
    try {
      const result = await request("/api/stop-script", {});
      renderStatus(result);
      if (result.running) statusEl.textContent = "已请求停止，等待当前动作结束…";
    } catch (error) {
      showConnectionError(`停止请求未收到结果（${error.message}），正在重新确认状态。`);
    } finally {
      requestPending = false;
      syncControls();
      schedulePoll(100);
    }
  }

  async function loadStateNames() {
    try {
      const result = await request("/api/screen-state-names");
      const suggestions = document.querySelector("#screen-state-suggestions");
      for (const state of result.states || []) {
        const option = document.createElement("option");
        option.value = state;
        suggestions.append(option);
      }
    } catch {
      // 状态建议仅辅助填写，失败时仍可手动输入模拟状态。
    }
  }

  runButton.addEventListener("click", runScript);
  stopButton.addEventListener("click", stopScript);
  scriptSelect.addEventListener("change", loadScriptDetails);
  dryRun.addEventListener("change", syncControls);
  syncControls();
  loadStateNames();
  pollStatus();
})();
