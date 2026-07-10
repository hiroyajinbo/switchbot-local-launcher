const buttonList = document.querySelector("#buttonList");
const deviceStatusList = document.querySelector("#deviceStatusList");
const environmentList = document.querySelector("#environmentList");
const refreshStatusButton = document.querySelector("#refreshStatusButton");
const remoteList = document.querySelector("#remoteList");
const resultMessage = document.querySelector("#resultMessage");
const resultTime = document.querySelector("#resultTime");
const statusBadge = document.querySelector("#statusBadge");
const statusCheckedAt = document.querySelector("#statusCheckedAt");

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

function renderStatus(snapshot) {
  statusCheckedAt.textContent = `更新: ${snapshot.checked_at}`;
  renderEnvironment(snapshot.environment || []);
  renderDevices(snapshot.devices || [], snapshot.errors || []);
  renderRemotes(snapshot.remotes || []);
}

function renderEnvironment(items) {
  environmentList.replaceChildren();
  if (items.length === 0) {
    environmentList.append(emptyText("環境データは見つかりませんでした。"));
    return;
  }

  items.forEach((item) => {
    const element = document.createElement("div");
    element.className = "environment-card";

    const title = document.createElement("div");
    title.className = "environment-title";
    title.textContent = item.label;

    const values = document.createElement("div");
    values.className = "environment-values";
    item.details.forEach((detail) => {
      if (!["temperature", "humidity", "lightLevel"].includes(detail.key)) {
        return;
      }
      const value = document.createElement("div");
      value.className = "metric";
      value.textContent = formatDetail(detail);
      values.append(value);
    });

    element.append(title, values);
    environmentList.append(element);
  });
}

function renderDevices(items, errors) {
  deviceStatusList.replaceChildren();
  if (items.length === 0 && errors.length === 0) {
    deviceStatusList.append(emptyText("状態データは見つかりませんでした。"));
    return;
  }

  items.forEach((item) => {
    const element = document.createElement("div");
    element.className = "device-row";
    element.append(deviceMain(item.label, item.type, item.summary), detailList(item.details));
    deviceStatusList.append(element);
  });

  errors.forEach((error) => {
    const element = document.createElement("div");
    element.className = "device-row error-row";
    element.append(deviceMain(error.label, "取得不可", error.message));
    deviceStatusList.append(element);
  });
}

function renderRemotes(items) {
  remoteList.replaceChildren();
  if (items.length === 0) {
    remoteList.append(emptyText("赤外線リモコンは見つかりませんでした。"));
    return;
  }

  items.forEach((item) => {
    const element = document.createElement("div");
    element.className = "device-row muted-row";
    element.append(deviceMain(item.label, item.type, item.summary), remoteDetails(item));
    remoteList.append(element);
  });
}

function remoteDetails(item) {
  const wrapper = document.createElement("div");
  wrapper.className = "device-details";
  if (item.hub_device_id) {
    const pill = document.createElement("span");
    pill.className = "detail-pill";
    pill.textContent = `Hub: ${item.hub_device_id}`;
    wrapper.append(pill);
  }
  return wrapper;
}

function deviceMain(label, type, summary) {
  const wrapper = document.createElement("div");
  wrapper.className = "device-main";

  const name = document.createElement("div");
  name.className = "device-name";
  name.textContent = label;

  const meta = document.createElement("div");
  meta.className = "device-meta";
  meta.textContent = `${type} / ${summary}`;

  wrapper.append(name, meta);
  return wrapper;
}

function detailList(details) {
  const wrapper = document.createElement("div");
  wrapper.className = "device-details";
  details.slice(0, 4).forEach((detail) => {
    const pill = document.createElement("span");
    pill.className = "detail-pill";
    pill.textContent = formatDetail(detail);
    wrapper.append(pill);
  });
  return wrapper;
}

function formatDetail(detail) {
  const labels = {
    battery: "電池",
    brightness: "明るさ",
    colorTemperature: "色温度",
    deviceMode: "モード",
    doorState: "ドア",
    electricCurrent: "電流",
    electricityOfDay: "本日電力",
    humidity: "湿度",
    lightLevel: "照度",
    lockState: "鍵",
    moveDetected: "動き",
    openState: "開閉",
    power: "電源",
    temperature: "気温",
    voltage: "電圧",
  };
  const suffixes = {
    battery: "%",
    colorTemperature: "K",
    humidity: "%",
    temperature: "℃",
    voltage: "V",
  };
  const label = labels[detail.key] || detail.key;
  const suffix = suffixes[detail.key] || "";
  return `${label}: ${detail.value}${suffix}`;
}

function emptyText(message) {
  const element = document.createElement("div");
  element.className = "empty-text";
  element.textContent = message;
  return element;
}

async function refreshStatus() {
  refreshStatusButton.disabled = true;
  try {
    const snapshot = await requestJson("/api/status");
    renderStatus(snapshot);
  } catch (error) {
    environmentList.replaceChildren(emptyText(error.message));
    deviceStatusList.replaceChildren(emptyText("状態を取得できませんでした。"));
    remoteList.replaceChildren(emptyText("赤外線リモコンを取得できませんでした。"));
  } finally {
    refreshStatusButton.disabled = false;
  }
}

async function boot() {
  try {
    const health = await requestJson("/api/health");
    if (!health.ok) {
      throw new Error(health.error || "初期化に失敗しました。");
    }
    const data = await requestJson("/api/buttons");
    renderButtons(data.buttons);
    await refreshStatus();
    setStatus(true, "準備完了");
  } catch (error) {
    setStatus(false, "要確認");
    setResult(error.message, "", true);
  }
}

refreshStatusButton.addEventListener("click", refreshStatus);
boot();
