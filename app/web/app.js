const buttonList = document.querySelector("#buttonList");
const applyCandidatesButton = document.querySelector("#applyCandidatesButton");
const addRoomButton = document.querySelector("#addRoomButton");
const candidateList = document.querySelector("#candidateList");
const configMessage = document.querySelector("#configMessage");
const deviceStatusList = document.querySelector("#deviceStatusList");
const desktopAutostart = document.querySelector("#desktopAutostart");
const desktopLogPath = document.querySelector("#desktopLogPath");
const environmentList = document.querySelector("#environmentList");
const editModeButton = document.querySelector("#editModeButton");
const historyList = document.querySelector("#historyList");
const historyCount = document.querySelector("#historyCount");
const newRoomName = document.querySelector("#newRoomName");
const openLogsButton = document.querySelector("#openLogsButton");
const refreshStatusButton = document.querySelector("#refreshStatusButton");
const refreshCandidatesButton = document.querySelector("#refreshCandidatesButton");
const remoteList = document.querySelector("#remoteList");
const resultMessage = document.querySelector("#resultMessage");
const resultTime = document.querySelector("#resultTime");
const removeStaleButton = document.querySelector("#removeStaleButton");
const staleList = document.querySelector("#staleList");
const statusBadge = document.querySelector("#statusBadge");
const statusCheckedAt = document.querySelector("#statusCheckedAt");
const toastRegion = document.querySelector("#toastRegion");
const themeButton = document.querySelector("#themeButton");
const executionHistory = [];
const pendingDeviceDetails = new Map();
let statusRefreshTimer = null;
let availableRooms = ["未分類"];
let latestStatusSnapshot = null;
let currentButtons = [];
let roomEditBusy = false;
const quickIconOptions = {
  scene: "シーン", light: "照明", strip_light: "テープライト", plug: "プラグ",
  bot: "Bot", lock: "鍵", climate: "空調", fan: "扇風機", monitor: "モニター",
  game: "ゲーム", computer: "パソコン", bath: "お風呂", kettle: "ポット",
  door: "ドア", curtain: "カーテン", speaker: "スピーカー", tv: "テレビ",
  appliance: "家電", other: "その他",
};
const quickBadgeOptions = {
  none: "なし", up: "上", down: "下", left: "左", right: "右", on: "ON",
  off: "OFF", power: "電源", play: "再生", pause: "停止", plus: "＋",
  minus: "－", toggle: "切替",
};

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
  if (!message.endsWith("実行中...") && !message.endsWith("操作中...")) showToast(message, isError);
}

function showToast(message, isError = false) {
  const toast = document.createElement("div");
  toast.className = `toast${isError ? " error" : ""}`;
  toast.textContent = message;
  toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), isError ? 8000 : 3000);
}

function setBusy(isBusy) {
  buttonList.classList.toggle("busy", isBusy);
  document.querySelectorAll(".action-button").forEach((button) => {
    button.disabled = isBusy || button.closest(".scene-action")?.classList.contains("locked");
  });
  document.querySelectorAll(".scene-lock").forEach((button) => {
    button.disabled = isBusy;
  });
}

function addHistory(label, message, time, isError = false) {
  executionHistory.unshift({ label, message, time, isError });
  executionHistory.splice(5);
  historyCount.textContent = `${executionHistory.length}件`;
  historyList.replaceChildren();
  executionHistory.forEach((entry) => {
    const item = document.createElement("li");
    item.className = `history-item${entry.isError ? " error" : ""}`;
    const summary = document.createElement("span");
    summary.textContent = `${entry.label}: ${entry.message}`;
    const timestamp = document.createElement("time");
    timestamp.textContent = entry.time;
    item.append(summary, timestamp);
    historyList.append(item);
  });
}

async function executeAction(button) {
  setBusy(true);
  setResult(`${button.label} 実行中...`);
  try {
    const result = await requestJson(`/api/actions/${button.id}`, { method: "POST" });
    setResult(result.message, result.executed_at);
    addHistory(button.label, result.message, result.executed_at);
  } catch (error) {
    const time = new Date().toLocaleString("ja-JP");
    setResult(error.message, time, true);
    addHistory(button.label, error.message, time, true);
  } finally {
    setBusy(false);
  }
}

function renderButtons(buttons) {
  currentButtons = buttons;
  buttonList.replaceChildren();
  buttons = buttons.filter((button) => ["scene", "remote_command"].includes(button.type));
  const groups = new Map();
  buttons.forEach((button) => {
    const groupName = button.group || "その他";
    groups.set(groupName, [...(groups.get(groupName) || []), button]);
  });
  groups.forEach((groupButtons, groupName) => {
    const section = document.createElement("section");
    section.className = "action-group";
    const heading = document.createElement("h2");
    heading.textContent = groupName;
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    groupButtons.forEach((button) => {
      const wrapper = document.createElement("div");
      wrapper.className = `scene-action${button.locked ? " locked" : ""}`;
      const element = document.createElement("button");
      element.className = "action-button";
      element.type = "button";
      const icon = quickActionIcon(
        button.icon || (button.type === "remote_command" ? "climate" : "scene"),
        button.icon_badge || "none",
      );
      const label = document.createElement("span");
      label.textContent = button.label;
      element.append(icon, label);
      element.disabled = button.locked;
      element.addEventListener("click", () => executeAction(button));
      const lock = document.createElement("button");
      lock.type = "button";
      lock.className = `scene-lock${button.locked ? " locked" : ""}`;
      lock.title = button.locked ? "シーンのロックを解除" : "シーンをロック";
      lock.innerHTML = svgIcon(button.locked ? "locked" : "unlocked");
      lock.addEventListener("click", () => setSceneLock(button.id, !button.locked));
      wrapper.append(element, lock, buttonAppearanceEditor(button));
      toolbar.append(wrapper);
    });
    section.append(heading, toolbar);
    buttonList.append(section);
  });
}

async function loadButtons() {
  const data = await requestJson("/api/buttons");
  renderButtons(data.buttons);
}

