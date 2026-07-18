const state = {
  view: "overview",
};

const titles = {
  overview: ["Overview", "System, assistant, and productivity snapshot."],
  chat: ["Chat", "Send commands or natural language prompts to STAR."],
  memory: ["Memory", "View and edit what STAR remembers."],
  tasks: ["Tasks", "Tasks, reminders, and focus timer."],
  voice: ["Voice", "Listening, language, speech, and confirmation controls."],
  integrations: ["Integrations", "Cloud sync, mobile queue, and smart home controls."],
  suggestions: ["Suggestions", "Smart actions STAR thinks are worth doing next."],
  analytics: ["Analytics", "Usage, tools, daily activity, and recent issues."],
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

async function safeApi(path, fallback, options = {}) {
  try {
    return await api(path, options);
  } catch (error) {
    console.warn(`Dashboard request failed: ${path}`, error);
    return fallback;
  }
}

function text(value, fallback = "n/a") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function checked(value) {
  return ["1", "true", "yes", "on", "enabled"].includes(String(value).toLowerCase());
}

function statusPill(label, ok) {
  return `<span class="pill ${ok ? "ok" : "warn"}">${escapeHtml(label)}</span>`;
}

function renderSettings(settings) {
  const rows = [
    ["Groq", settings.groq_configured ? "ready" : "missing"],
    ["Picovoice", settings.picovoice_configured ? "ready" : "missing"],
    ["Email", settings.email_configured ? "ready" : "missing"],
    ["Security", settings.security_mode || "normal"],
    ["Voice", settings.voice?.voice_language || "auto"],
    ["Pending", settings.pending_confirmation || "none"],
  ];

  $("#settingsList").innerHTML = rows
    .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`)
    .join("");
}

function renderMetrics(health) {
  const items = [
    ["Memory", health.memory_items],
    ["Contacts", health.contacts],
    ["Snippets", health.snippets],
    ["Finance", health.finance_transactions],
    ["Health", health.health_logs],
    ["Integrations", health.integrations],
    ["Mobile Queue", health.mobile_notifications],
    ["Tasks", health.open_tasks],
    ["Reminders", health.open_reminders],
    ["Calendar", health.upcoming_calendar_events],
    ["Automations", health.active_automations],
  ];

  $("#metrics").innerHTML = items
    .map(
      ([label, value]) => `
        <div class="metric">
          <div class="label">${escapeHtml(label)}</div>
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
    ["CPU", `${system.cpu?.usage_percent ?? 0}%`],
    ["RAM", `${system.memory?.usage_percent ?? 0}% used`],
    ["Disk", `${system.disk?.free_gb ?? 0} GB free`],
    ["Battery", battery],
    ["Network", `${system.network?.interfaces?.length ?? 0} interfaces`],
    ["Windows", `${system.windows?.system ?? "Windows"} ${system.windows?.release ?? ""}`],
  ];

  $("#systemGrid").innerHTML = items
    .map(([label, value]) => `<div class="system-item"><b>${escapeHtml(label)}</b><span>${escapeHtml(value)}</span></div>`)
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
          <div class="muted">${escapeHtml(item.category)} &middot; ${escapeHtml(item.updated_at)}</div>
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
          <span class="muted">#${item.id} &middot; ${escapeHtml(item.priority)} &middot; ${escapeHtml(item.status)}</span>
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
          <span class="muted">#${item.id} &middot; ${escapeHtml(item.due_at)} &middot; ${escapeHtml(item.status)}</span>
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
          <div class="muted">${escapeHtml(item.level)} &middot; ${escapeHtml(item.created_at)}</div>
        </div>
      `,
    )
    .join("");
}

function renderAnalytics(summary) {
  const commands = summary.commands || {};
  const productivity = summary.productivity || {};
  const memory = summary.memory || {};
  const usage = [
    ["Commands", commands.total_commands ?? 0],
    ["Success Rate", `${commands.success_rate ?? 0}%`],
    ["Memory Items", memory.total_memory_items ?? 0],
    ["Automation Runs", productivity.automation_runs ?? 0],
  ];

  $("#analyticsUsage").innerHTML = usage
    .map(([label, value]) => `<div class="system-item"><b>${escapeHtml(label)}</b><span>${escapeHtml(value)}</span></div>`)
    .join("");

  $("#analyticsTools").innerHTML = (commands.top_tools || [])
    .map((item) => `<div class="list-item"><b>${escapeHtml(item.tool)}</b><span>${item.count} command(s)</span></div>`)
    .join("") || `<div class="list-item">No tool usage yet.</div>`;

  $("#analyticsDaily").innerHTML = (summary.daily_commands || [])
    .map((item) => `<div class="list-item"><b>${escapeHtml(item.day)}</b><span>${item.count} command(s)</span></div>`)
    .join("") || `<div class="list-item">No daily activity yet.</div>`;

  const logs = summary.recent_errors?.logs || [];
  const commandsWithErrors = summary.recent_errors?.commands || [];
  const issues = [
    ...logs.map((item) => `${item.event}: ${item.details || ""}`),
    ...commandsWithErrors.map((item) => `${item.tool}: ${item.command}`),
  ];
  $("#analyticsErrors").innerHTML = issues
    .slice(0, 10)
    .map((item) => `<div class="list-item">${escapeHtml(item)}</div>`)
    .join("") || `<div class="list-item">No recent issues.</div>`;
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

function renderVoice(voice) {
  const settings = voice.settings || {};
  $("#voiceLanguage").value = settings.voice_language || "auto";
  $("#voiceMode").value = settings.voice_mode || "conversation";
  $("#voiceTimeout").value = settings.voice_timeout || "5";
  $("#voicePhraseLimit").value = settings.voice_phrase_time_limit || "6";
  $("#voicePause").value = settings.voice_pause_threshold || "0.8";
  $("#voiceEnergy").value = settings.voice_energy_threshold || "300";
  $("#ttsVoice").value = settings.tts_voice || "en-US-GuyNeural";
  $("#ttsRate").value = settings.tts_rate || "+5%";
  $("#ttsPitch").value = settings.tts_pitch || "+0Hz";
  $("#spokenConfirmations").checked = checked(settings.voice_spoken_confirmations);

  const items = [
    ["Mode", settings.voice_mode || "conversation"],
    ["Language", settings.voice_language || "auto"],
    ["Fallback", (voice.recognition_languages || []).join(", ") || "en-IN, hi-IN, en-US"],
    ["Timeout", `${settings.voice_timeout || 5}s`],
    ["Phrase", `${settings.voice_phrase_time_limit || 6}s`],
    ["Pending", voice.pending_confirmation || "none"],
  ];

  $("#voiceStatusGrid").innerHTML = items
    .map(([label, value]) => `<div class="system-item"><b>${escapeHtml(label)}</b><span>${escapeHtml(value)}</span></div>`)
    .join("");

  const last = voice.last || {};
  $("#voiceLastList").innerHTML = `
    <div class="list-item">
      <b>Last Command</b>
      <span>${escapeHtml(last.last_command || "none")}</span>
    </div>
    <div class="list-item">
      <b>Last Reply</b>
      <span>${escapeHtml(last.last_reply || "none")}</span>
    </div>
  `;
}

function renderIntegrations(status, integrations, mobile, smartHome) {
  const cloud = status.cloud || {};
  const mobileStatus = status.mobile || {};
  const smartStatus = status.smart_home || {};
  const items = [
    ["Cloud", statusPill(cloud.configured ? "configured" : "local", true)],
    ["Sync Dir", escapeHtml(cloud.sync_dir || "cloud_sync")],
    ["Mobile", `${mobileStatus.queued_notifications ?? 0} queued`],
    ["Smart Home", statusPill(smartStatus.configured ? "configured" : "missing", !!smartStatus.configured)],
  ];

  $("#integrationStatusGrid").innerHTML = items
    .map(([label, value]) => `<div class="system-item"><b>${escapeHtml(label)}</b><span>${value}</span></div>`)
    .join("");

  $("#mobileList").innerHTML = (mobile.items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.title)}</b>
          <span>${escapeHtml(item.body)}</span>
          <div class="muted">#${item.id} &middot; ${escapeHtml(item.status)} &middot; ${escapeHtml(item.created_at)}</div>
          <div class="item-actions">
            <button class="button small secondary" data-read-mobile="${item.id}">Read</button>
            <button class="button small danger" data-delete-mobile="${item.id}">Delete</button>
          </div>
        </div>
      `,
    )
    .join("") || `<div class="list-item">No queued mobile notifications.</div>`;

  $("#smartHomeGrid").innerHTML = `
    <div class="system-item"><b>Configured</b><span>${smartHome.configured ? "yes" : "no"}</span></div>
    <div class="system-item"><b>Status</b><span>${escapeHtml(smartHome.status || "not_configured")}</span></div>
  `;

  $("#integrationsList").innerHTML = (integrations.items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.name)}</b>
          <span>${escapeHtml(item.kind)} &middot; ${escapeHtml(item.status)}</span>
          <div class="muted">#${item.id} &middot; ${escapeHtml(item.updated_at)}</div>
          <div class="item-actions">
            <button class="button small danger" data-delete-integration="${item.id}">Delete</button>
          </div>
        </div>
      `,
    )
    .join("") || `<div class="list-item">No saved integrations yet.</div>`;
}

function renderSuggestions(items) {
  $("#suggestionsList").innerHTML = (items || [])
    .map(
      (item) => `
        <div class="list-item">
          <b>${escapeHtml(item.title)}</b>
          <span>${escapeHtml(item.reason)}</span>
          <div class="muted">Command: ${escapeHtml(item.command)}</div>
          <div class="item-actions">
            <button class="button small" data-run-suggestion="${escapeHtml(item.command)}">Run</button>
            <button class="button small secondary" data-suggestion-key="${escapeHtml(item.key)}" data-suggestion-action="accept">Accept</button>
            <button class="button small secondary" data-suggestion-key="${escapeHtml(item.key)}" data-suggestion-action="snooze">Snooze</button>
            <button class="button small danger" data-suggestion-key="${escapeHtml(item.key)}" data-suggestion-action="dismiss">Dismiss</button>
          </div>
        </div>
      `,
    )
    .join("") || `<div class="list-item">No smart suggestions right now.</div>`;
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
  const [
    health,
    settings,
    system,
    commands,
    memory,
    tasks,
    reminders,
    logs,
    history,
    analytics,
    voice,
    suggestions,
    integrationStatus,
    integrations,
    mobile,
    smartHome,
  ] = await Promise.all([
    safeApi("/health", {}),
    safeApi("/settings", {}),
    safeApi("/system", {}),
    safeApi("/commands?limit=8", { items: [] }),
    safeApi("/memory?limit=50", { items: [] }),
    safeApi("/tasks?limit=20", { items: [] }),
    safeApi("/reminders?limit=20", { items: [] }),
    safeApi("/logs?limit=30", { items: [] }),
    safeApi("/history?limit=30", { items: [] }),
    safeApi("/analytics", {}),
    safeApi("/voice/status", { settings: {}, recognition_languages: [], last: {} }),
    safeApi("/suggestions?limit=10", { items: [] }),
    safeApi("/integrations/status", { cloud: {}, mobile: {}, smart_home: {} }),
    safeApi("/integrations?limit=30", { items: [] }),
    safeApi("/mobile/notifications?status=queued&limit=20", { items: [] }),
    safeApi("/smart-home/status", { configured: false, status: "not_configured" }),
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
  renderAnalytics(analytics);
  renderVoice(voice);
  renderSuggestions(suggestions.items);
  renderIntegrations(integrationStatus, integrations, mobile, smartHome);
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
  $("#voiceStopBtn").addEventListener("click", async () => {
    await api("/stop");
    await refreshAll();
  });

  $("#briefingBtn").addEventListener("click", async () => {
    const result = await api("/briefing");
    $("#briefingText").textContent = result.briefing || "";
  });

  $("#repeatVoiceBtn").addEventListener("click", async () => {
    const result = await api("/voice/repeat", { method: "POST" });
    addMessage("assistant", result.reply || "");
    await refreshAll();
  });

  $("#confirmBtn").addEventListener("click", async () => {
    const result = await api("/confirm", { method: "POST" });
    addMessage("assistant", result.reply || "");
    await refreshAll();
  });

  $("#cancelBtn").addEventListener("click", async () => {
    const result = await api("/cancel", { method: "POST" });
    addMessage("assistant", result.reply || "");
    await refreshAll();
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

  $("#voiceForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const params = new URLSearchParams({
      language: $("#voiceLanguage").value,
      mode: $("#voiceMode").value,
      timeout: $("#voiceTimeout").value,
      phrase_time_limit: $("#voicePhraseLimit").value,
      pause_threshold: $("#voicePause").value,
      energy_threshold: $("#voiceEnergy").value,
      spoken_confirmations: String($("#spokenConfirmations").checked),
      tts_voice: $("#ttsVoice").value,
      tts_rate: $("#ttsRate").value,
      tts_pitch: $("#ttsPitch").value,
    });
    await api(`/voice/settings?${params.toString()}`, { method: "POST" });
    await refreshAll();
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

  $("#mobileForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = $("#mobileTitle").value.trim();
    const body = $("#mobileBody").value.trim();
    if (!title || !body) return;
    await api(`/mobile/notifications?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`, { method: "POST" });
    $("#mobileTitle").value = "";
    $("#mobileBody").value = "";
    await refreshAll();
  });

  $("#cloudSyncBtn").addEventListener("click", async () => {
    const result = await api("/cloud/sync", { method: "POST" });
    addMessage("assistant", `Cloud sync ${result.status}: ${result.path || ""}`);
    await refreshAll();
  });

  $("#smartHomeRefreshBtn").addEventListener("click", refreshAll);

  $("#smartHomeForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const entity = $("#smartEntity").value.trim();
    const service = $("#smartService").value;
    if (!entity) return;
    const domain = entity.includes(".") ? entity.split(".")[0] : "homeassistant";
    const result = await api(`/smart-home/service?domain=${encodeURIComponent(domain)}&service=${encodeURIComponent(service)}&entity_id=${encodeURIComponent(entity)}`, { method: "POST" });
    $("#smartHomeResult").textContent = `Smart home result: ${result.status || "unknown"}.`;
    await refreshAll();
  });

  $("#integrationForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = $("#integrationName").value.trim();
    const kind = $("#integrationKind").value.trim();
    if (!name || !kind) return;
    await api(`/integrations?name=${encodeURIComponent(name)}&kind=${encodeURIComponent(kind)}`, { method: "POST" });
    $("#integrationName").value = "";
    $("#integrationKind").value = "";
    await refreshAll();
  });

  $("#suggestionsRefreshBtn").addEventListener("click", refreshAll);

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

    if (target.dataset.readMobile) {
      await api(`/mobile/notifications/${target.dataset.readMobile}/read`, { method: "POST" });
      await refreshAll();
    }

    if (target.dataset.deleteMobile) {
      await api(`/mobile/notifications/${target.dataset.deleteMobile}`, { method: "DELETE" });
      await refreshAll();
    }

    if (target.dataset.deleteIntegration) {
      await api(`/integrations/${target.dataset.deleteIntegration}`, { method: "DELETE" });
      await refreshAll();
    }

    if (target.dataset.runSuggestion) {
      switchView("chat");
      await sendCommand(target.dataset.runSuggestion);
    }

    if (target.dataset.suggestionKey && target.dataset.suggestionAction) {
      const params = new URLSearchParams({
        key: target.dataset.suggestionKey,
        action: target.dataset.suggestionAction,
      });
      await api(`/suggestions/feedback?${params.toString()}`, { method: "POST" });
      await refreshAll();
    }
  });
}

bindEvents();
refreshAll().catch((error) => {
  addMessage("assistant", `Dashboard load failed: ${error.message}`);
});
