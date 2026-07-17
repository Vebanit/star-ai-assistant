const state = {
  view: "overview",
};

const titles = {
  overview: ["Overview", "System, assistant, and productivity snapshot."],
  chat: ["Chat", "Send commands or natural language prompts to STAR."],
  memory: ["Memory", "View and edit what STAR remembers."],
  tasks: ["Tasks", "Tasks, reminders, and focus timer."],
  logs: ["Logs", "Command, app, and conversation history."],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function text(value, fallback = "n/a") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function renderSettings(settings) {
  const rows = [
    ["Groq", settings.groq_configured ? "ready" : "missing"],
    ["Picovoice", settings.picovoice_configured ? "ready" : "missing"],
    ["Pending", settings.pending_confirmation || "none"],
  ];

  $("#settingsList").innerHTML = rows
    .map(([key, value]) => `<div><dt>${key}</dt><dd>${value}</dd></div>`)
    .join("");
}

function renderMetrics(health) {
  const items = [
    ["Memory", health.memory_items],
    ["Tasks", health.open_tasks],
    ["Reminders", health.open_reminders],
    ["Logs", health.logs],
  ];

  $("#metrics").innerHTML = items
    .map(
      ([label, value]) => `
        <div class="metric">
          <div class="label">${label}</div>
          <div class="value">${text(value, "0")}</div>
        </div>
      `,
    )
    .join("");
}

function renderSystem(system) {
  const battery = system.battery?.available
    ? `${system.battery.percent}% ${system.battery.plugged_in ? "charging" : "battery"}`
    : "not available";

  const items = [
    ["CPU", `${system.cpu.usage_percent}%`],
    ["RAM", `${system.memory.usage_percent}% used`],
    ["Disk", `${system.disk.free_gb} GB free`],
    ["Battery", battery],
    ["Network", `${system.network.interfaces.length} interfaces`],
    ["Windows", `${system.windows.system} ${system.windows.release}`],
  ];

  $("#systemGrid").innerHTML = items
    .map(([label, value]) => `<div class="system-item"><b>${label}</b><span>${value}</span></div>`)
    .join("");
}

function renderCommands(items) {
  $("#commandsTable").innerHTML = (items || [])
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.command)}</td>
          <td>${escapeHtml(item.tool)}</td>
          <td>${escapeHtml(item.status)}</td>
          <td>${escapeHtml(item.created_at)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderMemory(items) {
  $("#memoryList").innerHTML = (items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.key)}</b>
          <span>${escapeHtml(item.value)}</span>
          <div class="muted">${escapeHtml(item.category)} · ${escapeHtml(item.updated_at)}</div>
          <div class="item-actions">
            <button class="button small secondary" data-delete-memory="${escapeHtml(item.key)}">Forget</button>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderTasks(items) {
  $("#taskList").innerHTML = (items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.title)}</b>
          <span class="muted">#${item.id} · ${escapeHtml(item.priority)} · ${escapeHtml(item.status)}</span>
          <div class="item-actions">
            <button class="button small secondary" data-complete-task="${item.id}">Complete</button>
            <button class="button small danger" data-delete-task="${item.id}">Delete</button>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderReminders(items) {
  $("#reminderList").innerHTML = (items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.text)}</b>
          <span class="muted">#${item.id} · ${escapeHtml(item.due_at)} · ${escapeHtml(item.status)}</span>
          <div class="item-actions">
            <button class="button small secondary" data-complete-reminder="${item.id}">Complete</button>
            <button class="button small danger" data-delete-reminder="${item.id}">Delete</button>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderLogs(items) {
  $("#logsList").innerHTML = (items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.event)}</b>
          <span>${escapeHtml(item.details || "")}</span>
          <div class="muted">${escapeHtml(item.level)} · ${escapeHtml(item.created_at)}</div>
        </div>
      `,
    )
    .join("");
}

function renderHistory(items) {
  $("#historyList").innerHTML = (items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.role)}</b>
          <span>${escapeHtml(item.content)}</span>
          <div class="muted">${escapeHtml(item.created_at)}</div>
        </div>
      `,
    )
    .join("");
}