async function setSceneLock(buttonId, locked) {
  try {
    await requestJson(`/api/buttons/${buttonId}/lock`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locked }),
    });
    await loadButtons();
    showToast(locked ? "シーンをロックしました。" : "シーンのロックを解除しました。");
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderStatus(snapshot) {
  latestStatusSnapshot = snapshot;
  statusCheckedAt.textContent = `更新: ${snapshot.checked_at}`;
  statusCheckedAt.classList.remove("error-text");
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

  const rooms = new Map();
  items.forEach((rawItem) => {
    const item = applyPendingDeviceDetails(rawItem);
    const room = item.room || "未分類";
    if (!rooms.has(room)) rooms.set(room, []);
    rooms.get(room).push(item);
  });
  const roomOrder = [
    ...availableRooms,
    ...[...rooms.keys()].filter((room) => !availableRooms.includes(room)),
  ];
  roomOrder.forEach((room) => {
    const roomItems = rooms.get(room) || [];
    const section = document.createElement("section");
    section.className = `room-section${roomItems.length === 0 ? " empty-room" : ""}`;
    const headingRow = document.createElement("div");
    headingRow.className = "room-heading";
    const heading = document.createElement("h3");
    heading.textContent = room;
    headingRow.append(heading, roomActionMenu(room));
    const grid = document.createElement("div");
    grid.className = "room-device-grid";
    section.append(headingRow, grid);
    roomItems.forEach((item) => {
    const element = document.createElement("div");
    element.className = `device-row${item.locked ? " locked" : ""}${item.stale ? " stale-row" : ""}`;
    element.dataset.deviceId = item.device_id;
    const details = detailList(item.details);
    const controlledDetails = {
      power: "power",
      brightness: "brightness",
      color: "color",
      color_temperature: "colorTemperature",
    };
    Object.entries(controlledDetails).forEach(([control, detail]) => {
      if (item.controls?.[control]) details.querySelector(`[data-detail-key="${detail}"]`)?.remove();
    });
    if (item.controls?.press) {
      details.querySelector('[data-detail-key="power"]')?.remove();
      details.querySelector('[data-detail-key="deviceMode"]')?.remove();
    }
    if (item.controls?.power || item.controls?.brightness || item.controls?.press) {
      details.append(deviceControls(item));
    }
    details.append(preferenceControls(item));
    if (item.stale) {
      const warning = document.createElement("div");
      warning.className = "device-status-warning";
      warning.textContent = "最新状態を取得できなかったため、直前の状態を表示しています。";
      details.append(warning);
    }
    element.append(deviceMainWithIcon(item), details);
    grid.append(element);
    });
    deviceStatusList.append(section);
  });

  const displayedIds = new Set(items.map((item) => item.device_id));
  errors.filter((error) => !displayedIds.has(error.device_id)).forEach((error) => {
    const element = document.createElement("div");
    element.className = "device-row error-row";
    element.append(deviceMain(error.label, "取得不可", error.message));
    deviceStatusList.append(element);
  });
}

function deviceControls(item) {
  const controls = document.createElement("div");
  controls.className = "device-controls";
  if (item.controls.power) {
    const power = item.details.find((detail) => detail.key === "power")?.value === "on";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = `power-toggle${power ? " on" : ""}`;
    toggle.setAttribute("role", "switch");
    toggle.setAttribute("aria-checked", String(power));
    toggle.innerHTML = `<span></span><strong>${power ? "ON" : "OFF"}</strong>`;
    toggle.addEventListener("click", () => controlDevice(item, power ? "turn_off" : "turn_on"));
    controls.append(controlField("電源", toggle));
  }
  if (item.controls.press) {
    controls.append(controlField("操作", controlButton("押す", () => controlDevice(item, "press"))));
  }
  if (item.controls.brightness) {
    const brightness = item.details.find((detail) => detail.key === "brightness")?.value || 50;
    const range = document.createElement("input");
    range.type = "range";
    range.min = "1";
    range.max = "100";
    range.value = brightness;
    range.dataset.committedValue = String(brightness);
    range.title = "明るさ";
    const value = document.createElement("span");
    value.textContent = `${brightness}%`;
    range.addEventListener("input", () => { value.textContent = `${range.value}%`; });
    range.addEventListener("change", async () => {
      const previous = Number(range.dataset.committedValue);
      const next = Number(range.value);
      const succeeded = await controlDevice(item, "set_brightness", next, () => {
        range.value = String(previous);
        value.textContent = `${previous}%`;
      });
      if (succeeded) range.dataset.committedValue = String(next);
    });
    controls.append(controlField("明るさ", range, value));
  }
  if (item.controls.color) {
    const color = document.createElement("input");
    color.type = "color";
    color.className = "color-control";
    color.title = "色";
    const current = item.details.find((detail) => detail.key === "color")?.value;
    color.value = rgbToHex(current || "255:255:255");
    color.dataset.committedValue = color.value;
    color.addEventListener("change", async () => {
      const previous = color.dataset.committedValue;
      const next = color.value;
      const succeeded = await controlDevice(item, "set_color", hexToRgb(next), () => {
        color.value = previous;
      });
      if (succeeded) color.dataset.committedValue = next;
    });
    controls.append(controlField("色", color));
  }
  if (item.controls.color_temperature) {
    const temperature = document.createElement("input");
    temperature.type = "range";
    temperature.className = "temperature-control";
    temperature.min = "2700";
    temperature.max = "6500";
    temperature.step = "100";
    temperature.title = "色温度";
    const current = item.details.find((detail) => detail.key === "colorTemperature")?.value || 4000;
    temperature.value = current;
    temperature.dataset.committedValue = String(current);
    const value = document.createElement("span");
    value.textContent = `${current}K`;
    temperature.addEventListener("input", () => { value.textContent = `${temperature.value}K`; });
    temperature.addEventListener("change", async () => {
      const previous = Number(temperature.dataset.committedValue);
      const next = Number(temperature.value);
      const succeeded = await controlDevice(item, "set_color_temperature", next, () => {
        temperature.value = String(previous);
        value.textContent = `${previous}K`;
      });
      if (succeeded) temperature.dataset.committedValue = String(next);
    });
    controls.append(controlField("色温度", temperature, value));
  }
  if (item.controls.brightness) {
    const presets = document.createElement("div");
    presets.className = "light-presets";
    const editor = createLightPresetEditor(item);
    (item.presets || []).forEach((preset) => {
      const chip = document.createElement("span");
      chip.className = "preset-chip";
      const button = controlButton(preset.name, () => applyLightPreset(item, preset));
      button.title = presetSummary(preset);
      const summary = document.createElement("small");
      summary.textContent = presetSummary(preset);
      button.append(summary);
      const edit = controlButton("✎", () => openLightPresetEditor(item, editor, preset));
      edit.classList.add("preset-edit");
      edit.title = `マイセット「${preset.name}」を編集`;
      edit.setAttribute("aria-label", edit.title);
      const remove = controlButton("×", () => removeLightPreset(item, preset));
      remove.classList.add("preset-remove");
      remove.title = `マイセット「${preset.name}」を削除`;
      remove.setAttribute("aria-label", remove.title);
      chip.append(button, edit, remove);
      presets.append(chip);
    });
    const add = controlButton("＋ マイセット", () => {
      if (!editor.hidden && !editor.dataset.originalName) editor.hidden = true;
      else openLightPresetEditor(item, editor);
    });
    presets.append(add);
    controls.append(presets, editor);
  }
  const feedback = document.createElement("div");
  feedback.className = "device-feedback";
  feedback.setAttribute("aria-live", "polite");
  feedback.hidden = true;
  controls.append(feedback);
  if (item.locked) {
    controls.querySelectorAll("button, input").forEach((element) => { element.disabled = true; });
  }
  return controls;
}

