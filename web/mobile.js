const state = {
  wakeEnabled: false,
  awake: false,
  recognition: null,
  restarting: false,
  wakePhrases: ["hello star", "hey star", "star"],
};

const $ = (selector) => document.querySelector(selector);

function getSecret() {
  return localStorage.getItem("star_mobile_secret") || "";
}

function setSecret(value) {
  localStorage.setItem("star_mobile_secret", value || "");
}

function apiPath(path, params = {}) {
  const url = new URL(path, window.location.origin);
  const secret = getSecret();
  if (secret) url.searchParams.set("secret", secret);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return url.toString();
}

async function api(path, params = {}, options = {}) {
  const response = await fetch(apiPath(path, params), options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^\w\s'.-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function wakeMatch(text) {
  const clean = normalize(text);
  for (const phrase of state.wakePhrases) {
    if (clean === phrase || clean.startsWith(`${phrase} `)) {
      return { phrase, command: clean.slice(phrase.length).trim() };
    }
  }
  return null;
}

function isSleepCommand(text) {
  const clean = normalize(text);
  return [
    "sleep",
    "u can sleep",
    "you can sleep",
    "go to sleep",
    "stop listening",
    "sunna band",
    "so ja",
    "ab so ja",
    "sleep mode",
  ].some((phrase) => clean === phrase || clean.includes(phrase));
}

function setUi() {
  const title = state.awake ? "Listening" : state.wakeEnabled ? "Wake only" : "Idle";
  $("#wakeTitle").textContent = title;
  $("#wakeLabel").textContent = title;
  $("#statusText").textContent = state.awake
    ? "STAR is taking mobile voice commands."
    : state.wakeEnabled
      ? "Say hello star to start command mode."
      : "Tap Start Wake to keep mobile wake listening on.";

  $("#statusDot").className = `status-dot ${state.awake ? "awake" : state.wakeEnabled ? "live" : ""}`;
  $("#wakePad").className = `wake-pad ${state.awake ? "awake" : state.wakeEnabled ? "live" : ""}`;
  $("#startWakeBtn").textContent = state.wakeEnabled ? "Stop Wake" : "Start Wake";
}

function speakMobile(text) {
  if (!text) return;
  if (!("speechSynthesis" in window)) {
    $("#replyBox").textContent = `${text}\n\nPhone speech is not available in this browser.`;
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = $("#languageSelect").value || "en-IN";
  window.speechSynthesis.speak(utterance);
}

async function sendCommand(command, source = "mobile") {
  const clean = command.trim();
  if (!clean) return;
  $("#commandInput").value = "";
  $("#replyBox").textContent = "Working...";
  try {
    const result = await api("/mobile/command", { command: clean, source }, { method: "POST" });
    if (!result.authorized) {
      $("#replyBox").textContent = result.error || "Mobile auth failed.";
      return;
    }
    const reply = result.reply || "";
    $("#replyBox").textContent = reply || "Done.";
    if (reply) speakMobile(reply);
    if (result.voice?.sleep_requested || isSleepCommand(clean)) {
      state.awake = false;
      setUi();
    }
    await loadNotifications();
  } catch (error) {
    $("#replyBox").textContent = `Mobile command failed: ${error.message}`;
  }
}

function handleTranscript(transcript) {
  const clean = normalize(transcript);
  if (!clean) return;
  $("#replyBox").textContent = `Heard: ${clean}`;

  if (!state.awake) {
    const wake = wakeMatch(clean);
    if (!wake) return;
    state.awake = true;
    setUi();
    speakMobile("Haan bhai, bol.");
    if (wake.command) sendCommand(wake.command, "mobile_voice");
    return;
  }

  const wake = wakeMatch(clean);
  if (wake) {
    if (wake.command) sendCommand(wake.command, "mobile_voice");
    return;
  }
  sendCommand(clean, "mobile_voice");
}

function createRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    $("#replyBox").textContent = "Speech recognition is not available in this mobile browser.";
    return null;
  }
  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = false;
  recognition.lang = $("#languageSelect").value || "en-IN";
  recognition.onresult = (event) => {
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      if (event.results[index].isFinal) handleTranscript(event.results[index][0].transcript);
    }
  };
  recognition.onerror = (event) => {
    $("#replyBox").textContent = `Mic error: ${event.error}`;
  };
  recognition.onend = () => {
    if (!state.wakeEnabled || state.restarting) return;
    state.restarting = true;
    window.setTimeout(() => {
      state.restarting = false;
      startRecognition();
    }, 500);
  };
  return recognition;
}

function startRecognition() {
  if (!state.recognition) state.recognition = createRecognition();
  if (!state.recognition) return;
  state.recognition.lang = $("#languageSelect").value || "en-IN";
  try {
    state.recognition.start();
  } catch (error) {
    if (!String(error.message || "").includes("started")) {
      $("#replyBox").textContent = `Mic start failed: ${error.message}`;
    }
  }
}

function stopRecognition() {
  if (!state.recognition) return;
  try {
    state.recognition.stop();
  } catch (error) {
    console.warn("Recognition stop failed", error);
  }
}

async function loadStatus() {
  try {
    const result = await api("/mobile/status");
    if (!result.authorized) {
      $("#replyBox").textContent = result.error || "Mobile auth failed.";
      return;
    }
    state.wakePhrases = result.voice?.wake_phrases?.length ? result.voice.wake_phrases : state.wakePhrases;
    $("#statusText").textContent = `Server ${result.server}. ${result.notifications || 0} queued notification(s).`;
  } catch (error) {
    $("#statusText").textContent = `Server check failed: ${error.message}`;
  }
}

async function loadNotifications() {
  try {
    const result = await api("/mobile/pull", { limit: 20 });
    if (!result.authorized) {
      $("#notificationsList").innerHTML = `<div class="notice">${escapeHtml(result.error || "Mobile auth failed.")}</div>`;
      return;
    }
    $("#notificationsList").innerHTML = (result.items || [])
      .map(
        (item) => `
          <div class="notice">
            <b>${escapeHtml(item.title)}</b>
            <span>${escapeHtml(item.body)}</span>
          </div>
        `,
      )
      .join("") || `<div class="notice">No queued notifications.</div>`;
  } catch (error) {
    $("#notificationsList").innerHTML = `<div class="notice">Notification sync failed: ${escapeHtml(error.message)}</div>`;
  }
}

function bindEvents() {
  $("#secretInput").value = getSecret();
  $("#secretInput").addEventListener("change", (event) => {
    setSecret(event.target.value.trim());
    loadStatus();
    loadNotifications();
  });

  $("#startWakeBtn").addEventListener("click", () => {
    state.wakeEnabled = !state.wakeEnabled;
    if (!state.wakeEnabled) {
      state.awake = false;
      stopRecognition();
    } else {
      startRecognition();
    }
    setUi();
  });

  $("#sleepBtn").addEventListener("click", async () => {
    state.awake = false;
    await api("/voice/sleep", {}, { method: "POST" });
    setUi();
  });

  $("#commandForm").addEventListener("submit", (event) => {
    event.preventDefault();
    state.awake = true;
    setUi();
    sendCommand($("#commandInput").value, "mobile_text");
  });

  $("#languageSelect").addEventListener("change", () => {
    if (state.wakeEnabled) {
      stopRecognition();
      window.setTimeout(startRecognition, 300);
    }
  });

  $("#refreshBtn").addEventListener("click", loadNotifications);
}

bindEvents();
setUi();
loadStatus();
loadNotifications();
window.setInterval(loadNotifications, 15000);
