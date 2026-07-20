const API_BASE = "http://127.0.0.1:8765";
const quickActions = document.querySelector("#quickActions");
const refreshButton = document.querySelector("#refreshButton");
const openAppButton = document.querySelector("#openAppButton");
const statusMessage = document.querySelector("#statusMessage");

const iconSymbols = {
  scene: "◎", light: "💡", strip_light: "▬", plug: "⌁", bot: "◉",
  lock: "🔒", climate: "❄", fan: "◉", monitor: "▣", game: "🎮",
  computer: "▰", bath: "♨", kettle: "♨", door: "▯", curtain: "▥",
  speaker: "◖", tv: "▣", appliance: "◇", other: "○",
};

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "操作に失敗しました。");
  return body;
}

function setStatus(message, type = "") {
  statusMessage.textContent = message;
  statusMessage.className = type;
}

function showUnavailable() {
  quickActions.replaceChildren();
  const message = document.createElement("p");
  message.className = "message error";
  message.textContent = "PCアプリが起動していません。SwitchBot Local Launcherを起動してから再読み込みしてください。";
  quickActions.append(message);
  setStatus("PCアプリ未接続", "error");
}

function renderButtons(buttons) {
  const visible = buttons.filter((button) => ["scene", "remote_command"].includes(button.type));
  const groups = new Map();
  visible.forEach((button) => {
    const group = button.group || "その他";
    groups.set(group, [...(groups.get(group) || []), button]);
  });
  quickActions.replaceChildren();
  if (visible.length === 0) {
    const message = document.createElement("p");
    message.className = "message";
    message.textContent = "登録済みのクイック操作はありません。";
    quickActions.append(message);
    return;
  }
  groups.forEach((buttonsInGroup, groupName) => {
    const section = document.createElement("section");
    section.className = "group";
    const heading = document.createElement("h2");
    heading.textContent = groupName;
    const list = document.createElement("div");
    list.className = "action-list";
    buttonsInGroup.forEach((button) => list.append(actionButton(button)));
    section.append(heading, list);
    quickActions.append(section);
  });
}

function actionButton(button) {
  const element = document.createElement("button");
  element.type = "button";
  element.className = "action-button";
  element.disabled = button.locked;
  const icon = document.createElement("span");
  icon.className = "action-icon";
  icon.textContent = iconSymbols[button.icon] || iconSymbols.other;
  const label = document.createElement("span");
  label.className = "action-label";
  label.textContent = button.label;
  const state = document.createElement("span");
  state.className = "action-state";
  state.textContent = button.locked ? "ロック中" : "";
  element.append(icon, label, state);
  element.addEventListener("click", () => executeAction(button, element, state));
  return element;
}

async function executeAction(button, element, state) {
  element.disabled = true;
  state.textContent = "実行中…";
  setStatus(`${button.label} を実行中…`);
  try {
    const result = await requestJson(`/api/actions/${encodeURIComponent(button.id)}`, {
      method: "POST",
    });
    state.textContent = "成功";
    setStatus(result.message, "success");
  } catch (error) {
    state.textContent = "失敗";
    setStatus(error.message, "error");
  } finally {
    element.disabled = button.locked;
  }
}

async function loadButtons() {
  refreshButton.disabled = true;
  setStatus("接続確認中");
  try {
    const health = await requestJson("/api/health");
    if (!health.ok) throw new Error(health.error || "PCアプリを初期化できませんでした。");
    const data = await requestJson("/api/buttons");
    renderButtons(data.buttons || []);
    setStatus("PCアプリ接続済み", "success");
  } catch (_error) {
    showUnavailable();
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadButtons);
openAppButton.addEventListener("click", () => chrome.tabs.create({ url: `${API_BASE}/` }));
loadButtons();