function controlField(label, ...elements) {
  const field = document.createElement("div");
  field.className = "device-control-field";
  const controlName = {
    "電源": "power", "操作": "action", "明るさ": "brightness",
    "色温度": "temperature", "色": "color",
  }[label];
  if (controlName) field.classList.add(`device-control-${controlName}`);
  const name = document.createElement("span");
  name.className = "device-control-label";
  name.textContent = label;
  field.append(name, ...elements);
  return field;
}

function createLightPresetEditor(item) {
  const editor = document.createElement("form");
  editor.className = "preset-editor";
  editor.hidden = true;
  const name = document.createElement("input");
  name.type = "text";
  name.maxLength = 40;
  name.placeholder = "マイセット名";
  name.className = "preset-name";
  name.setAttribute("aria-label", `${item.label}のマイセット名`);
  const brightness = document.createElement("input");
  brightness.type = "number";
  brightness.min = "1";
  brightness.max = "100";
  brightness.className = "preset-brightness";
  brightness.setAttribute("aria-label", "明るさ");
  const color = document.createElement("input");
  color.type = "color";
  color.className = "preset-color";
  color.setAttribute("aria-label", "RGB色");
  color.hidden = !item.controls.color;
  const temperature = document.createElement("input");
  temperature.type = "number";
  temperature.min = "2700";
  temperature.max = "6500";
  temperature.step = "100";
  temperature.className = "preset-temperature";
  temperature.setAttribute("aria-label", "色温度");
  temperature.hidden = !item.controls.color_temperature;
  const mode = document.createElement("select");
  mode.className = "preset-mode";
  mode.setAttribute("aria-label", "保存する色設定");
  mode.append(new Option("RGB色を保存", "color"), new Option("色温度を保存", "temperature"));
  mode.hidden = !(item.controls.color && item.controls.color_temperature);
  const save = controlButton("保存", () => {});
  save.type = "submit";
  const cancel = controlButton("キャンセル", () => {
    editor.hidden = true;
    name.value = "";
    editor.dataset.originalName = "";
  });
  cancel.type = "button";
  editor.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!name.value.trim()) {
      name.focus();
      return;
    }
    await saveLightPreset(item, editor);
  });
  editor.append(name, brightness);
  if (!mode.hidden) editor.append(mode);
  if (!color.hidden) editor.append(color);
  if (!temperature.hidden) editor.append(temperature);
  editor.append(save, cancel);
  return editor;
}

function openLightPresetEditor(item, editor, preset = null) {
  const row = document.querySelector(`[data-device-id="${CSS.escape(item.device_id)}"]`);
  editor.dataset.originalName = preset?.name || "";
  editor.querySelector(".preset-name").value = preset?.name || "";
  editor.querySelector(".preset-brightness").value = String(
    preset?.brightness || row?.querySelector('input[title="明るさ"]')?.value || 50,
  );
  const color = editor.querySelector(".preset-color");
  if (color) color.value = rgbToHex(preset?.color || hexToRgb(row?.querySelector('input[title="色"]')?.value || "#ffffff"));
  const temperature = editor.querySelector(".preset-temperature");
  if (temperature) {
    temperature.value = String(
      preset?.color_temperature || row?.querySelector('input[title="色温度"]')?.value || 4000,
    );
  }
  const mode = editor.querySelector(".preset-mode");
  if (mode) mode.value = preset?.color ? "color" : "temperature";
  editor.hidden = false;
  editor.querySelector(".preset-name").focus();
}

function presetSummary(preset) {
  const details = [`明るさ ${preset.brightness}%`];
  if (preset.color) details.push(`RGB ${preset.color}`);
  if (preset.color_temperature) details.push(`色温度 ${preset.color_temperature}K`);
  return details.join(" / ");
}

async function saveLightPreset(item, editor) {
  const name = editor.querySelector(".preset-name").value.trim();
  const brightness = Number(editor.querySelector(".preset-brightness").value);
  const mode = editor.querySelector(".preset-mode")?.value || (item.controls.color ? "color" : "temperature");
  const colorHex = editor.querySelector(".preset-color")?.value;
  const colorTemperature = Number(editor.querySelector(".preset-temperature")?.value || 0) || null;
  const useColor = Boolean(colorHex) && mode === "color";
  const originalName = editor.dataset.originalName;
  if (!originalName && (item.presets || []).some((preset) => preset.name === name)) {
    if (!window.confirm(`マイセット「${name}」を上書きしますか？`)) return;
  }
  setDeviceBusy(item, true, "マイセットを保存中...");
  try {
    const url = originalName
      ? `/api/devices/${encodeURIComponent(item.device_id)}/presets/${encodeURIComponent(originalName)}`
      : `/api/devices/${encodeURIComponent(item.device_id)}/presets`;
    await requestJson(url, {
      method: originalName ? "PUT" : "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name, brightness,
        color: useColor ? hexToRgb(colorHex) : null,
        color_temperature: useColor ? null : colorTemperature,
      }),
    });
    showToast(`マイセット「${name}」を保存しました。`);
    editor.hidden = true;
    editor.dataset.originalName = "";
    await refreshStatus();
    setDeviceFeedback(item.device_id, `マイセット「${name}」を保存しました。`, "success");
  } catch (error) {
    showToast(error.message, true);
    setDeviceFeedback(item.device_id, error.message, "error");
  } finally {
    setDeviceBusy(item, false);
  }
}

async function applyLightPreset(item, preset) {
  const actions = [];
  if (preset.brightness) actions.push(["set_brightness", preset.brightness]);
  if (preset.color) actions.push(["set_color", preset.color]);
  else if (preset.color_temperature) actions.push(["set_color_temperature", preset.color_temperature]);
  setDeviceBusy(item, true, `マイセット「${preset.name}」を適用中...`);
  try {
    for (const [action, value] of actions) {
      await requestJson(`/api/devices/${item.device_id}/control`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, value }),
      });
    }
    if (preset.brightness) setPendingDeviceDetail(item.device_id, "brightness", preset.brightness);
    if (preset.color) setPendingDeviceDetail(item.device_id, "color", preset.color);
    if (preset.color_temperature) {
      setPendingDeviceDetail(item.device_id, "colorTemperature", preset.color_temperature);
    }
    const time = new Date().toLocaleString("ja-JP");
    showToast(`${item.label}「${preset.name}」を適用しました。`);
    setDeviceFeedback(item.device_id, `「${preset.name}」を適用しました。`, "success");
    addHistory(item.label, `マイセット ${preset.name} 適用`, time);
    scheduleStatusRefresh(5000);
  } catch (error) {
    showToast(error.message, true);
    setDeviceFeedback(item.device_id, error.message, "error");
    scheduleStatusRefresh(3000);
  } finally {
    setDeviceBusy(item, false);
  }
}

