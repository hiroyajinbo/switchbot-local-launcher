const buttonList = document.querySelector("#buttonList");
const resultMessage = document.querySelector("#resultMessage");
const resultTime = document.querySelector("#resultTime");
const statusBadge = document.querySelector("#statusBadge");

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || "通信に失敗しました。");
  }
  return body;
}

function setStatus(ok, message) {
  statusBadge.textContent = message;
  statusBadge.classList.toggle("ok", ok);
  statusBadge.classList.toggle("error", !ok);
}

function setResult(message, time = "", isError = false) {
  resultMessage.textContent = message;
  resultMessage.classList.toggle("error", isError);
  resultTime.textContent = time;
}

function setBusy(isBusy) {
  document.querySelectorAll(".action-button").forEach((button) => {
    button.disabled = isBusy;
  });
}

async function executeAction(button) {
  setBusy(true);
  setResult(`${button.label} 実行中...`);
  try {
    const result = await requestJson(`/api/actions/${button.id}`, { method: "POST" });
    setResult(result.message, result.executed_at);
  } catch (error) {
    setResult(error.message, new Date().toLocaleString("ja-JP"), true);
  } finally {
    setBusy(false);
  }
}

function renderButtons(buttons) {
  buttonList.replaceChildren();
  buttons.forEach((button) => {
    const element = document.createElement("button");
    element.className = "action-button";
    element.type = "button";
    element.textContent = button.label;
    element.addEventListener("click", () => executeAction(button));
    buttonList.append(element);
  });
}

async function boot() {
  try {
    const health = await requestJson("/api/health");
    if (!health.ok) {
      throw new Error(health.error || "初期化に失敗しました。");
    }
    const data = await requestJson("/api/buttons");
    renderButtons(data.buttons);
    setStatus(true, "準備完了");
  } catch (error) {
    setStatus(false, "要確認");
    setResult(error.message, "", true);
  }
}

boot();