function addMessage(role, content) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = content;
  $("#chatLog").appendChild(node);
  $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
}

async function sendCommand(command) {
  if (!command.trim()) return;
  addMessage("user", command);
  const result = await api(`/ask-star?q=${encodeURIComponent(command)}`);
  addMessage("assistant", result.reply || "");
  await refreshAll();
}

async function refreshAll() {
  const [health, settings, system, commands, memory, tasks, reminders, logs, history] = await Promise.all([
    api("/health"),
    api("/settings"),
    api("/system"),
    api("/commands?limit=8"),
    api("/memory?limit=50"),
    api("/tasks?limit=20"),
    api("/reminders?limit=20"),
    api("/logs?limit=30"),
    api("/history?limit=30"),
  ]);

  renderMetrics(health);
  renderSettings(settings);
  renderSystem(system);
  renderCommands(commands.items);
  renderMemory(memory.items);
  renderTasks(tasks.items);
  renderReminders(reminders.items);
  renderLogs(logs.items);
  renderHistory(history.items);
}

function switchView(view) {
  state.view = view;
  $$(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  $$(".view").forEach((panel) => panel.classList.remove("active"));
  $(`#${view}View`).classList.add("active");
  $("#viewTitle").textContent = titles[view][0];
  $("#viewSubtitle").textContent = titles[view][1];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  $$(".nav-item").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });

  $("#refreshBtn").addEventListener("click", refreshAll);
  $("#stopBtn").addEventListener("click", async () => {
    await api("/stop");
    await refreshAll();
  });

  $("#briefingBtn").addEventListener("click", async () => {
    const result = await api("/briefing");
    $("#briefingText").textContent = result.briefing || "";
  });

  $$(".quick").forEach((button) => {
    button.addEventListener("click", () => sendCommand(button.dataset.command));
  });

  $("#chatForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("#chatInput");
    const command = input.value;
    input.value = "";
    await sendCommand(command);
  });

  $("#memoryForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const key = $("#memoryKey").value.trim();
    const value = $("#memoryValue").value.trim();
    if (!key || !value) return;
    await api(`/memory?key=${encodeURIComponent(key)}&value=${encodeURIComponent(value)}`, { method: "POST" });
    $("#memoryKey").value = "";
    $("#memoryValue").value = "";
    await refreshAll();
  });

  $("#taskForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = $("#taskTitle").value.trim();
    if (!title) return;
    await api(`/tasks?title=${encodeURIComponent(title)}`, { method: "POST" });
    $("#taskTitle").value = "";
    await refreshAll();
  });

  $("#reminderForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const textValue = $("#reminderText").value.trim();
    const due = $("#reminderDue").value.trim();
    if (!textValue || !due) return;
    await api(`/reminders?text=${encodeURIComponent(textValue)}&due=${encodeURIComponent(due)}`, { method: "POST" });
    $("#reminderText").value = "";
    $("#reminderDue").value = "";
    await refreshAll();
  });

  document.body.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    if (target.dataset.deleteMemory) {
      await api(`/memory/${encodeURIComponent(target.dataset.deleteMemory)}`, { method: "DELETE" });
      await refreshAll();
    }

    if (target.dataset.completeTask) {
      await api(`/tasks/${target.dataset.completeTask}/complete`, { method: "POST" });
      await refreshAll();
    }

    if (target.dataset.deleteTask) {
      await api(`/tasks/${target.dataset.deleteTask}`, { method: "DELETE" });
      await refreshAll();
    }

    if (target.dataset.completeReminder) {
      await api(`/reminders/${target.dataset.completeReminder}/complete`, { method: "POST" });
      await refreshAll();
    }

    if (target.dataset.deleteReminder) {
      await api(`/reminders/${target.dataset.deleteReminder}`, { method: "DELETE" });
      await refreshAll();
    }
  });
}

bindEvents();
refreshAll().catch((error) => {
  addMessage("assistant", `Dashboard load failed: ${error.message}`);
});
