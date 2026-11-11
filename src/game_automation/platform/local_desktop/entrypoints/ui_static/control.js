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
  const historySelect = document.querySelector("#history-select");
  const historySummary = document.querySelector("#history-summary");
  const historyOutput = document.querySelector("#history-output");
  const historyError = document.querySelector("#history-error");
  const historyDownload = document.querySelector("#download-history");
  const historyPanel = document.querySelector("#run-history-panel");
  const reasons = {
    completed: "脚本执行完成", stopped_unmet_condition: "条件未满足，已停止后续步骤",
    cancelled: "已取消", timed_out: "等待超时", failed: "运行失败",
    setup_failed: "运行环境不可用", configuration_failed: "配置错误",
    script_not_found: "脚本不存在", idle: "脚本未运行",
    unfinished: "尚无结束记录（运行中或服务曾退出）",
  };
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
  let historyVersion = 0;
  let historyLoaded = false;
  let historyListVersion = 0;

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
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      return result;
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
      const wasRunning = activeRun;
      renderStatus(result);
      if (!historyLoaded || (wasRunning && !activeRun)) await loadHistory();
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

  function historyTime(value) {
    return value ? new Date(value).toLocaleString("zh-CN", {hour12: false}) : "原时间未知";
  }

  async function loadHistory() {
    const version = ++historyListVersion;
    try {
      const result = await request("/api/run-history");
      if (version !== historyListVersion) return;
      const selected = historySelect.value;
      historySelect.replaceChildren();
      for (const item of result.runs || []) {
        const option = document.createElement("option");
        option.value = item.id;
        const reason = item.running ? "运行中" : reasons[item.finish_reason] || item.finish_reason;
        option.textContent = `${historyTime(item.started_at)} · ${item.name} · ${item.dry_run ? "模拟" : "真实"} · ${reason}`;
        historySelect.append(option);
      }
      if ([...historySelect.options].some(option => option.value === selected)) historySelect.value = selected;
      historyLoaded = true;
      historyError.hidden = true;
      if (historySelect.value && historyPanel.open) await loadHistoryRun();
      else if (historySelect.value) historyDownload.hidden = true;
      else {
        historySelect.add(new Option("暂无保存的运行记录", ""));
        historyOutput.textContent = "暂无保存的运行记录。";
        historySummary.textContent = "";
        historyDownload.hidden = true;
      }
    } catch (error) {
      if (version !== historyListVersion) return;
      historyError.textContent = `历史记录读取失败：${error.message}。可点击刷新重试。`;
      historyError.hidden = false;
    }
  }

  async function loadHistoryRun() {
    const version = ++historyVersion;
    const id = historySelect.value;
    historyDownload.hidden = true;
    if (!id) return;
    historyOutput.textContent = "正在读取日志…";
    try {
      const result = await request(`/api/run-history?id=${encodeURIComponent(id)}`);
      if (version !== historyVersion) return;
      const item = result.summary;
      historySummary.textContent = [
        `结果：${reasons[item.finish_reason] || item.finish_reason} · 退出码 ${item.exit_code ?? "未知"}`,
        `开始：${historyTime(item.started_at)} · 结束：${item.ended_at ? historyTime(item.ended_at) : item.source === "recovered" ? "原时间未知" : "尚未记录"}`,
        item.source === "recovered" ? "从旧服务抢救的日志，原始时间未知。" : "",
        item.last_step ? `最后步骤：${item.last_step}` : "",
        item.error ? `提示与错误：${item.error.trim()}` : "",
      ].filter(Boolean).join("\n");
      const lines = (result.records || []).flatMap(record => {
        const time = record.recorded_at ? historyTime(record.recorded_at) : "时间未知";
        if (record.kind === "event") {
          const e = record.data;
          return [`[${time}] ${e.type} ${e.path || ""} ${e.step || ""} ${e.status || ""} ${JSON.stringify(e.details || {})}`];
        }
        return String(typeof record.data === "string" ? record.data : JSON.stringify(record.data))
          .split("\n").filter(Boolean).map(line => `[${time}] ${record.kind}: ${line}`);
      });
      historyOutput.textContent = (lines.length > 300 ? "（显示最后 300 行，完整记录可下载）\n" : "") + lines.slice(-300).join("\n");
      historyDownload.href = `/api/run-history?id=${encodeURIComponent(id)}&download=1`;
      historyDownload.hidden = false;
      historyError.hidden = true;
    } catch (error) {
      if (version !== historyVersion) return;
      historyError.textContent = `日志读取失败：${error.message}`;
      historyError.hidden = false;
      historyOutput.textContent = "日志暂不可用。";
      historySummary.textContent = "";
    }
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
      loadHistory();
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
  historySelect.addEventListener("change", loadHistoryRun);
  historyPanel.addEventListener("toggle", () => { if (historyPanel.open) loadHistoryRun(); });
  document.querySelector("#refresh-history").addEventListener("click", loadHistory);
  syncControls();
  loadStateNames();
  pollStatus();
})();
