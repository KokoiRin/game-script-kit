const app = document.querySelector("#lab-app");
const modeBadge = document.querySelector("#mode-badge");
const sequenceBadge = document.querySelector("#sequence-badge");
const truthStatus = document.querySelector("#truth-status");

let lastSequence = -1;

async function requestState() {
  const response = await fetch("/api/state");
  if (!response.ok) {
    throw new Error(`state request failed: ${response.status}`);
  }
  return response.json();
}

async function performAction(action) {
  const response = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `action failed: ${response.status}`);
  }
  render(payload);
}

function actionButton(action, image, label) {
  const button = document.createElement("button");
  button.className = "visual-action";
  button.dataset.action = action;
  button.innerHTML = `
    <img class="pixel-template" src="/static/images/${image}" alt="">
    <strong>${label}</strong>
  `;
  button.addEventListener("click", () => performAction(action).catch(renderError));
  fitTemplateImages(button);
  return button;
}

function panel(title, description) {
  const element = document.createElement("article");
  element.className = "lab-panel";
  element.innerHTML = `<h2>${title}</h2><p>${description}</p>`;
  return element;
}

function render(state) {
  modeBadge.textContent = `模式：${state.mode}`;
  sequenceBadge.textContent = `事件：${state.sequence}`;
  truthStatus.textContent = `真值接口：${state.state}`;
  if (state.sequence === lastSequence) {
    return;
  }
  lastSequence = state.sequence;
  const views = {
    home: renderHome,
    task_list: () => renderTaskList(state),
    loading: renderLoading,
    confirm: renderConfirm,
    completed: renderCompleted,
  };
  const view = views[state.state];
  if (!view) {
    renderError(new Error(`unknown state: ${state.state}`));
    return;
  }
  view();
}

function renderHome() {
  const content = panel("准备开始", "打开任务列表，寻找今天需要处理的目标任务。");
  content.append(actionButton("open_tasks", "open-tasks.png", "打开任务列表"));
  app.replaceChildren(content);
}

function renderTaskList(state) {
  const content = panel("任务列表", "目标任务的位置固定，但它可能被故障模式移除。");
  if (state.available_actions.includes("select_target")) {
    content.append(actionButton("select_target", "target-task.png", "处理目标任务"));
  } else {
    const missing = document.createElement("div");
    missing.className = "lab-empty";
    missing.textContent = "目标任务当前不可用";
    content.append(missing);
  }
  app.replaceChildren(content);
}

function renderLoading() {
  const content = panel("正在加载", "请等待目标任务准备完成，不要提前点击。");
  content.insertBefore(stateImage("loading.png", "加载中"), content.firstChild);
  app.replaceChildren(content);
}

function renderConfirm() {
  const content = panel("确认执行", "任务已准备完成，确认后会进入最终完成状态。");
  content.append(actionButton("confirm_task", "confirm-task.png", "确认执行"));
  app.replaceChildren(content);
}

function renderCompleted() {
  const content = panel("处理完成", "靶场已经记录完整动作链，可以通过真值接口验收。");
  content.insertBefore(stateImage("completed.png", "已完成"), content.firstChild);
  app.replaceChildren(content);
}

function stateImage(image, label) {
  const wrapper = document.createElement("div");
  wrapper.className = "lab-state-image";
  wrapper.innerHTML = `<img class="pixel-template" src="/static/images/${image}" alt="${label}">`;
  fitTemplateImages(wrapper);
  return wrapper;
}

function fitTemplateImages(root) {
  for (const image of root.querySelectorAll(".pixel-template")) {
    const fit = () => {
      image.style.width = `${image.naturalWidth / window.devicePixelRatio}px`;
      image.style.height = `${image.naturalHeight / window.devicePixelRatio}px`;
    };
    if (image.complete) {
      fit();
    } else {
      image.addEventListener("load", fit, { once: true });
    }
  }
}

function renderError(error) {
  app.innerHTML = `<p class="lab-error">靶场连接失败：${error.message}</p>`;
  truthStatus.textContent = "真值接口：连接失败";
}

async function refresh() {
  try {
    render(await requestState());
  } catch (error) {
    renderError(error);
  }
}

refresh();
window.setInterval(refresh, 120);