async function removeLightPreset(item, preset) {
  if (!window.confirm(`マイセット「${preset.name}」を削除しますか？`)) return;
  setDeviceBusy(item, true, `マイセット「${preset.name}」を削除中...`);
  try {
    await requestJson(
      `/api/devices/${encodeURIComponent(item.device_id)}/presets/${encodeURIComponent(preset.name)}`,
      { method: "DELETE" },
    );
    showToast(`マイセット「${preset.name}」を削除しました。`);
    await refreshStatus();
    setDeviceFeedback(item.device_id, `「${preset.name}」を削除しました。`, "success");
  } catch (error) {
    showToast(error.message, true);
    setDeviceFeedback(item.device_id, error.message, "error");
  } finally {
    setDeviceBusy(item, false);
  }
}

function rgbToHex(rgb) {
  const parts = String(rgb).split(":").map(Number);
  if (parts.length !== 3 || parts.some((value) => Number.isNaN(value))) return "#ffffff";
  return `#${parts.map((value) => Math.max(0, Math.min(255, value)).toString(16).padStart(2, "0")).join("")}`;
}

function hexToRgb(hex) {
  return [1, 3, 5].map((index) => Number.parseInt(hex.slice(index, index + 2), 16)).join(":");
}

function preferenceControls(item) {
  const controls = document.createElement("div");
  controls.className = "preference-controls";
  const room = document.createElement("select");
  room.setAttribute("aria-label", `${item.label}の部屋`);
  [...new Set([...availableRooms, item.room || "未分類"])].forEach((roomName) => {
    const option = document.createElement("option");
    option.value = roomName;
    option.textContent = roomName;
    option.selected = roomName === item.room;
    room.append(option);
  });
  room.addEventListener("change", () => savePreference(item, { room: room.value }));
  const lock = document.createElement("button");
  lock.type = "button";
  lock.className = `device-lock${item.locked ? " locked" : ""}`;
  lock.title = item.locked ? "操作ロックを解除" : "操作をロック";
  lock.setAttribute("aria-label", lock.title);
  lock.innerHTML = svgIcon(item.locked ? "locked" : "unlocked");
  lock.addEventListener("click", () => savePreference(item, { locked: !item.locked }));
  const saveStatus = document.createElement("span");
  saveStatus.className = "preference-save-status";
  saveStatus.setAttribute("aria-live", "polite");
  controls.append(room, lock, saveStatus);
  return controls;
}

function deviceMainWithIcon(item) {
  const wrapper = deviceMain(item.label, item.type, friendlyDeviceStatus(item));
  wrapper.querySelector(".device-meta").title = `${item.type} / ${item.summary}`;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "device-icon-button";
  button.title = "アイコンを変更";
  button.innerHTML = svgIcon(item.icon);
  const picker = iconPicker(item);
  button.addEventListener("click", () => picker.toggleAttribute("hidden"));
  wrapper.prepend(button);
  wrapper.append(picker);
  return wrapper;
}

function iconPicker(item) {
  const picker = document.createElement("div");
  picker.className = "icon-picker";
  picker.hidden = true;
  const icons = ["light", "strip_light", "plug", "bot", "sensor", "lock", "hub", "climate", "appliance", "other"];
  icons.forEach((icon) => {
    const button = document.createElement("button");
    button.type = "button";
    button.title = icon;
    button.innerHTML = svgIcon(icon);
    button.addEventListener("click", () => savePreference(item, { icon }));
    picker.append(button);
  });
  return picker;
}

