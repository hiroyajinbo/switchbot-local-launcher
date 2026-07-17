const buttonList = document.querySelector("#buttonList");
const applyCandidatesButton = document.querySelector("#applyCandidatesButton");
const addRoomButton = document.querySelector("#addRoomButton");
const candidateList = document.querySelector("#candidateList");
const configMessage = document.querySelector("#configMessage");
const deviceStatusList = document.querySelector("#deviceStatusList");
const environmentList = document.querySelector("#environmentList");
const editModeButton = document.querySelector("#editModeButton");
const historyList = document.querySelector("#historyList");
const historyCount = document.querySelector("#historyCount");
const newRoomName = document.querySelector("#newRoomName");
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
  buttonList.replaceChildren();
  buttons = buttons.filter((button) => button.type === "scene");
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
      element.textContent = button.label;
      element.disabled = button.locked;
      element.addEventListener("click", () => executeAction(button));
      const lock = document.createElement("button");
      lock.type = "button";
      lock.className = `scene-lock${button.locked ? " locked" : ""}`;
      lock.title = button.locked ? "シーンのロックを解除" : "シーンをロック";
      lock.innerHTML = svgIcon(button.locked ? "locked" : "unlocked");
      lock.addEventListener("click", () => setSceneLock(button.id, !button.locked));
      wrapper.append(element, lock);
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
    const orderControls = document.createElement("div");
    orderControls.className = "room-order-controls edit-only";
    const up = controlButton("↑", () => moveRoom(room, -1));
    up.title = `${room}を上へ移動`;
    up.disabled = availableRooms.indexOf(room) <= 0;
    const down = controlButton("↓", () => moveRoom(room, 1));
    down.title = `${room}を下へ移動`;
    const configuredIndex = availableRooms.indexOf(room);
    down.disabled = configuredIndex < 0 || configuredIndex >= availableRooms.length - 1;
    orderControls.append(up, down);
    headingRow.append(heading, orderControls);
    const grid = document.createElement("div");
    grid.className = "room-device-grid";
    section.append(headingRow, grid);
    roomItems.forEach((item) => {
    const element = document.createElement("div");
    element.className = `device-row${item.locked ? " locked" : ""}`;
    element.dataset.deviceId = item.device_id;
    const details = detailList(item.details);
    if (item.controls?.power) details.querySelector('[data-detail-key="power"]')?.remove();
    if (item.controls?.power || item.controls?.brightness || item.controls?.press) {
      details.append(deviceControls(item));
    }
    details.append(preferenceControls(item));
    element.append(deviceMainWithIcon(item), details);
    grid.append(element);
    });
    deviceStatusList.append(section);
  });

  errors.forEach((error) => {
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
    controls.append(toggle);
  }
  if (item.controls.press) {
    controls.append(controlButton("押す", () => controlDevice(item, "press")));
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
    controls.append(range, value);
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
    controls.append(color);
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
    controls.append(temperature, value);
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
  controls.append(room, lock);
  return controls;
}

function deviceMainWithIcon(item) {
  const wrapper = deviceMain(item.label, item.type, item.summary);
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
    light: '<path d="M9 18h6M10 22h4M8 14a7 7 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z"/>',
    strip_light: '<path d="M4 7h14a3 3 0 0 1 0 6H8a2 2 0 0 0 0 4h12"/><circle cx="4" cy="7" r="1"/>',
    plug: '<path d="M8 3v6m8-6v6M6 9h12v2a6 6 0 0 1-6 6v4"/>',
    bot: '<rect x="5" y="5" width="14" height="14" rx="4"/><circle cx="12" cy="12" r="3"/>',
    sensor: '<path d="M4 12a8 8 0 0 1 8-8m-8 8a8 8 0 0 0 8 8m-4-8a4 4 0 0 1 4-4m-4 4a4 4 0 0 0 4 4"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    hub: '<rect x="4" y="6" width="16" height="12" rx="3"/><path d="M8 13h8M12 9v8"/>',
    climate: '<path d="M7 5h10M5 9h14M7 13h10M9 17h6"/><path d="M4 3v16h16V3"/>',
    appliance: '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="13" r="4"/><path d="M8 7h1m2 0h1"/>',
    other: '<path d="M12 3 3 9v10h18V9l-9-6Z"/><path d="M9 19v-6h6v6"/>',
    locked: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    unlocked: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M16 10V7a4 4 0 0 0-7-2"/>',
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[icon] || paths.other}</svg>`;
}

async function savePreference(item, changes) {
  try {
    await requestJson(`/api/devices/${item.device_id}/preference`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room: item.room || "未分類", icon: item.icon, locked: item.locked, ...changes }),
    });
    await refreshStatus();
  } catch (error) {
    setResult(error.message, new Date().toLocaleString("ja-JP"), true);
  }
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
  setDeviceBusy(item, true, `${operationLabel(action)}を操作中...`);
  setResult(`${item.label} 操作中...`);
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
    const detailKey = ({
      turn_on: "power",
      turn_off: "power",
      set_brightness: "brightness",
      set_color: "color",
      set_color_temperature: "colorTemperature",
    })[action];
    if (detailKey) {
      const detailValue = action === "turn_on" ? "on" : action === "turn_off" ? "off" : value;
      setPendingDeviceDetail(item.device_id, detailKey, detailValue);
    }
    if (action === "set_brightness") {
      updateDisplayedBrightness(item.device_id, value);
      scheduleStatusRefresh(5000);
    } else {
      scheduleStatusRefresh(2000);
    }
    return true;
  } catch (error) {
    rollback?.();
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

function updateDisplayedBrightness(deviceId, brightness) {
  const row = document.querySelector(`[data-device-id="${CSS.escape(deviceId)}"]`);
  if (!row) return;
  const pill = row.querySelector('[data-detail-key="brightness"]');
  if (pill) pill.textContent = `明るさ: ${brightness}`;
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
  return `${label}: ${detail.value}${suffix}`;
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
    const snapshot = await requestJson("/api/status");
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
  if (!room) return;
  const data = await requestJson("/api/rooms", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room }),
  });
  availableRooms = data.rooms;
  newRoomName.value = "";
  await refreshStatus();
}

async function moveRoom(room, direction) {
  const currentIndex = availableRooms.indexOf(room);
  const nextIndex = currentIndex + direction;
  if (currentIndex < 0 || nextIndex < 0 || nextIndex >= availableRooms.length) return;
  const rooms = [...availableRooms];
  [rooms[currentIndex], rooms[nextIndex]] = [rooms[nextIndex], rooms[currentIndex]];
  try {
    const data = await requestJson("/api/rooms/order", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rooms }),
    });
    availableRooms = data.rooms;
    await refreshStatus();
    showToast("部屋の並び順を保存しました。");
  } catch (error) {
    showToast(error.message, true);
  }
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const dark = theme === "dark";
  themeButton.textContent = dark ? "☀️" : "🌙";
  themeButton.setAttribute("aria-label", dark ? "ライトモードに切り替え" : "ダークモードに切り替え");
}

async function boot() {
  try {
    const health = await requestJson("/api/health");
    if (!health.ok) {
      throw new Error(health.error || "初期化に失敗しました。");
    }
    await loadButtons();
    await loadRooms();
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