function svgIcon(icon) {
  const paths = {
    scene: '<path d="M4 12h16M12 4v16"/><circle cx="12" cy="12" r="8"/>',
    light: '<path d="M9 18h6M10 22h4M8 14a7 7 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z"/>',
    strip_light: '<path d="M4 7h14a3 3 0 0 1 0 6H8a2 2 0 0 0 0 4h12"/><circle cx="4" cy="7" r="1"/>',
    plug: '<path d="M8 3v6m8-6v6M6 9h12v2a6 6 0 0 1-6 6v4"/>',
    bot: '<rect x="5" y="5" width="14" height="14" rx="4"/><circle cx="12" cy="12" r="3"/>',
    sensor: '<path d="M4 12a8 8 0 0 1 8-8m-8 8a8 8 0 0 0 8 8m-4-8a4 4 0 0 1 4-4m-4 4a4 4 0 0 0 4 4"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    hub: '<rect x="4" y="6" width="16" height="12" rx="3"/><path d="M8 13h8M12 9v8"/>',
    climate: '<path d="M7 5h10M5 9h14M7 13h10M9 17h6"/><path d="M4 3v16h16V3"/>',
    fan: '<circle cx="12" cy="12" r="2"/><path d="M12 10c-1-5 2-7 5-5 2 2 0 6-3 7M10 12c-5 1-7-2-5-5 2-2 6 0 7 3M12 14c1 5-2 7-5 5-2-2 0-6 3-7"/>',
    monitor: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
    game: '<path d="M8 8h8a6 6 0 0 1 5 7l-1 3a2 2 0 0 1-3 1l-3-2h-4l-3 2a2 2 0 0 1-3-1l-1-3a6 6 0 0 1 5-7Z"/><path d="M7 12v4m-2-2h4m7-1h.01m2 2h.01"/>',
    computer: '<rect x="4" y="3" width="16" height="13" rx="2"/><path d="M8 21h8M12 16v5"/>',
    bath: '<path d="M3 12h18v2a6 6 0 0 1-6 6H9a6 6 0 0 1-6-6v-2Z"/><path d="M7 12V6a3 3 0 0 1 6 0"/>',
    kettle: '<path d="M6 7h10v12H6Z"/><path d="M16 9h2a3 3 0 0 1 0 6h-2M8 4h6"/>',
    door: '<path d="M5 21V3h14v18M9 21V7h7v14"/><circle cx="14" cy="14" r=".5"/>',
    curtain: '<path d="M4 4h16M6 4v16m12-16v16M6 20c4-4 4-12 0-16m12 16c-4-4-4-12 0-16"/>',
    speaker: '<rect x="6" y="3" width="12" height="18" rx="2"/><circle cx="12" cy="14" r="4"/><circle cx="12" cy="7" r="1"/>',
    tv: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m9 2 3 3 3-3"/>',
    appliance: '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="13" r="4"/><path d="M8 7h1m2 0h1"/>',
    other: '<path d="M12 3 3 9v10h18V9l-9-6Z"/><path d="M9 19v-6h6v6"/>',
    locked: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    unlocked: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M16 10V7a4 4 0 0 0-7-2"/>',
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[icon] || paths.other}</svg>`;
}

async function savePreference(item, changes) {
  const previousSnapshot = cloneSnapshot(latestStatusSnapshot);
  const current = latestStatusSnapshot?.devices?.find(
    (device) => device.device_id === item.device_id,
  );
  if (current) Object.assign(current, changes);
  if (latestStatusSnapshot) renderStatus(latestStatusSnapshot);
  setPreferenceSaving(current || item, true);
  try {
    await requestJson(`/api/devices/${item.device_id}/preference`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room: item.room || "未分類", icon: item.icon, locked: item.locked, ...changes }),
    });
    setPreferenceSaving(current || item, false);
    showToast("デバイス設定を保存しました。");
  } catch (error) {
    if (previousSnapshot) renderStatus(previousSnapshot);
    setResult(error.message, new Date().toLocaleString("ja-JP"), true);
    showToast(error.message, true);
  }
}

function cloneSnapshot(snapshot) {
  return snapshot ? JSON.parse(JSON.stringify(snapshot)) : null;
}

function roomActionMenu(room) {
  const menu = document.createElement("details");
  menu.className = "room-action-menu edit-only";
  const trigger = document.createElement("summary");
  trigger.textContent = "…";
  trigger.title = `${room}のメニュー`;
  trigger.setAttribute("aria-label", trigger.title);
  const panel = document.createElement("div");
  panel.className = "room-action-panel";
  const index = availableRooms.indexOf(room);
  const up = controlButton("↑ 上へ移動", () => moveRoom(room, -1));
  up.disabled = roomEditBusy || index <= 0;
  const down = controlButton("↓ 下へ移動", () => moveRoom(room, 1));
  down.disabled = roomEditBusy || index < 0 || index >= availableRooms.length - 1;
  panel.append(up, down);
  if (room !== "未分類") {
    const remove = controlButton("部屋を削除", () => removeRoom(room));
    remove.classList.add("room-remove");
    remove.disabled = roomEditBusy;
    panel.append(remove);
  }
  menu.append(trigger, panel);
  return menu;
}

function quickActionIcon(icon, badge) {
  const wrapper = document.createElement("span");
  wrapper.className = "quick-action-icon";
  wrapper.innerHTML = svgIcon(icon);
  if (badge && badge !== "none") {
    const marker = document.createElement("span");
    marker.className = "quick-action-badge";
    marker.innerHTML = badgeVisual(badge);
    wrapper.append(marker);
  }
  return wrapper;
}

function friendlyDeviceStatus(item) {
  const details = Object.fromEntries((item.details || []).map((detail) => [detail.key, detail.value]));
  if (details.deviceMode === "pressMode") return "押すモード";
  if (details.power === "on") return "オン";
  if (details.power === "off") return "オフ";
  if (details.lockState) return details.lockState === "locked" ? "施錠中" : "解錠中";
  if (details.openState) return details.openState === "open" ? "開いています" : "閉じています";
  if (details.temperature !== undefined) return `${details.temperature}℃ / 湿度 ${details.humidity}%`;
  return "状態情報なし";
}

function buttonAppearanceEditor(button) {
  const editor = document.createElement("details");
  editor.className = "scene-appearance-editor edit-only";
  let selectedIcon = button.icon || "scene";
  let selectedBadge = button.icon_badge || "none";
  const summary = document.createElement("summary");
  summary.append(quickActionIcon(selectedIcon, selectedBadge), document.createTextNode("アイコン設定"));
  const panel = document.createElement("div");
  panel.className = "scene-appearance-panel";
  const iconTitle = document.createElement("strong");
  iconTitle.textContent = "ベースアイコン";
  const iconGrid = document.createElement("div");
  iconGrid.className = "appearance-choice-grid icon-choice-grid";
  const badgeTitle = document.createElement("strong");
  badgeTitle.textContent = "操作バッジ";
  const badgeGrid = document.createElement("div");
  badgeGrid.className = "appearance-choice-grid badge-choice-grid";

  const refreshSelection = () => {
    iconGrid.querySelectorAll("button").forEach((choice) => {
      choice.classList.toggle("selected", choice.dataset.value === selectedIcon);
    });
    badgeGrid.querySelectorAll("button").forEach((choice) => {
      choice.classList.toggle("selected", choice.dataset.value === selectedBadge);
    });
    summary.replaceChildren(
      quickActionIcon(selectedIcon, selectedBadge),
      document.createTextNode("アイコン設定"),
    );
  };

  Object.entries(quickIconOptions).forEach(([value, label]) => {
    const choice = appearanceChoice(label, value, svgIcon(value));
    choice.addEventListener("click", () => { selectedIcon = value; refreshSelection(); });
    iconGrid.append(choice);
  });
  Object.entries(quickBadgeOptions).forEach(([value, label]) => {
    const visual = `<span class="badge-choice-symbol">${badgeVisual(value) || "なし"}</span>`;
    const choice = appearanceChoice(label, value, visual);
    choice.addEventListener("click", () => { selectedBadge = value; refreshSelection(); });
    badgeGrid.append(choice);
  });
  const apply = document.createElement("button");
  apply.type = "button";
  apply.className = "appearance-apply-button";
  apply.textContent = "適用";
  apply.addEventListener("click", () => setButtonAppearance(button, selectedIcon, selectedBadge));
  panel.append(iconTitle, iconGrid, badgeTitle, badgeGrid, apply);
  editor.append(summary, panel);
  refreshSelection();
  return editor;
}

function appearanceChoice(label, value, visual) {
  const choice = document.createElement("button");
  choice.type = "button";
  choice.dataset.value = value;
  choice.title = label;
  choice.setAttribute("aria-label", label);
  choice.innerHTML = visual;
  const text = document.createElement("small");
  text.textContent = label;
  choice.append(text);
  return choice;
}

function badgeVisual(badge) {
  if (badge === "on" || badge === "off") return `<span>${badge.toUpperCase()}</span>`;
  const paths = {
    up: '<path d="m3 7 5-5 5 5M8 2v12"/>',
    down: '<path d="m3 9 5 5 5-5M8 14V2"/>',
    left: '<path d="m7 3-5 5 5 5M2 8h12"/>',
    right: '<path d="m9 3 5 5-5 5M14 8H2"/>',
    power: '<path d="M8 1v7M4 3.5a6 6 0 1 0 8 0"/>',
    play: '<path d="m5 2 8 6-8 6Z"/>',
    pause: '<path d="M4 3h3v10H4zm5 0h3v10H9z"/>',
    plus: '<path d="M8 2v12M2 8h12"/>',
    minus: '<path d="M2 8h12"/>',
    toggle: '<path d="m5 3-3 3 3 3M2 6h12m-3 1 3 3-3 3"/>',
  };
  return paths[badge]
    ? `<svg viewBox="0 0 16 16" aria-hidden="true">${paths[badge]}</svg>`
    : "";
}

async function setButtonAppearance(button, icon, iconBadge) {
  const previous = { icon: button.icon || "scene", icon_badge: button.icon_badge || "none" };
  button.icon = icon;
  button.icon_badge = iconBadge;
  renderButtons(currentButtons);
  try {
    await requestJson(`/api/buttons/${button.id}/appearance`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ icon, icon_badge: iconBadge }),
    });
    showToast("クイック操作のアイコンを保存しました。");
  } catch (error) {
    Object.assign(button, previous);
    renderButtons(currentButtons);
    showToast(error.message, true);
  }
}

function setPreferenceSaving(item, saving) {
  const row = document.querySelector(`[data-device-id="${CSS.escape(item.device_id)}"]`);
  if (!row) return;
  row.classList.toggle("preference-saving", saving);
  row.querySelectorAll(".preference-controls button, .preference-controls select").forEach((element) => {
    element.disabled = saving || item.locked;
  });
  const status = row.querySelector(".preference-save-status");
  if (status) status.textContent = saving ? "保存中..." : "";
}

function controlButton(label, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "mini-button";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}

async function controlDevice(item, action, value = null, rollback = null) {
  const optimistic = optimisticDeviceDetail(action, value);
  const previousSnapshot = cloneSnapshot(latestStatusSnapshot);
  if (optimistic) {
    setPendingDeviceDetail(item.device_id, optimistic.key, optimistic.value);
    if (latestStatusSnapshot) renderStatus(latestStatusSnapshot);
  }
  setDeviceBusy(item, true, `${operationLabel(action)}を操作中...`);
  setResult(`${item.label} 送信中...`);
  try {
    const result = await requestJson(`/api/devices/${item.device_id}/control`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, value }),
    });
    const time = new Date().toLocaleString("ja-JP");
    setResult(result.message, time);
    addHistory(item.label, result.message, time);
    setDeviceFeedback(item.device_id, result.message, "success");
    if (action === "set_brightness") {
      scheduleStatusRefresh(5000);
    } else {
      scheduleStatusRefresh(2000);
    }
    return true;
  } catch (error) {
    if (optimistic) removePendingDeviceDetail(item.device_id, optimistic.key);
    if (previousSnapshot) renderStatus(previousSnapshot);
    else rollback?.();
    const time = new Date().toLocaleString("ja-JP");
    setResult(error.message, time, true);
    addHistory(item.label, error.message, time, true);
    setDeviceFeedback(item.device_id, error.message, "error");
    scheduleStatusRefresh(3000);
    return false;
  } finally {
    setDeviceBusy(item, false);
  }
}

function operationLabel(action) {
  return ({
    turn_on: "電源ON",
    turn_off: "電源OFF",
    press: "ボタン",
    set_brightness: "明るさ",
    set_color: "色",
    set_color_temperature: "色温度",
  })[action] || "デバイス";
}

function setDeviceBusy(item, isBusy, message = "") {
  const row = document.querySelector(`[data-device-id="${CSS.escape(item.device_id)}"]`);
  if (!row) return;
  row.classList.toggle("busy", isBusy);
  row.setAttribute("aria-busy", String(isBusy));
  row.querySelectorAll("button, input, select").forEach((element) => {
    element.disabled = isBusy || item.locked;
  });
  if (isBusy && message) setDeviceFeedback(item.device_id, message, "pending");
}

function setDeviceFeedback(deviceId, message, state) {
  const row = document.querySelector(`[data-device-id="${CSS.escape(deviceId)}"]`);
  const feedback = row?.querySelector(".device-feedback");
  if (!feedback) return;
  feedback.hidden = !message;
  feedback.className = `device-feedback ${state || ""}`.trim();
  feedback.textContent = message;
}

function setPendingDeviceDetail(deviceId, key, value) {
  const pending = pendingDeviceDetails.get(deviceId) || {};
  pending[key] = { value, expiresAt: Date.now() + 30000 };
  pendingDeviceDetails.set(deviceId, pending);
}

function removePendingDeviceDetail(deviceId, key) {
  const pending = pendingDeviceDetails.get(deviceId);
  if (!pending) return;
  delete pending[key];
  if (Object.keys(pending).length === 0) pendingDeviceDetails.delete(deviceId);
  else pendingDeviceDetails.set(deviceId, pending);
}

function applyPendingDeviceDetails(item) {
  const pending = pendingDeviceDetails.get(item.device_id);
  if (!pending) return item;
  const now = Date.now();
  const details = item.details.map((detail) => {
    const expected = pending[detail.key];
    if (!expected) return detail;
    if (String(detail.value) === String(expected.value) || now >= expected.expiresAt) {
      delete pending[detail.key];
      return detail;
    }
    return { ...detail, value: expected.value };
  });
  if (Object.keys(pending).length === 0) pendingDeviceDetails.delete(item.device_id);
  else {
    pendingDeviceDetails.set(item.device_id, pending);
    scheduleStatusRefresh(5000);
  }
  return { ...item, details };
}

function scheduleStatusRefresh(delay) {
  if (statusRefreshTimer !== null) window.clearTimeout(statusRefreshTimer);
  statusRefreshTimer = window.setTimeout(() => {
    statusRefreshTimer = null;
    refreshStatus();
  }, delay);
}

function renderRemotes(items) {
  remoteList.replaceChildren();
  if (items.length === 0) {
    remoteList.append(emptyText("赤外線リモコンは見つかりませんでした。"));
    return;
  }

  items.forEach((item) => {
    const element = document.createElement("div");
    element.className = "device-row remote-row";
    element.dataset.remoteId = item.device_id;
    const details = item.controls?.air_conditioner
      ? airConditionerControls(item)
      : remoteDetails(item);
    element.append(deviceMain(item.label, item.type, item.summary), details);
    remoteList.append(element);
  });
}

function airConditionerControls(item) {
  const wrapper = document.createElement("form");
  wrapper.className = "air-conditioner-controls";

  const temperature = remoteSelect("温度", Array.from({ length: 15 }, (_, i) => {
    const value = String(i + 16);
    return [value, `${value}℃`];
  }), "24");
  const mode = remoteSelect("モード", [
    ["auto", "自動"], ["cool", "冷房"], ["dry", "除湿"],
    ["fan", "送風"], ["heat", "暖房"],
  ], "cool");
  const fanSpeed = remoteSelect("風量", [
    ["auto", "自動"], ["low", "弱"], ["medium", "中"], ["high", "強"],
  ], "auto");
  const power = remoteSelect("電源", [["on", "ON"], ["off", "OFF"]], "on");

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "mini-button remote-send-button";
  submit.textContent = "この設定を送信";

  const quickButton = document.createElement("button");
  quickButton.type = "button";
  quickButton.className = "mini-button remote-quick-button";
  quickButton.textContent = "＋ クイック操作";

  const quickEditor = airConditionerQuickEditor(item, {
    temperature, mode, fanSpeed, power,
  });
  quickButton.addEventListener("click", () => {
    quickEditor.hidden = !quickEditor.hidden;
  });

  const feedback = document.createElement("div");
  feedback.className = "device-feedback";
  feedback.hidden = true;

  wrapper.append(
    temperature.field, mode.field, fanSpeed.field, power.field,
    submit, quickButton, quickEditor, feedback,
  );
  wrapper.addEventListener("submit", async (event) => {
    event.preventDefault();
    wrapper.closest(".remote-row")?.classList.add("busy");
    submit.disabled = true;
    feedback.hidden = false;
    feedback.className = "device-feedback pending";
    feedback.textContent = "赤外線コマンドを送信中...";
    setResult(`${item.label} 送信中...`);
    try {
      const result = await requestJson(`/api/remotes/${item.device_id}/air-conditioner`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          temperature: Number(temperature.select.value),
          mode: mode.select.value,
          fan_speed: fanSpeed.select.value,
          power: power.select.value,
        }),
      });
      const time = new Date().toLocaleString("ja-JP");
      feedback.className = "device-feedback success";
      feedback.textContent = `最後に送信: ${remoteSettingLabel(result.last_sent)}`;
      setResult(result.message, time);
      addHistory(item.label, result.message, time);
    } catch (error) {
      const time = new Date().toLocaleString("ja-JP");
      feedback.className = "device-feedback error";
      feedback.textContent = error.message;
      setResult(error.message, time, true);
      addHistory(item.label, error.message, time, true);
    } finally {
      wrapper.closest(".remote-row")?.classList.remove("busy");
      submit.disabled = false;
    }
  });
  return wrapper;
}

function airConditionerQuickEditor(item, controls) {
  const editor = document.createElement("div");
  editor.className = "remote-quick-editor";
  editor.hidden = true;

  const name = labeledTextInput("表示名", `${item.label} 24℃ 冷房`);
  const group = labeledTextInput("グループ", "空調");
  const icon = remoteSelect("アイコン", Object.entries(quickIconOptions), "climate");
  const save = document.createElement("button");
  save.type = "button";
  save.className = "mini-button";
  save.textContent = "追加";
  save.addEventListener("click", async () => {
    const label = name.input.value.trim();
    const groupName = group.input.value.trim();
    if (!label || !groupName) {
      showToast("表示名とグループを入力してください。", true);
      return;
    }
    const payload = {
      label,
      group: groupName,
      device_id: item.device_id,
      parameter: airConditionerParameter(controls),
      icon: icon.select.value,
      icon_badge: "none",
      overwrite: false,
    };
    save.disabled = true;
    try {
      await saveRemoteQuickAction(payload);
      editor.hidden = true;
    } catch (error) {
      if (error.message.includes("同じリモコン設定が登録済み") &&
          window.confirm("同じ設定が登録済みです。表示名などを上書きしますか？")) {
        payload.overwrite = true;
        try {
          await saveRemoteQuickAction(payload);
          editor.hidden = true;
        } catch (overwriteError) {
          showToast(overwriteError.message, true);
        }
      } else if (!error.message.includes("同じリモコン設定が登録済み")) {
        showToast(error.message, true);
      }
    } finally {
      save.disabled = false;
    }
  });
  editor.append(name.field, group.field, icon.field, save);
  return editor;
}

function labeledTextInput(label, value) {
  const field = document.createElement("label");
  field.className = "remote-control-field";
  const caption = document.createElement("span");
  caption.textContent = label;
  const input = document.createElement("input");
  input.type = "text";
  input.value = value;
  field.append(caption, input);
  return { field, input };
}

function airConditionerParameter({ temperature, mode, fanSpeed, power }) {
  const modeCodes = { auto: 1, cool: 2, dry: 3, fan: 4, heat: 5 };
  const fanCodes = { auto: 1, low: 2, medium: 3, high: 4 };
  return [
    temperature.select.value,
    modeCodes[mode.select.value],
    fanCodes[fanSpeed.select.value],
    power.select.value,
  ].join(",");
}

async function saveRemoteQuickAction(payload) {
  const result = await requestJson("/api/remotes/quick-actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await loadButtons();
  showToast(result.updated ? "クイック操作を更新しました。" : "クイック操作へ追加しました。");
}

function remoteSelect(label, options, selected) {
  const field = document.createElement("label");
  field.className = "remote-control-field";
  const caption = document.createElement("span");
  caption.textContent = label;
  const select = document.createElement("select");
  options.forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    option.selected = value === selected;
    select.append(option);
  });
  field.append(caption, select);
  return { field, select };
}

function remoteSettingLabel(setting) {
  const modes = { auto: "自動", cool: "冷房", dry: "除湿", fan: "送風", heat: "暖房" };
  const fans = { auto: "風量自動", low: "風量弱", medium: "風量中", high: "風量強" };
  return `${setting.power === "on" ? "ON" : "OFF"} / ${setting.temperature}℃ / ${modes[setting.mode]} / ${fans[setting.fan_speed]}`;
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
    pill.dataset.detailKey = detail.key;
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
  const translated = {
    on: "オン", off: "オフ", pressMode: "押すモード", switchMode: "スイッチモード",
    open: "開", close: "閉", locked: "施錠", unlocked: "解錠",
  }[String(detail.value)] || detail.value;
  return `${label}: ${translated}${suffix}`;
}

function emptyText(message) {
  const element = document.createElement("div");
  element.className = "empty-text";
  element.textContent = message;
  return element;
}

async function refreshCandidates() {
  refreshCandidatesButton.disabled = true;
  configMessage.textContent = "取得中...";
  try {
    const data = await requestJson("/api/config/candidates", { method: "POST" });
    candidateList.replaceChildren();
    data.candidates.forEach((candidate) => {
      const label = document.createElement("label");
      label.className = "candidate-item";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = candidate.id;
      checkbox.addEventListener("change", updateApplyButton);
      const text = document.createElement("span");
      text.textContent = `${candidate.group} / ${candidate.label}`;
      label.append(checkbox, text);
      candidateList.append(label);
    });
    if (data.candidates.length === 0) candidateList.append(emptyText("追加候補はありません。"));
    staleList.replaceChildren();
    data.stale.forEach((candidate) => {
      const label = document.createElement("label");
      label.className = "candidate-item stale-item";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = candidate.id;
      checkbox.addEventListener("change", updateRemoveButton);
      const text = document.createElement("span");
      text.textContent = `存在しません: ${candidate.label}`;
      label.append(checkbox, text);
      staleList.append(label);
    });
    if (data.stale.length === 0) staleList.append(emptyText("削除候補はありません。"));
    configMessage.textContent = `追加候補 ${data.candidates.length}件 / 削除候補 ${data.stale.length}件`;
  } catch (error) {
    configMessage.textContent = error.message;
  } finally {
    refreshCandidatesButton.disabled = false;
    updateApplyButton();
  }
}

function updateRemoveButton() {
  removeStaleButton.disabled = staleList.querySelectorAll("input:checked").length === 0;
}

async function removeStale() {
  const ids = [...staleList.querySelectorAll("input:checked")].map((item) => item.value);
  if (!window.confirm(`${ids.length}件の設定を削除しますか？`)) return;
  try {
    const result = await requestJson("/api/config/remove", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    showToast(`${result.removed}件を削除しました。`);
    await loadButtons();
    await refreshCandidates();
  } catch (error) {
    showToast(error.message, true);
  }
}

function updateApplyButton() {
  applyCandidatesButton.disabled = candidateList.querySelectorAll("input:checked").length === 0;
}

async function applyCandidates() {
  const ids = [...candidateList.querySelectorAll("input:checked")].map((item) => item.value);
  applyCandidatesButton.disabled = true;
  try {
    const result = await requestJson("/api/config/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    configMessage.textContent = `${result.added}件を追加しました。`;
    await loadButtons();
    await refreshCandidates();
  } catch (error) {
    configMessage.textContent = error.message;
    updateApplyButton();
  }
}

async function refreshStatus() {
  refreshStatusButton.disabled = true;
  try {
    const [snapshot, roomData] = await Promise.all([
      requestJson("/api/status"),
      requestJson("/api/rooms"),
    ]);
    availableRooms = roomData.rooms || ["未分類"];
    renderStatus(snapshot);
  } catch (error) {
    const hasPreviousStatus = Boolean(statusCheckedAt.textContent);
    statusCheckedAt.textContent = `更新失敗: ${error.message}`;
    statusCheckedAt.classList.add("error-text");
    if (!hasPreviousStatus) {
      environmentList.replaceChildren(emptyText("環境情報を取得できませんでした。"));
      deviceStatusList.replaceChildren(emptyText(`状態を取得できませんでした: ${error.message}`));
      remoteList.replaceChildren(emptyText("赤外線リモコンを取得できませんでした。"));
    }
  } finally {
    refreshStatusButton.disabled = false;
  }
}

async function loadRooms() {
  const data = await requestJson("/api/rooms");
  availableRooms = data.rooms || ["未分類"];
}

async function addRoom() {
  const room = newRoomName.value.trim();
  if (!room || roomEditBusy) return;
  const previousRooms = [...availableRooms];
  if (!availableRooms.includes(room)) availableRooms = [...availableRooms, room];
  newRoomName.value = "";
  setRoomEditBusy(true);
  try {
    const data = await requestJson("/api/rooms", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room }),
    });
    availableRooms = data.rooms;
    setRoomEditBusy(false);
    showToast(`${room}を追加しました。`);
  } catch (error) {
    availableRooms = previousRooms;
    setRoomEditBusy(false);
    showToast(error.message, true);
  }
}

function optimisticDeviceDetail(action, value) {
  const details = {
    turn_on: { key: "power", value: "on" },
    turn_off: { key: "power", value: "off" },
    set_brightness: { key: "brightness", value },
    set_color: { key: "color", value },
    set_color_temperature: { key: "colorTemperature", value },
  };
  return details[action] || null;
}

async function moveRoom(room, direction) {
  if (roomEditBusy) return;
  const currentIndex = availableRooms.indexOf(room);
  const nextIndex = currentIndex + direction;
  if (currentIndex < 0 || nextIndex < 0 || nextIndex >= availableRooms.length) return;
  const rooms = [...availableRooms];
  [rooms[currentIndex], rooms[nextIndex]] = [rooms[nextIndex], rooms[currentIndex]];
  const previousRooms = availableRooms;
  availableRooms = rooms;
  setRoomEditBusy(true);
  try {
    const data = await requestJson("/api/rooms/order", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rooms }),
    });
    availableRooms = data.rooms;
    setRoomEditBusy(false);
    showToast("部屋の並び順を保存しました。");
  } catch (error) {
    availableRooms = previousRooms;
    setRoomEditBusy(false);
    showToast(error.message, true);
  }
}

async function removeRoom(room) {
  if (roomEditBusy) return;
  const confirmed = window.confirm(
    `「${room}」を削除しますか？\n所属するデバイスは「未分類」へ移動し、設定とマイセットは保持されます。`,
  );
  if (!confirmed) return;
  const previousRooms = [...availableRooms];
  const previousSnapshot = cloneSnapshot(latestStatusSnapshot);
  availableRooms = availableRooms.filter((item) => item !== room);
  latestStatusSnapshot?.devices?.forEach((device) => {
    if (device.room === room) device.room = "未分類";
  });
  setRoomEditBusy(true);
  try {
    const result = await requestJson(`/api/rooms/${encodeURIComponent(room)}`, { method: "DELETE" });
    availableRooms = result.rooms;
    setRoomEditBusy(false);
    const moved = result.moved_devices;
    showToast(moved > 0 ? `${room}を削除し、${moved}台を未分類へ移動しました。` : `${room}を削除しました。`);
  } catch (error) {
    availableRooms = previousRooms;
    if (previousSnapshot) latestStatusSnapshot = previousSnapshot;
    setRoomEditBusy(false);
    showToast(error.message, true);
  }
}

function setRoomEditBusy(busy) {
  roomEditBusy = busy;
  addRoomButton.disabled = busy;
  if (latestStatusSnapshot) renderStatus(latestStatusSnapshot);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const dark = theme === "dark";
  themeButton.textContent = dark ? "☀️" : "🌙";
  themeButton.setAttribute("aria-label", dark ? "ライトモードに切り替え" : "ダークモードに切り替え");
}

async function loadDesktopStatus() {
  try {
    const status = await requestJson("/api/desktop");
    desktopAutostart.checked = status.autostart_enabled;
    desktopAutostart.disabled = !status.available;
    openLogsButton.disabled = !status.available;
    desktopLogPath.textContent = `ログ: ${status.log_directory}`;
  } catch (error) {
    desktopAutostart.disabled = true;
    openLogsButton.disabled = true;
    desktopLogPath.textContent = error.message;
  }
}

async function updateDesktopAutostart() {
  const enabled = desktopAutostart.checked;
  desktopAutostart.disabled = true;
  try {
    const result = await requestJson("/api/desktop/autostart", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    desktopAutostart.checked = result.autostart_enabled;
    showToast(result.autostart_enabled ? "自動起動を有効にしました。" : "自動起動を無効にしました。");
  } catch (error) {
    desktopAutostart.checked = !enabled;
    showToast(error.message, true);
  } finally {
    desktopAutostart.disabled = false;
  }
}

async function openDesktopLogs() {
  openLogsButton.disabled = true;
  try {
    await requestJson("/api/desktop/open-logs", { method: "POST" });
    showToast("ログフォルダを開きました。");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    openLogsButton.disabled = false;
  }
}

async function boot() {
  try {
    const health = await requestJson("/api/health");
    if (!health.ok) {
      throw new Error(health.error || "初期化に失敗しました。");
    }
    await Promise.all([loadButtons(), loadDesktopStatus()]);
    await refreshStatus();
    setStatus(true, "準備完了");
  } catch (error) {
    setStatus(false, "要確認");
    setResult(error.message, "", true);
  }
}

refreshStatusButton.addEventListener("click", refreshStatus);
refreshCandidatesButton.addEventListener("click", refreshCandidates);
applyCandidatesButton.addEventListener("click", applyCandidates);
addRoomButton.addEventListener("click", addRoom);
removeStaleButton.addEventListener("click", removeStale);
desktopAutostart.addEventListener("change", updateDesktopAutostart);
openLogsButton.addEventListener("click", openDesktopLogs);
editModeButton.addEventListener("click", () => {
  const editing = document.body.classList.toggle("edit-mode");
  editModeButton.textContent = editing ? "完了" : "編集";
  editModeButton.setAttribute("aria-pressed", String(editing));
});
themeButton.addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("switchbot-theme", theme);
  applyTheme(theme);
});
applyTheme(localStorage.getItem("switchbot-theme") || "light");
boot();
