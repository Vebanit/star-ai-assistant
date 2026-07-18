import contextvars
import datetime
import difflib
import glob
import json
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import psutil
import pyautogui
from ddgs import DDGS
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

import star_storage as storage
import star_system
import star_files
import star_research
import star_productivity
import star_browser
import star_media
import star_whatsapp
import star_coding
import star_git
import star_automation
import star_security
import star_analytics
import star_vision
import star_email
import star_calendar
import star_contacts
import star_clipboard
import star_emotion
import star_finance
import star_health
import star_integrations
import star_language
import star_suggestions
import star_voice


BASE_DIR = Path(__file__).resolve().parent
LEGACY_MEMORY_FILE = BASE_DIR / "star_memory.json"
SPEAKER_FILE = BASE_DIR / "speaker.py"
WEB_DIR = BASE_DIR / "web"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="STAR Assistant")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None

current_process = None
PENDING_CONFIRMATION = None
SPEECH_CONTEXT = None
ADAPTED_REPLY_CACHE = {}
SUPPRESS_TTS = contextvars.ContextVar("SUPPRESS_TTS", default=False)


def infer_memory_category(key):
    key = storage.normalize_key(key)
    if key in {"name", "city", "location", "birthday", "age"}:
        return "profile"
    if any(word in key for word in ["favourite", "favorite", "prefer", "like"]):
        return "preference"
    if any(word in key for word in ["project", "repo", "code"]):
        return "project"
    return "general"


def migrate_legacy_memory():
    if not LEGACY_MEMORY_FILE.exists():
        return

    try:
        with LEGACY_MEMORY_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        storage.add_log("warning", "legacy_memory_migration_failed", str(exc))
        return

    if not isinstance(data, dict):
        return

    migrated = 0
    for key, value in data.items():
        if storage.set_memory(key, value, infer_memory_category(key), "legacy_json"):
            migrated += 1

    if migrated:
        storage.add_log("info", "legacy_memory_migrated", {"items": migrated})


storage.init_db()
migrate_legacy_memory()


# ------------------- INTERNET ACCESS -------------------

def search_internet(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=3)
        return " ".join(result.get("body", "") for result in results)
    except Exception as exc:
        print("Internet search failed:", exc)
        return ""


# ------------------- TTS -------------------

def adapt_reply_for_context(reply, user_text=None):
    context = user_text or SPEECH_CONTEXT
    if not context:
        return str(reply or "")
    key = (str(context), str(reply or ""))
    if key not in ADAPTED_REPLY_CACHE:
        ADAPTED_REPLY_CACHE[key] = star_emotion.adapt_reply(reply, context, client=client)
    return ADAPTED_REPLY_CACHE[key]


def speak(text):
    global current_process

    if not text:
        return False

    if SUPPRESS_TTS.get():
        return False

    if star_voice.is_voice_quiet():
        return False

    text = adapt_reply_for_context(str(text))

    if current_process and current_process.poll() is None:
        current_process.terminate()

    try:
        voice_settings = star_voice.get_settings()
        speaker_env = os.environ.copy()
        speaker_env["STAR_TTS_VOICE"] = voice_settings.get("tts_voice", "en-US-JennyNeural")
        speaker_env["STAR_TTS_RATE"] = voice_settings.get("tts_rate", "+5%")
        speaker_env["STAR_TTS_PITCH"] = voice_settings.get("tts_pitch", "+0Hz")
        current_process = subprocess.Popen(
            [sys.executable, str(SPEAKER_FILE), str(text)],
            cwd=str(BASE_DIR),
            env=speaker_env,
        )
        return True
    except Exception as exc:
        print("Speech failed:", exc)
        return False


def stop_speaking():
    global current_process

    if current_process and current_process.poll() is None:
        current_process.terminate()
        current_process = None
        return True

    return False


# ------------------- BROWSER AUTOMATION -------------------

def create_chrome_driver():
    options = Options()
    profile_dir = os.getenv("STAR_CHROME_PROFILE_DIR") or str(BASE_DIR / "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def check_instagram():
    driver = None

    try:
        driver = create_chrome_driver()
        driver.get("https://www.instagram.com")

        speak("Login first")
        time.sleep(25)

        driver.get("https://www.instagram.com/direct/inbox/")
        time.sleep(10)

        chats = driver.find_elements(By.XPATH, "//div[contains(@class,'x1lliihq')]")
        if not chats:
            return "No Instagram chats found."

        chats[0].click()
        time.sleep(3)

        messages = driver.find_elements(By.XPATH, "//div[@role='row']")
        if not messages:
            return "No Instagram messages found."

        last_msg = messages[-1].text
        print("Last Instagram message:", last_msg)

        box = driver.find_element(By.TAG_NAME, "textarea")
        box.send_keys("Okay, I will respond later.")
        box.send_keys(Keys.ENTER)
        return "Instagram reply sent."
    except Exception as exc:
        print("Instagram automation failed:", exc)
        return "Instagram automation failed."
    finally:
        if driver:
            driver.quit()


def check_whatsapp():
    driver = None

    try:
        speak("Opening WhatsApp")
        driver = create_chrome_driver()
        driver.get("https://web.whatsapp.com")

        speak("Scan the QR code")
        time.sleep(20)

        chats = driver.find_elements(By.XPATH, "//span[@aria-label='Unread message']")
        if not chats:
            return "No unread WhatsApp messages found."

        replied = 0
        for chat in chats:
            chat.click()
            time.sleep(2)

            msgs = driver.find_elements(By.CSS_SELECTOR, "span.selectable-text")
            if msgs:
                print("WhatsApp message:", msgs[-1].text)

            box = driver.find_element(By.XPATH, "//div[@title='Type a message']")
            box.send_keys("Okay, I will respond later.")
            box.send_keys(Keys.ENTER)
            replied += 1
            time.sleep(2)

        return f"Replied to {replied} WhatsApp chat(s)."
    except Exception as exc:
        print("WhatsApp automation failed:", exc)
        return "WhatsApp automation failed."
    finally:
        if driver:
            driver.quit()


# ------------------- PC CONTROL -------------------

def scan_apps():
    start_menu_paths = [
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        os.path.join(
            os.path.expanduser("~"),
            r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        ),
    ]

    apps = {}
    for path in start_menu_paths:
        for file in glob.glob(path + "/**/*.lnk", recursive=True):
            name = os.path.basename(file).replace(".lnk", "").lower()
            apps[name] = file

    return apps


APP_DATABASE = scan_apps()

APP_ALIASES = {
    "calculator": "calc",
    "calc": "calc",
    "notepad": "notepad",
    "paint": "mspaint",
    "vs code": "code",
    "vscode": "code",
    "chrome": "chrome",
    "edge": "msedge",
    "task manager": "taskmgr",
    "control panel": "control",
    "whatsapp": "whatsapp:",
}

CLOSE_TARGETS = {
    "calculator": ["calculatorapp.exe", "calc.exe"],
    "calc": ["calculatorapp.exe", "calc.exe"],
    "notepad": ["notepad.exe"],
    "paint": ["mspaint.exe", "paintstudio.view.exe"],
    "vs code": ["code.exe"],
    "vscode": ["code.exe"],
    "chrome": ["chrome.exe"],
    "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "microsoft edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "brave": ["brave.exe"],
    "opera": ["opera.exe"],
    "task manager": ["taskmgr.exe"],
    "whatsapp": ["whatsapp.exe", "chrome.exe", "msedge.exe"],
    "youtube": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"],
    "google": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"],
    "gmail": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"],
    "github": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"],
    "browser": ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"],
}

CLOSE_VERBS = [
    "close",
    "exit",
    "quit",
    "kill",
    "stop app",
    "band karo",
    "band kar",
    "band",
    "bandh karo",
    "bandh kar",
    "bandh",
    "bnd karo",
    "bnd kar",
    "bnd",
    "बंद करो",
    "बंद कर",
    "बंद",
]

PROTECTED_CLOSE_PROCESSES = {
    "python.exe",
    "pythonw.exe",
    "uvicorn.exe",
    "powershell.exe",
    "pwsh.exe",
    "cmd.exe",
    "explorer.exe",
    "winlogon.exe",
    "csrss.exe",
    "services.exe",
    "lsass.exe",
}


def open_anything(command):
    cmd = command.lower().replace("open ", "", 1).strip()

    for key, target in APP_ALIASES.items():
        if key in cmd:
            speak(f"Opening {key}")
            subprocess.Popen(f'start "" {target}', shell=True)
            return True

    sites = {
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
    }

    for site, url in sites.items():
        if site in cmd:
            speak(f"Opening {site}")
            webbrowser.open(url)
            return True

    folders = {
        "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
    }

    for folder, path in folders.items():
        if folder in cmd:
            speak(f"Opening {folder}")
            os.startfile(path)
            return True

    match = difflib.get_close_matches(cmd, APP_DATABASE.keys(), n=1, cutoff=0.5)
    if match:
        app_name = match[0]
        speak(f"Opening {app_name}")
        os.startfile(APP_DATABASE[app_name])
        return True

    try:
        speak(f"Opening {cmd}")
        subprocess.Popen(f'start "" {cmd}', shell=True)
        return True
    except Exception as exc:
        print("Open command failed:", exc)
        return False


def close_target_from_command(command):
    text = str(command).lower().strip()
    for verb in CLOSE_VERBS:
        text = text.replace(verb, " ")
    text = " ".join(text.split()).strip()
    fillers = ["application", "window", "please", "krdo", "kardo", "kar do", "kar de"]
    for filler in fillers:
        text = text.replace(filler, " ")
    return " ".join(text.split()).strip()


def close_active_window(command):
    text = str(command).lower()
    if any(phrase in text for phrase in ["current tab", "close tab", "tab band", "tab bandh"]):
        pyautogui.hotkey("ctrl", "w")
        speak("Closing current tab")
        return True
    if any(phrase in text for phrase in ["current window", "active window", "close window", "window band", "window bandh"]):
        pyautogui.hotkey("alt", "f4")
        speak("Closing current window")
        return True
    return False


def find_processes_for_target(target):
    clean_target = target.lower().replace(".exe", "").strip()
    wanted_names = []
    for key, names in CLOSE_TARGETS.items():
        if key in clean_target or clean_target in key:
            wanted_names.extend(names)

    matches = []
    process_rows = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info.get("name") or ""
            lower_name = name.lower()
            if not lower_name or lower_name in PROTECTED_CLOSE_PROCESSES:
                continue
            process_rows.append((proc, lower_name))
            if lower_name in wanted_names:
                matches.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if matches:
        return matches

    for proc, lower_name in process_rows:
        base_name = lower_name.replace(".exe", "")
        if clean_target and (clean_target == base_name or clean_target in base_name or base_name in clean_target):
            matches.append(proc)

    if matches:
        return matches

    names = sorted({name for _, name in process_rows})
    match = difflib.get_close_matches(clean_target, names, n=1, cutoff=0.62)
    if not match:
        return []
    return [proc for proc, lower_name in process_rows if lower_name == match[0]]


def close_anything(command):
    if close_active_window(command):
        return True

    target = close_target_from_command(command)
    if not target:
        return False

    matches = find_processes_for_target(target)
    if not matches:
        return False

    closed = 0
    for proc in matches:
        try:
            proc.terminate()
            closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    gone, alive = psutil.wait_procs(matches, timeout=2)
    for proc in alive:
        try:
            proc.kill()
            closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if closed:
        speak(f"Closing {target}")
        return True
    return False


def take_screenshot():
    filename = f"screenshot_{datetime.datetime.now().strftime('%H%M%S')}.png"
    path = BASE_DIR / filename

    screenshot = pyautogui.screenshot()
    screenshot.save(path)
    speak("Screenshot taken")
    return True


def control_screen(command):
    cmd = command.lower()

    if "screenshot" in cmd:
        return take_screenshot()

    if "scroll down" in cmd:
        pyautogui.scroll(-500)
        speak("Scrolling down")
        return True

    if "scroll up" in cmd:
        pyautogui.scroll(500)
        speak("Scrolling up")
        return True

    if "click" in cmd:
        pyautogui.click()
        speak("Clicking")
        return True

    if "type" in cmd:
        text = cmd.replace("type", "", 1).strip()
        pyautogui.write(text)
        speak("Typing")
        return True

    return False


def search_web(command):
    cmd = command.lower()
    query = (
        cmd.replace("search", "", 1)
        .replace("google", "", 1)
        .replace("find", "", 1)
        .strip()
    )

    if not query:
        return False

    speak(f"Searching {query}")
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return True


def open_chrome_and_search(command):
    cmd = command.lower()
    if "open chrome and search" not in cmd:
        return False

    query = cmd.split("search", 1)[-1].strip()
    if not query:
        return False

    speak("Opening Chrome and searching")
    subprocess.Popen('start "" chrome', shell=True)
    time.sleep(2)
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return True


# ------------------- SYSTEM AGENT -------------------

def set_pending_confirmation(action, description, callback):
    global PENDING_CONFIRMATION
    PENDING_CONFIRMATION = {
        "action": action,
        "description": description,
        "callback": callback,
        "created_at": datetime.datetime.utcnow(),
    }
    return f"{description}. Say confirm to continue, or cancel."


def clear_pending_confirmation():
    global PENDING_CONFIRMATION
    PENDING_CONFIRMATION = None


def handle_confirmation_command(command):
    global PENDING_CONFIRMATION
    intent = star_voice.confirmation_intent(command)
    text = (intent or command).lower().strip()

    if text == "cancel":
        if PENDING_CONFIRMATION:
            star_security.audit("confirmation_cancelled", "info", {"action": PENDING_CONFIRMATION["action"]})
            clear_pending_confirmation()
            return "Cancelled."
        return None

    if text != "confirm":
        return None

    if not PENDING_CONFIRMATION:
        return "Nothing is waiting for confirmation."

    pending = PENDING_CONFIRMATION
    clear_pending_confirmation()

    try:
        star_security.audit("confirmation_approved", "warning", {"action": pending["action"]})
        return pending["callback"]()
    except Exception as exc:
        storage.add_log("error", "confirmed_action_failed", {"action": pending["action"], "error": str(exc)})
        return f"{pending['action']} failed."


def detect_system_command(user_text):
    text = user_text.lower()
    system_words = [
        "system",
        "cpu",
        "ram",
        "memory usage",
        "disk",
        "battery",
        "network",
        "windows info",
        "pc info",
        "running process",
        "running apps",
        "installed apps",
        "volume",
        "brightness",
        "shutdown",
        "restart pc",
        "reboot",
        "sleep",
        "lock pc",
        "cancel shutdown",
    ]
    return any(word in text for word in system_words)


def handle_system_command(command):
    text = command.lower()

    if "cancel shutdown" in text or "abort shutdown" in text:
        return star_system.cancel_power_action()

    if "shutdown" in text:
        return set_pending_confirmation("shutdown", "Shutdown requested", star_system.shutdown_pc)

    if "restart pc" in text or "reboot" in text:
        return set_pending_confirmation("restart", "Restart requested", star_system.restart_pc)

    if "sleep" in text and ("pc" in text or "computer" in text or text.strip() == "sleep"):
        return set_pending_confirmation("sleep", "Sleep mode requested", star_system.sleep_pc)

    if "lock pc" in text or "lock computer" in text:
        return set_pending_confirmation("lock", "Lock PC requested", star_system.lock_pc)

    if "volume" in text or "mute" in text:
        reply = star_system.control_volume(command)
        if reply:
            return reply

    if "brightness" in text:
        return star_system.control_brightness(command)

    if "running process" in text or "processes" in text:
        processes = star_system.list_processes(limit=8)
        names = [f"{item['name']} ({item['memory_percent']} percent memory)" for item in processes if item.get("name")]
        return "Top processes are " + ", ".join(names) + "." if names else "No running processes found."

    if "installed apps" in text or "running apps" in text:
        apps = star_system.list_installed_apps(APP_DATABASE, limit=10)
        names = [item["name"] for item in apps]
        return "Installed apps include " + ", ".join(names) + "." if names else "No installed apps found."

    status = star_system.get_system_status()

    if "cpu" in text:
        return f"CPU usage is {status['cpu']['usage_percent']} percent."

    if "ram" in text or "memory usage" in text:
        memory = status["memory"]
        return f"RAM usage is {memory['usage_percent']} percent, with {memory['available_gb']} GB available."

    if "disk" in text:
        disk = status["disk"]
        return f"Disk usage is {disk['usage_percent']} percent, with {disk['free_gb']} GB free."

    if "battery" in text:
        battery = status["battery"]
        if not battery.get("available"):
            return "Battery information is not available on this device."
        state = "charging" if battery["plugged_in"] else "not charging"
        return f"Battery is {battery['percent']} percent and {state}."

    if "network" in text:
        network = status["network"]
        return f"Network is available on {len(network['interfaces'])} interface(s)."

    if "windows info" in text or "pc info" in text:
        windows = status["windows"]
        return f"This is {windows['system']} {windows['release']} on {windows['machine']}."

    if "system" in text or "status" in text:
        return star_system.format_system_summary(status)

    return None


# ------------------- FILE AGENT -------------------

def text_after_any(text, phrases):
    lowered = text.lower()
    for phrase in phrases:
        if phrase in lowered:
            index = lowered.index(phrase)
            return text[index + len(phrase):].strip()
    return ""


def handle_file_command(command):
    text = command.strip()
    lower_text = text.lower()

    if any(phrase in lower_text for phrase in ["search files", "find files", "find file", "file search"]):
        query = text_after_any(text, ["search files", "find files", "find file", "file search"])
        if not query:
            return "Tell me what file to search for."

        results = star_files.search_files(query, limit=8)
        if not results:
            return f"No files found for {query}."

        names = [item["name"] for item in results[:5]]
        return "Found " + ", ".join(names) + "."

    if lower_text.startswith("read file") or lower_text.startswith("open file text"):
        path = text_after_any(text, ["read file", "open file text"])
        if not path:
            return "Tell me which file to read."

        result = star_files.read_file(path, max_chars=1800)
        if result.get("error"):
            return result["error"]
        return result["text"] or "The file is empty."

    if lower_text.startswith("summarize file") or lower_text.startswith("summary of file"):
        path = text_after_any(text, ["summarize file", "summary of file"])
        if not path:
            return "Tell me which file to summarize."

        result = star_files.read_file(path, max_chars=20000)
        if result.get("error"):
            return result["error"]

        summary = star_files.summarize_text(result["text"], max_sentences=5)
        return summary or "I could not summarize that file."

    if any(phrase in lower_text for phrase in ["analyze folder", "folder analysis", "analyse folder"]):
        folder = text_after_any(text, ["analyze folder", "folder analysis", "analyse folder"]) or "workspace"
        result = star_files.analyze_folder(folder)
        if result.get("error"):
            return result["error"]
        if result.get("file"):
            return f"{result['file']['name']} is a file, not a folder."
        return (
            f"Folder has {result['total_files']} files, {result['total_dirs']} folders, "
            f"using {result['total_size_mb']} MB."
        )

    return None


# ------------------- RESEARCH AGENT -------------------

def handle_research_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text.startswith("summarize webpage") or lower_text.startswith("read webpage"):
        url = text_after_any(text, ["summarize webpage", "read webpage"])
        if not url:
            return "Send me the webpage URL."
        try:
            page = star_research.summarize_webpage(url)
        except Exception as exc:
            storage.add_log("warning", "webpage_summary_failed", str(exc))
            return "I could not read that webpage."
        return page.get("summary") or "I could not summarize that webpage."

    if lower_text.startswith("weather"):
        query = text_after_any(text, ["weather"]).strip()
        result = star_research.weather(query)
        return result["summary"]

    if "latest news" in lower_text or lower_text.startswith("news"):
        query = text_after_any(text, ["latest news", "news"]).strip() or "latest news"
        result = star_research.latest_news(query)
        return result["summary"]

    if "price" in lower_text and any(word in lower_text for word in ["today", "current", "latest", "market", "stock", "crypto"]):
        query = lower_text.replace("current", "").replace("latest", "").replace("today", "").strip()
        result = star_research.market_price(query)
        return result["summary"]

    if lower_text.startswith("wikipedia"):
        query = text_after_any(text, ["wikipedia"]).strip()
        if not query:
            return "Tell me what to search on Wikipedia."
        result = star_research.wikipedia_search(query)
        return result["summary"]

    if lower_text.startswith("research"):
        query = text_after_any(text, ["research"]).strip()
        if not query:
            return "Tell me what to research."
        result = star_research.research_summary(query)
        return result["summary"]

    return None


# ------------------- PRODUCTIVITY AGENT -------------------

def first_number(text):
    import re

    match = re.search(r"\b(\d+)\b", text)
    return int(match.group(1)) if match else None


def handle_productivity_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"daily briefing", "morning briefing", "briefing", "morning routine"}:
        status = star_system.get_system_status()
        return star_productivity.daily_briefing(star_system.format_system_summary(status))

    if lower_text.startswith(("add note", "note ")):
        content = text_after_any(text, ["add note", "note"]).strip()
        if not content:
            return "Tell me what note to save."
        note_id = star_productivity.add_note(content)
        return f"Note {note_id} saved."

    if lower_text.startswith(("show notes", "list notes", "search notes")):
        query = text_after_any(text, ["search notes"]).strip() if lower_text.startswith("search notes") else None
        notes = star_productivity.list_notes(query=query, limit=10)
        return star_productivity.format_notes(notes)

    if lower_text.startswith("delete note"):
        note_id = first_number(text)
        if not note_id:
            return "Tell me the note number to delete."
        return "Note deleted." if star_productivity.delete_note(note_id) else "Note not found."

    if lower_text.startswith(("add task", "todo ", "to do ")):
        task = text_after_any(text, ["add task", "todo", "to do"]).strip()
        if not task:
            return "Tell me the task."
        due_at = star_productivity.parse_due_time(task)
        task_id = star_productivity.add_task(task, due_at=due_at)
        return f"Task {task_id} added."

    if lower_text in {"show tasks", "list tasks", "show todo", "show to do", "todo list", "to do list"}:
        return star_productivity.format_tasks(star_productivity.list_tasks(limit=10))

    if lower_text.startswith(("complete task", "finish task", "done task")):
        task_id = first_number(text)
        if not task_id:
            return "Tell me the task number to complete."
        return "Task completed." if star_productivity.complete_task(task_id) else "Task not found."

    if lower_text.startswith("delete task"):
        task_id = first_number(text)
        if not task_id:
            return "Tell me the task number to delete."
        return "Task deleted." if star_productivity.delete_task(task_id) else "Task not found."

    if lower_text.startswith("remind me to"):
        payload = text_after_any(text, ["remind me to"]).strip()
        due_at = star_productivity.parse_due_time(payload)
        if not due_at:
            return "Tell me when to remind you, like in 10 minutes or at 5 pm."
        reminder_text = star_productivity.strip_due_phrase(payload) or payload
        reminder_id = star_productivity.add_reminder(reminder_text, due_at)
        return f"Reminder {reminder_id} set for {due_at.strftime('%Y-%m-%d %H:%M')}."

    if lower_text in {"show reminders", "list reminders", "my reminders"}:
        return star_productivity.format_reminders(star_productivity.list_reminders(limit=10))

    if lower_text in {"due reminders", "check reminders"}:
        return star_productivity.format_reminders(star_productivity.due_reminders(limit=10))

    if lower_text.startswith(("complete reminder", "done reminder")):
        reminder_id = first_number(text)
        if not reminder_id:
            return "Tell me the reminder number to complete."
        return "Reminder completed." if star_productivity.complete_reminder(reminder_id) else "Reminder not found."

    if lower_text.startswith("delete reminder"):
        reminder_id = first_number(text)
        if not reminder_id:
            return "Tell me the reminder number to delete."
        return "Reminder deleted." if star_productivity.delete_reminder(reminder_id) else "Reminder not found."

    if lower_text.startswith("start pomodoro"):
        minutes = first_number(text) or 25
        state = star_productivity.start_pomodoro(minutes=minutes)
        return f"Pomodoro started for {state['minutes']} minutes."

    if lower_text in {"stop pomodoro", "cancel pomodoro"}:
        stopped = star_productivity.stop_pomodoro()
        return "Pomodoro stopped." if stopped else "No pomodoro is running."

    if lower_text in {"pomodoro status", "timer status"}:
        state = star_productivity.pomodoro_status()
        if not state["active"]:
            return "No pomodoro is running."
        minutes = state["remaining_seconds"] // 60
        seconds = state["remaining_seconds"] % 60
        return f"Pomodoro has {minutes} minutes and {seconds} seconds left."

    return None


# ------------------- CALENDAR AGENT -------------------

def handle_calendar_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"calendar", "calendar agenda", "show calendar", "show events", "list events", "upcoming events"}:
        events = star_calendar.upcoming_events(limit=8)
        return star_calendar.format_events(events, empty="No upcoming calendar events.")

    if lower_text in {"today agenda", "agenda today", "today's agenda", "calendar today"}:
        events = star_calendar.agenda("today")
        return star_calendar.format_events(events, empty="No calendar events today.")

    if lower_text in {"tomorrow agenda", "agenda tomorrow", "calendar tomorrow"}:
        events = star_calendar.agenda("tomorrow")
        return star_calendar.format_events(events, empty="No calendar events tomorrow.")

    if lower_text.startswith(("add event", "create event", "schedule event", "calendar add")):
        payload = text_after_any(text, ["add event", "create event", "schedule event", "calendar add"]).strip()
        if not payload:
            return "Tell me the event title and time."
        result = star_calendar.create_event_from_text(payload)
        if result.get("error"):
            return result["error"]
        return f"Event {result['id']} added for {result['starts_at'].strftime('%Y-%m-%d %H:%M')}."

    if lower_text.startswith(("delete event", "remove event")):
        event_id = first_number(text)
        if not event_id:
            return "Tell me the event number to delete."
        return "Event deleted." if star_calendar.delete_event(event_id) else "Event not found."

    if lower_text.startswith(("cancel event", "cancel calendar event")):
        event_id = first_number(text)
        if not event_id:
            return "Tell me the event number to cancel."
        return "Event cancelled." if star_calendar.cancel_event(event_id) else "Event not found."

    return None


# ------------------- BROWSER + MEDIA + MESSAGING -------------------

def handle_browser_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text.startswith(("open website", "open site")):
        target = text_after_any(text, ["open website", "open site"])
        return star_browser.open_website(target)

    if lower_text.startswith("google search"):
        query = text_after_any(text, ["google search"])
        return star_browser.search_google(query)

    if lower_text.startswith(("duckduckgo search", "duck duck go search")):
        query = text_after_any(text, ["duckduckgo search", "duck duck go search"])
        return star_browser.search_duckduckgo(query)

    if lower_text.startswith("new tab"):
        target = text_after_any(text, ["new tab"])
        return star_browser.new_tab(target or None)

    if lower_text in {"close tab", "close current tab"}:
        return star_browser.close_tab()

    if lower_text in {"next tab", "switch next tab"}:
        return star_browser.next_tab()

    if lower_text in {"previous tab", "prev tab", "switch previous tab"}:
        return star_browser.previous_tab()

    if lower_text in {"refresh page", "reload page"}:
        return star_browser.refresh_page()

    if lower_text in {"address bar", "focus address bar"}:
        return star_browser.focus_address_bar()

    if lower_text in {"open downloads", "browser downloads", "show downloads"}:
        return star_browser.open_downloads_page()

    if lower_text.startswith("download file"):
        url = text_after_any(text, ["download file"])
        if not url:
            return "Send me the file URL."
        try:
            result = star_browser.download_file(url)
        except Exception as exc:
            storage.add_log("warning", "download_failed", str(exc))
            return "Download failed."
        return f"Downloaded to {result['path']}."

    return None


def parse_whatsapp_send(text):
    lower_text = text.lower()
    if " message " in lower_text:
        index = lower_text.index(" message ")
        before = text[:index]
        message = text[index + len(" message "):]
    elif " saying " in lower_text:
        index = lower_text.index(" saying ")
        before = text[:index]
        message = text[index + len(" saying "):]
    else:
        return None

    contact = text_after_any(before, ["send whatsapp to", "whatsapp message to", "send message to"]).strip()
    if not contact or not message.strip():
        return None
    return contact, message.strip()


def handle_whatsapp_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"whatsapp status", "whatsapp login status", "check whatsapp"}:
        driver = None
        try:
            driver = create_chrome_driver()
            status = star_whatsapp.open_whatsapp(driver)
            return status["message"]
        except Exception as exc:
            storage.add_log("warning", "whatsapp_status_failed", str(exc))
            return "WhatsApp status check failed."
        finally:
            if driver:
                driver.quit()

    parsed = parse_whatsapp_send(text)
    if parsed:
        contact, message = parsed
        driver = None
        try:
            driver = create_chrome_driver()
            return star_whatsapp.send_message(driver, contact, message)
        except Exception as exc:
            storage.add_log("warning", "whatsapp_send_failed", str(exc))
            return "WhatsApp send failed."
        finally:
            if driver:
                driver.quit()

    if lower_text.startswith(("open whatsapp chat", "search whatsapp chat")):
        contact = text_after_any(text, ["open whatsapp chat", "search whatsapp chat"]).strip()
        if not contact:
            return "Tell me which WhatsApp chat to open."

        driver = None
        try:
            driver = create_chrome_driver()
            return star_whatsapp.open_chat(driver, contact)
        except Exception as exc:
            storage.add_log("warning", "whatsapp_open_chat_failed", str(exc))
            return "WhatsApp chat open failed."
        finally:
            if driver:
                driver.quit()

    return check_whatsapp()


def parse_email_send(text):
    lower_text = text.lower()
    if not lower_text.startswith(("send email to", "send mail to")):
        return None

    subject_marker = " subject "
    message_markers = [" message ", " body ", " saying "]
    if subject_marker not in lower_text:
        return None

    subject_index = lower_text.index(subject_marker)
    to_value = text_after_any(text[:subject_index], ["send email to", "send mail to"]).strip()
    remaining = text[subject_index + len(subject_marker):]
    remaining_lower = remaining.lower()

    message_index = None
    marker_used = None
    for marker in message_markers:
        if marker in remaining_lower:
            message_index = remaining_lower.index(marker)
            marker_used = marker
            break

    if message_index is None:
        return None

    subject = remaining[:message_index].strip()
    body = remaining[message_index + len(marker_used):].strip()
    if not to_value or not subject or not body:
        return None
    return to_value, subject, body


def handle_email_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"email status", "mail status"}:
        status = star_email.status()
        if status["configured"]:
            return f"Email is ready with {status['imap_host']} and {status['smtp_host']}."
        return "Email is not configured. Add EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env."

    if lower_text in {"email test", "test email", "email connection test"}:
        result = star_email.test_connection()
        if not result["configured"]:
            return "Email is not configured. Add EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env."
        return f"Email test: IMAP {result['imap']}, SMTP {result['smtp']}."

    if lower_text in {"read emails", "show emails", "inbox", "show inbox"}:
        try:
            return star_email.format_email_list(star_email.list_emails(limit=5))
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:
            storage.add_log("warning", "email_list_failed", str(exc))
            return "Email inbox check failed."

    if lower_text in {"unread emails", "show unread emails", "unread mail"}:
        try:
            return star_email.format_email_list(star_email.list_emails(limit=5, unread_only=True))
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:
            storage.add_log("warning", "email_unread_failed", str(exc))
            return "Unread email check failed."

    if lower_text.startswith(("search emails", "search mail")):
        query = text_after_any(text, ["search emails", "search mail"]).strip()
        if not query:
            return "Tell me what to search in email."
        try:
            return star_email.format_email_list(star_email.search_emails(query, limit=5))
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:
            storage.add_log("warning", "email_search_failed", str(exc))
            return "Email search failed."

    parsed = parse_email_send(text)
    if parsed:
        to_value, subject, body = parsed
        resolved = star_contacts.resolve_email(to_value)
        if not resolved:
            return f"I could not find an email address for {to_value}."
        try:
            result = star_email.send_email(resolved, subject, body)
            return f"Email sent to {result['to']}."
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:
            storage.add_log("warning", "email_send_failed", str(exc))
            return "Email send failed."

    if lower_text.startswith("archive email"):
        message_id = text_after_any(text, ["archive email"]).strip()
        if not message_id:
            return "Tell me which email id to archive."
        try:
            star_email.archive_email(message_id)
            return f"Email {message_id} archived."
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:
            storage.add_log("warning", "email_archive_failed", str(exc))
            return "Email archive failed."

    if lower_text.startswith("delete email"):
        message_id = text_after_any(text, ["delete email"]).strip()
        if not message_id:
            return "Tell me which email id to delete."
        try:
            star_email.delete_email(message_id)
            return f"Email {message_id} deleted."
        except RuntimeError as exc:
            return str(exc)
        except Exception as exc:
            storage.add_log("warning", "email_delete_failed", str(exc))
            return "Email delete failed."

    return "Email commands: email status, read emails, unread emails, search emails invoice, send email to someone@example.com subject Hello message Hi."


# ------------------- CONTACTS AGENT -------------------

def handle_contacts_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"contacts", "show contacts", "list contacts", "address book"}:
        return star_contacts.format_contacts(star_contacts.list_contacts(limit=10))

    if lower_text.startswith(("add contact", "save contact", "new contact")):
        payload = text_after_any(text, ["add contact", "save contact", "new contact"]).strip()
        if not payload:
            return "Tell me the contact name, email, or phone."
        parsed = star_contacts.parse_contact_payload(payload)
        if not parsed["name"]:
            return "Tell me the contact name."
        contact_id = star_contacts.add_contact(parsed["name"], email=parsed["email"], phone=parsed["phone"])
        return f"Contact {contact_id} saved."

    if lower_text.startswith(("find contact", "search contact", "contact ")):
        query = text_after_any(text, ["find contact", "search contact", "contact"]).strip()
        if not query:
            return "Tell me which contact to find."
        return star_contacts.format_contacts(star_contacts.search_contacts(query, limit=6))

    if lower_text.startswith("set contact email"):
        payload = text_after_any(text, ["set contact email"]).strip()
        if " to " not in payload.lower():
            return "Use: set contact email Bajrangi to name@example.com."
        index = payload.lower().index(" to ")
        query = payload[:index].strip()
        email = payload[index + 4:].strip()
        contact = star_contacts.find_one(query)
        if not contact:
            return "Contact not found."
        return "Contact updated." if star_contacts.update_contact(contact["id"], email=email) else "Contact update failed."

    if lower_text.startswith("set contact phone"):
        payload = text_after_any(text, ["set contact phone"]).strip()
        if " to " not in payload.lower():
            return "Use: set contact phone Bajrangi to +919999999999."
        index = payload.lower().index(" to ")
        query = payload[:index].strip()
        phone = payload[index + 4:].strip()
        contact = star_contacts.find_one(query)
        if not contact:
            return "Contact not found."
        return "Contact updated." if star_contacts.update_contact(contact["id"], phone=phone) else "Contact update failed."

    if lower_text.startswith(("delete contact", "remove contact")):
        contact_id = first_number(text)
        if not contact_id:
            query = text_after_any(text, ["delete contact", "remove contact"]).strip()
            contact = star_contacts.find_one(query) if query else None
            contact_id = contact["id"] if contact else None
        if not contact_id:
            return "Tell me the contact number or name to delete."
        return "Contact deleted." if star_contacts.delete_contact(contact_id) else "Contact not found."

    return None


# ------------------- CLIPBOARD + SNIPPETS AGENT -------------------

def parse_snippet_payload(payload):
    lower_payload = payload.lower()
    for marker in [" as ", " text ", " content "]:
        if marker in lower_payload:
            index = lower_payload.index(marker)
            name = payload[:index].strip()
            content = payload[index + len(marker):].strip()
            return name, content
    return None, None


def handle_clipboard_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"clipboard", "read clipboard", "clipboard status", "show clipboard"}:
        try:
            return star_clipboard.format_clipboard_text(star_clipboard.get_text())
        except Exception as exc:
            storage.add_log("warning", "clipboard_read_failed", str(exc))
            return "Could not read clipboard."

    if lower_text.startswith(("copy text", "copy to clipboard")):
        content = text_after_any(text, ["copy text", "copy to clipboard"]).strip()
        if not content:
            return "Tell me what text to copy."
        try:
            result = star_clipboard.set_text(content)
            return f"Copied {result['chars']} characters to clipboard."
        except Exception as exc:
            storage.add_log("warning", "clipboard_copy_failed", str(exc))
            return "Clipboard copy failed."

    if lower_text.startswith("paste text"):
        content = text_after_any(text, ["paste text"]).strip()
        if not content:
            return "Tell me what text to paste."
        try:
            result = star_clipboard.paste_text(content)
            return f"Pasted {result['chars']} characters."
        except Exception as exc:
            storage.add_log("warning", "clipboard_paste_failed", str(exc))
            return "Clipboard paste failed."

    if lower_text.startswith(("save snippet", "add snippet", "new snippet")):
        payload = text_after_any(text, ["save snippet", "add snippet", "new snippet"]).strip()
        name, content = parse_snippet_payload(payload)
        if not name or not content:
            return "Use: save snippet greeting as hello there."
        snippet_id = star_clipboard.add_snippet(name, content)
        return f"Snippet {snippet_id} saved."

    if lower_text in {"show snippets", "list snippets", "snippets"}:
        return star_clipboard.format_snippets(star_clipboard.list_snippets(limit=10))

    if lower_text.startswith("search snippets"):
        query = text_after_any(text, ["search snippets"]).strip()
        if not query:
            return "Tell me what snippet to search."
        return star_clipboard.format_snippets(star_clipboard.search_snippets(query, limit=8))

    if lower_text.startswith("copy snippet"):
        snippet_id = first_number(text)
        if not snippet_id:
            return "Tell me the snippet number to copy."
        snippet = star_clipboard.get_snippet(snippet_id)
        if not snippet:
            return "Snippet not found."
        try:
            star_clipboard.set_text(snippet["content"])
            return f"Snippet {snippet_id} copied to clipboard."
        except Exception as exc:
            storage.add_log("warning", "snippet_copy_failed", str(exc))
            return "Snippet copy failed."

    if lower_text.startswith("paste snippet"):
        snippet_id = first_number(text)
        if not snippet_id:
            return "Tell me the snippet number to paste."
        snippet = star_clipboard.get_snippet(snippet_id)
        if not snippet:
            return "Snippet not found."
        try:
            star_clipboard.paste_text(snippet["content"])
            return f"Snippet {snippet_id} pasted."
        except Exception as exc:
            storage.add_log("warning", "snippet_paste_failed", str(exc))
            return "Snippet paste failed."

    if lower_text.startswith("delete snippet"):
        snippet_id = first_number(text)
        if not snippet_id:
            return "Tell me the snippet number to delete."
        return "Snippet deleted." if star_clipboard.delete_snippet(snippet_id) else "Snippet not found."

    return None


# ------------------- FINANCE AGENT -------------------

def handle_finance_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"finance summary", "money summary", "expense summary", "monthly summary", "monthly finance"}:
        return star_finance.format_summary(star_finance.summary())

    if lower_text in {"show expenses", "list expenses", "monthly expenses", "recent expenses"}:
        return star_finance.format_transactions(star_finance.list_transactions(kind="expense", limit=10))

    if lower_text in {"show income", "list income", "recent income"}:
        return star_finance.format_transactions(star_finance.list_transactions(kind="income", limit=10))

    if lower_text in {"show transactions", "finance transactions", "recent transactions"}:
        return star_finance.format_transactions(star_finance.list_transactions(limit=10))

    if lower_text in {"expense categories", "spending categories", "category expenses"}:
        categories = star_finance.category_summary(limit=8)
        if not categories:
            return "No expense categories found this month."
        return "Expense categories: " + ", ".join(
            f"{item['category']} {star_finance.format_money(item['total'])}" for item in categories
        ) + "."

    if lower_text.startswith(("add expense", "record expense", "expense ")):
        payload = text_after_any(text, ["add expense", "record expense", "expense"]).strip()
        result = star_finance.create_from_text("expense", payload)
        if result.get("error"):
            return result["error"]
        return f"Expense {result['id']} added: {star_finance.format_money(result['amount'])} for {result['category']}."

    if lower_text.startswith(("add income", "record income", "income ")):
        payload = text_after_any(text, ["add income", "record income", "income"]).strip()
        result = star_finance.create_from_text("income", payload)
        if result.get("error"):
            return result["error"]
        return f"Income {result['id']} added: {star_finance.format_money(result['amount'])} for {result['category']}."

    if lower_text.startswith(("delete transaction", "delete expense", "delete income")):
        transaction_id = first_number(text)
        if not transaction_id:
            return "Tell me the transaction number to delete."
        return "Transaction deleted." if star_finance.delete_transaction(transaction_id) else "Transaction not found."

    return None


# ------------------- HEALTH AGENT -------------------

def handle_health_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"health summary", "today health", "wellness summary", "daily health"}:
        return star_health.format_summary(star_health.summary())

    if lower_text in {"show health logs", "health logs", "recent health logs"}:
        return star_health.format_logs(star_health.list_logs(limit=10))

    if lower_text.startswith(("log water", "drank water", "water ")):
        payload = text_after_any(text, ["log water", "drank water", "water"]).strip()
        result = star_health.log_water(payload)
        if result.get("error"):
            return result["error"]
        return f"Water log {result['id']} saved: {result['value']:g} ml."

    if lower_text.startswith(("log sleep", "slept ")):
        payload = text_after_any(text, ["log sleep", "slept"]).strip()
        result = star_health.log_sleep(payload)
        if result.get("error"):
            return result["error"]
        return f"Sleep log {result['id']} saved: {result['value']:g} hours."

    if lower_text.startswith(("log workout", "log exercise", "workout ", "exercise ")):
        payload = text_after_any(text, ["log workout", "log exercise", "workout", "exercise"]).strip()
        result = star_health.log_workout(payload)
        if result.get("error"):
            return result["error"]
        return f"Workout log {result['id']} saved: {result['value']:g} minutes."

    if lower_text.startswith(("log weight", "weight ")):
        payload = text_after_any(text, ["log weight", "weight"]).strip()
        result = star_health.log_weight(payload)
        if result.get("error"):
            return result["error"]
        return f"Weight log {result['id']} saved: {result['value']:g} kg."

    if lower_text.startswith(("log mood", "mood ", "feeling ", "feel ")):
        payload = text_after_any(text, ["log mood", "mood", "feeling", "feel"]).strip()
        if not payload:
            return "Tell me your mood, like log mood happy or mood 8."
        result = star_health.log_mood(payload)
        return f"Mood log {result['id']} saved."

    if lower_text.startswith(("delete health log", "delete health")):
        log_id = first_number(text)
        if not log_id:
            return "Tell me the health log number to delete."
        return "Health log deleted." if star_health.delete_log(log_id) else "Health log not found."

    return None


# ------------------- SUGGESTIONS + INTEGRATIONS -------------------

def handle_suggestions_command(command):
    text = command.strip().lower()

    if text in {"smart suggestions", "suggestions", "show suggestions", "what should i do", "learn from me"}:
        return star_suggestions.format_suggestions(star_suggestions.generate_suggestions(limit=5))

    if text.startswith(("dismiss suggestion", "snooze suggestion", "accept suggestion")):
        action = "accept"
        if text.startswith("dismiss"):
            action = "dismiss"
        elif text.startswith("snooze"):
            action = "snooze"
        key = text_after_any(command, ["dismiss suggestion", "snooze suggestion", "accept suggestion"]).strip()
        if not key:
            return "Tell me the suggestion key to update."
        star_suggestions.add_feedback(key, action)
        return f"Suggestion {action} saved."

    return None


def parse_mobile_notification(text):
    lower_text = text.lower()
    if " message " in lower_text:
        index = lower_text.index(" message ")
        title = text_after_any(text[:index], ["send mobile notification", "mobile notify"]).strip() or "STAR"
        body = text[index + len(" message "):].strip()
        return title, body
    payload = text_after_any(text, ["send mobile notification", "mobile notify"]).strip()
    return "STAR", payload


def queue_phone_action_reply(action, payload=None):
    devices = star_integrations.list_mobile_devices(limit=1)
    device_id = devices[0]["device_id"] if devices else None
    action_id = star_integrations.queue_mobile_action(action, payload or {}, device_id=device_id)
    if not action_id:
        return "I could not queue that phone action."
    if not devices:
        return f"Phone action {action_id} queued for the next connected phone. Start the Termux STAR bridge on your phone."
    return f"Phone action {action_id} queued."


def parse_phone_action_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"phone status", "mobile bridge status", "phone bridge status", "android status"}:
        return star_integrations.format_mobile_bridge_status()

    if lower_text in {"phone vibrate", "mobile vibrate", "vibrate phone"}:
        return queue_phone_action_reply("vibrate", {"duration_ms": 700})

    if lower_text.startswith(("phone speak", "mobile speak", "phone bolo", "mobile bolo")):
        payload = text_after_any(text, ["phone speak", "mobile speak", "phone bolo", "mobile bolo"]).strip()
        if not payload:
            return "Tell me what the phone should say."
        return queue_phone_action_reply("speak", {"text": payload})

    if lower_text.startswith(("phone notify", "mobile notify phone")):
        payload = text_after_any(text, ["phone notify", "mobile notify phone"]).strip()
        lower_payload = payload.lower()
        if " message " in lower_payload:
            marker_index = lower_payload.index(" message ")
            title = payload[:marker_index].strip() or "STAR"
            body = payload[marker_index + len(" message "):].strip()
        else:
            title, body = "STAR", payload
        if not body:
            return "Tell me the phone notification message."
        return queue_phone_action_reply("notify", {"title": title or "STAR", "body": body})

    if lower_text.startswith(("phone open", "mobile open")):
        target = text_after_any(text, ["phone open", "mobile open"]).strip()
        if not target:
            return "Tell me what URL or app link to open on phone."
        return queue_phone_action_reply("open_url", {"url": target})

    if lower_text.startswith(("phone share", "mobile share")):
        payload = text_after_any(text, ["phone share", "mobile share"]).strip()
        if not payload:
            return "Tell me what text to share from phone."
        return queue_phone_action_reply("share_text", {"text": payload})

    if lower_text.startswith(("phone call", "mobile call")):
        number = text_after_any(text, ["phone call", "mobile call"]).strip()
        if not number:
            return "Tell me the phone number to open in dialer."
        return queue_phone_action_reply("call_intent", {"number": number})

    if lower_text.startswith(("phone sms", "mobile sms", "phone message", "mobile message")):
        payload = text_after_any(text, ["phone sms", "mobile sms", "phone message", "mobile message"]).strip()
        lower_payload = payload.lower()
        marker = " message "
        if marker not in lower_payload:
            return "Use: phone sms NUMBER message TEXT."
        marker_index = lower_payload.index(marker)
        number = payload[:marker_index].strip()
        body = payload[marker_index + len(marker):].strip()
        if not number or not body:
            return "Use: phone sms NUMBER message TEXT."
        return queue_phone_action_reply("sms_intent", {"number": number, "body": body})

    return None


def handle_integrations_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"integration status", "integrations status", "cloud status", "mobile status", "smart home status"}:
        return star_integrations.format_status(star_integrations.integration_status())

    phone_reply = parse_phone_action_command(text)
    if phone_reply:
        return phone_reply

    if lower_text in {"cloud sync", "cloud sync now", "sync cloud"}:
        result = star_integrations.cloud_sync_snapshot(BASE_DIR)
        return f"Cloud snapshot saved to {result['path']}."

    if lower_text in {"mobile notifications", "show mobile notifications"}:
        items = star_integrations.list_mobile_notifications(limit=10)
        if not items:
            return "No mobile notifications queued."
        return "Mobile notifications: " + ", ".join(f"{item['id']}: {item['title']}" for item in items[:8]) + "."

    if lower_text.startswith(("send mobile notification", "mobile notify")):
        title, body = parse_mobile_notification(text)
        if not body:
            return "Tell me the mobile notification message."
        notification_id = star_integrations.queue_mobile_notification(title, body)
        return f"Mobile notification {notification_id} queued."

    if lower_text.startswith(("smart home turn on", "smart home turn off")):
        service = "turn_on" if lower_text.startswith("smart home turn on") else "turn_off"
        entity_id = text_after_any(text, ["smart home turn on", "smart home turn off"]).strip()
        if not entity_id:
            return "Tell me the smart home entity id, like light.kitchen."
        domain = entity_id.split(".", 1)[0] if "." in entity_id else "homeassistant"
        result = star_integrations.call_home_assistant_service(domain, service, entity_id=entity_id)
        return f"Smart home {service.replace('_', ' ')} result: {result['status']}."

    if lower_text.startswith("add integration"):
        payload = text_after_any(text, ["add integration"]).strip()
        if not payload:
            return "Tell me integration name and type."
        parts = payload.split()
        name = parts[0]
        kind = parts[1] if len(parts) > 1 else "general"
        integration_id = star_integrations.save_integration(name, kind)
        return f"Integration {integration_id} saved as planned."

    if lower_text in {"list integrations", "show integrations"}:
        items = star_integrations.list_integrations(limit=10)
        if not items:
            return "No integrations saved yet."
        return "Integrations: " + ", ".join(f"{item['id']}: {item['name']} ({item['kind']})" for item in items[:8]) + "."

    return None


# ------------------- VOICE AGENT -------------------

def handle_voice_command(command):
    if star_voice.is_quiet_command(command):
        star_voice.set_voice_quiet(True)
        stop_speaking()
        return "Theek hai, main chup ho gaya. Jab bolna ho, say ok star you can talk."

    if star_voice.is_resume_command(command):
        star_voice.set_voice_quiet(False)
        return "Theek hai bhai, ab main baat kar sakta hoon."

    parsed = star_voice.parse_voice_command(command)
    if not parsed:
        return None

    action = parsed["action"]
    if action == "status":
        return star_voice.format_settings()

    if action == "repeat":
        last = star_voice.last_voice_state().get("last_reply")
        if not last:
            return "I do not have a voice reply to repeat yet."
        speak(last)
        return last

    if action == "set":
        updates = {
            key: value
            for key, value in parsed.items()
            if (key.startswith("voice_") or key.startswith("wake_")) and value
        }
        if not updates:
            return "Tell me which voice setting to change."
        changed = star_voice.update_settings(**updates)
        if not changed:
            return "I could not update that voice setting."
        return "Voice settings updated. " + star_voice.format_settings()

    return None


# ------------------- CODING + GIT AGENTS -------------------

def handle_coding_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"analyze project", "analyse project", "project summary", "code summary"}:
        return star_coding.format_project_summary(star_coding.analyze_project())

    if lower_text.startswith(("search code", "find in code")):
        query = text_after_any(text, ["search code", "find in code"])
        if not query:
            return "Tell me what to search in code."
        matches = star_coding.search_code(query, limit=8)
        if not matches:
            return f"No code matches found for {query}."
        parts = [f"{Path(item['path']).name}:{item['line']}" for item in matches[:6]]
        return "Found matches at " + ", ".join(parts) + "."

    if lower_text.startswith(("explain file", "explain code")):
        path = text_after_any(text, ["explain file", "explain code"])
        if not path:
            return "Tell me which file to explain."
        info = star_coding.explain_file(path)
        if info.get("error"):
            return info["error"]
        summary = info.get("python_summary")
        if summary:
            funcs = ", ".join(summary.get("functions", [])[:8]) or "no functions"
            return f"{Path(info['path']).name} is a Python file with functions: {funcs}."
        return f"{Path(info['path']).name} has {info['chars']} characters."

    if lower_text.startswith(("review file", "review code")):
        path = text_after_any(text, ["review file", "review code"])
        if not path:
            return "Tell me which Python file to review."
        return star_coding.format_findings(star_coding.review_python_file(path))

    if lower_text in {"run code check", "run compile check", "python compile check"}:
        result = star_coding.compile_python()
        return "Python compile check passed." if result["ok"] else f"Compile check failed: {result['stderr'][:300]}"

    return None


def handle_git_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"git status", "repo status", "repository status"}:
        return star_git.format_status(star_git.status())

    if lower_text.startswith("git log"):
        limit = first_number(text) or 5
        return star_git.format_log(star_git.log(limit=limit))

    if lower_text in {"git branch", "current branch"}:
        result = star_git.branch()
        if not result.get("ok"):
            return result.get("message") or result.get("error") or "Could not read branch."
        return f"Current branch is {result.get('branch') or 'unknown'}."

    if lower_text in {"git remotes", "git remote", "repo remotes"}:
        result = star_git.remotes()
        if not result.get("ok"):
            return result.get("message") or result.get("error") or "Could not read remotes."
        return result.get("remotes") or "No git remotes configured."

    if lower_text.startswith("git diff"):
        path = text_after_any(text, ["git diff"]).strip() or None
        result = star_git.diff(path=path)
        if not result.get("ok"):
            return result.get("message") or result.get("error") or "Could not read diff."
        diff_text = result.get("diff") or "No diff."
        return diff_text[:1200]

    if lower_text.startswith("git commit"):
        message = text_after_any(text, ["git commit"]).strip()
        if not message:
            return "Tell me the commit message."

        def do_commit():
            add_result = star_git.add_all()
            if not add_result["ok"]:
                return f"Git add failed: {add_result['stderr']}"
            commit_result = star_git.commit(message)
            if not commit_result["ok"]:
                return f"Git commit failed: {commit_result['stderr']}"
            return commit_result["stdout"] or "Git commit complete."

        return set_pending_confirmation("git_commit", f"Git commit requested with message: {message}", do_commit)

    if lower_text == "git pull":
        def do_pull():
            result = star_git.pull()
            if not result["ok"]:
                return f"Git pull failed: {result['stderr']}"
            return result["stdout"] or "Git pull complete."

        return set_pending_confirmation("git_pull", "Git pull requested", do_pull)

    if lower_text == "git push":
        def do_push():
            result = star_git.push()
            if not result["ok"]:
                return f"Git push failed: {result['stderr']}"
            return result["stdout"] or "Git push complete."

        return set_pending_confirmation("git_push", "Git push requested", do_push)

    return None


# ------------------- AUTOMATION AGENT -------------------

def run_automation_item(automation):
    run_id = star_automation.mark_run_started(automation["id"])
    outputs = []
    status = "ok"

    for step in star_automation.automation_steps(automation):
        if not step:
            continue
        try:
            outputs.append(f"> {step}\n{ask_star(step)}")
        except Exception as exc:
            status = "error"
            outputs.append(f"> {step}\nERROR: {exc}")
            break

    output = "\n\n".join(outputs)
    star_automation.finish_run(run_id, automation, status, output)
    return {"id": automation["id"], "status": status, "output": output}


def run_due_automations(limit=10):
    due = star_automation.due_automations(limit=limit)
    results = [run_automation_item(item) for item in due]
    return results


def handle_automation_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text.startswith(("schedule command", "schedule")):
        payload = text_after_any(text, ["schedule command", "schedule"]).strip()
        due_at = star_automation.parse_schedule(payload)
        if not due_at:
            return "Tell me when to run it, like in 10 minutes or at 5 pm."

        command_text = star_automation.strip_schedule_phrase(payload)
        interval = star_automation.parse_interval(payload)
        command_text = command_text.replace("every", "").strip()
        if not command_text:
            return "Tell me what command to schedule."

        automation_id = star_automation.create_command_automation(
            name=command_text[:60],
            command=command_text,
            next_run_at=due_at,
            interval_minutes=interval,
        )
        return f"Automation {automation_id} scheduled for {due_at.strftime('%Y-%m-%d %H:%M')}."

    if lower_text.startswith("create workflow"):
        payload = text_after_any(text, ["create workflow"]).strip()
        if not payload or " then " not in payload.lower():
            return "Use: create workflow first command then second command."
        steps = [part.strip() for part in payload.split(" then ") if part.strip()]
        automation_id = star_automation.create_workflow("voice workflow", steps)
        return f"Workflow {automation_id} created with {len(steps)} steps."

    if lower_text in {"show automations", "list automations", "automation list"}:
        return star_automation.format_automations(star_automation.list_automations(limit=20))

    if lower_text in {"run automations", "run due automations", "check automations"}:
        results = run_due_automations()
        if not results:
            return "No automations are due."
        return f"Ran {len(results)} automation(s)."

    if lower_text.startswith("delete automation"):
        automation_id = first_number(text)
        if not automation_id:
            return "Tell me the automation number to delete."
        return "Automation deleted." if star_automation.delete_automation(automation_id) else "Automation not found."

    if lower_text.startswith("pause automation"):
        automation_id = first_number(text)
        if not automation_id:
            return "Tell me the automation number to pause."
        return "Automation paused." if star_automation.pause_automation(automation_id) else "Automation not found."

    if lower_text.startswith("resume automation"):
        automation_id = first_number(text)
        if not automation_id:
            return "Tell me the automation number to resume."
        return "Automation resumed." if star_automation.resume_automation(automation_id) else "Automation not found."

    return None


# ------------------- SECURITY AGENT -------------------

def handle_security_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"security status", "privacy status", "api key status"}:
        return star_security.format_security_status(star_security.security_status(BASE_DIR))

    if lower_text.startswith("security mode"):
        mode = text_after_any(text, ["security mode"]).strip().lower()
        if not mode:
            return f"Security mode is {star_security.get_mode()}."
        if star_security.set_mode(mode):
            return f"Security mode set to {mode}."
        return "Use security mode relaxed, normal, or strict."

    if lower_text in {"audit logs", "security logs"}:
        logs = [item for item in storage.list_logs(limit=20) if item["event"].startswith("security_")]
        if not logs:
            return "No security audit logs found."
        return "Audit logs: " + ", ".join(f"{item['event']} at {item['created_at']}" for item in logs[:6]) + "."

    if lower_text.startswith("check permission"):
        target = text_after_any(text, ["check permission"]).strip()
        if not target:
            return "Tell me which command to check."
        result = star_security.classify_command(target)
        if result["requires_confirmation"]:
            return f"That command needs confirmation. Categories: {', '.join(result['categories'])}."
        return f"That command is {result['risk']}."

    return None


# ------------------- ANALYTICS AGENT -------------------

def handle_analytics_command(command):
    text = command.lower().strip()

    if text in {"analytics", "analytics summary", "usage stats", "usage statistics"}:
        return star_analytics.format_summary(star_analytics.full_summary())

    if text in {"top tools", "most used tools"}:
        tools = star_analytics.command_summary()["top_tools"]
        if not tools:
            return "No tool usage yet."
        return "Top tools: " + ", ".join(f"{item['tool']} ({item['count']})" for item in tools[:6]) + "."

    if text in {"recent errors", "error summary"}:
        errors = star_analytics.recent_errors(limit=6)
        logs = errors["logs"]
        if not logs and not errors["commands"]:
            return "No recent errors found."
        parts = [item["event"] for item in logs[:5]]
        return "Recent issues: " + ", ".join(parts) + "."

    if text in {"daily activity", "command activity"}:
        days = star_analytics.daily_commands(limit=7)
        if not days:
            return "No command activity yet."
        return "Daily activity: " + ", ".join(f"{item['day']}: {item['count']}" for item in days) + "."

    return None


# ------------------- VISION AGENT -------------------

def handle_vision_command(command):
    text = command.strip()
    lower_text = text.lower()

    if lower_text in {"take screenshot", "capture screenshot", "screenshot"}:
        path = star_vision.capture_screenshot()
        return f"Screenshot saved to {path}."

    if lower_text in {"analyze screen", "analyse screen", "read screen", "screen summary"}:
        result = star_vision.screen_summary()
        ocr_text = result["ocr"].get("text") if result["ocr"].get("available") else ""
        if ocr_text:
            return f"{result['analysis']['summary']} Text found: {ocr_text[:300]}"
        return result["analysis"]["summary"] + " OCR is not available." if not result["ocr"].get("available") else result["analysis"]["summary"]

    if lower_text.startswith(("analyze image", "analyse image")):
        path = text_after_any(text, ["analyze image", "analyse image"])
        if not path:
            return "Tell me which image to analyze."
        result = star_vision.analyze_image(path)
        return result["summary"]

    if lower_text.startswith(("ocr image", "read image text", "read text from image")):
        path = text_after_any(text, ["ocr image", "read image text", "read text from image"])
        if not path:
            return "Tell me which image to read."
        result = star_vision.ocr_image(path)
        if not result.get("available"):
            return result.get("error") or "OCR is not available."
        return result.get("text") or "No text found in image."

    if lower_text.startswith(("scan qr", "read qr", "scan barcode")):
        path = text_after_any(text, ["scan qr", "read qr", "scan barcode"])
        if not path:
            return "Tell me which image to scan."
        qr = star_vision.decode_qr(path)
        barcodes = star_vision.decode_barcodes(path)
        items = qr.get("items", []) + barcodes.get("items", [])
        if not items:
            return qr.get("error") or barcodes.get("error") or "No QR or barcode found."
        return "Found codes: " + ", ".join(item["data"] for item in items[:5])

    if lower_text.startswith("compare images"):
        payload = text_after_any(text, ["compare images"])
        parts = [part.strip() for part in payload.split(" and ") if part.strip()]
        if len(parts) != 2:
            return "Use: compare images first.png and second.png."
        result = star_vision.compare_images(parts[0], parts[1])
        return f"Images are {result['similarity_percent']} percent similar."

    return None


def security_gate(command, tool, callback):
    result = star_security.classify_command(command, tool=tool)
    if not result["requires_confirmation"]:
        return callback()

    categories = ", ".join(result["categories"])
    star_security.audit("confirmation_required", "warning", {"command": command, "tool": tool, "categories": result["categories"]})
    return set_pending_confirmation(
        f"secure_{tool}",
        f"Security confirmation required for {categories}",
        callback,
    )


# ------------------- ACTION ROUTING -------------------

TOOLS = {
    "open",
    "close",
    "screen",
    "search",
    "whatsapp",
    "instagram",
    "system",
    "file",
    "research",
    "productivity",
    "browser",
    "media",
    "coding",
    "git",
    "automation",
    "security",
    "analytics",
    "vision",
    "email",
    "calendar",
    "contacts",
    "clipboard",
    "finance",
    "health",
    "suggestions",
    "integrations",
    "voice",
    "none",
}


def detect_tool_without_ai(user_text):
    text = user_text.lower().strip()

    voice_phrases = [
        "voice status",
        "voice settings",
        "listening status",
        "speech status",
        "voice language",
        "set voice language",
        "speech language",
        "voice mode",
        "set voice mode",
        "hindi mode",
        "hinglish mode",
        "english mode",
        "repeat",
        "repeat that",
        "dobara bolo",
        "fir se bolo",
        "phir se bolo",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in voice_phrases):
        return "voice"

    if any(phrase in text for phrase in ["search files", "find files", "find file", "file search", "read file", "summarize file", "summary of file", "analyze folder", "folder analysis", "analyse folder"]):
        return "file"

    if (
        text.startswith(("weather", "wikipedia", "research", "summarize webpage", "read webpage"))
        or "latest news" in text
        or ("price" in text and any(word in text for word in ["today", "current", "latest", "market", "stock", "crypto"]))
    ):
        return "research"

    productivity_phrases = [
        "add note",
        "note ",
        "show notes",
        "list notes",
        "search notes",
        "delete note",
        "add task",
        "todo ",
        "to do ",
        "show tasks",
        "list tasks",
        "show todo",
        "todo list",
        "complete task",
        "finish task",
        "done task",
        "delete task",
        "remind me to",
        "show reminders",
        "list reminders",
        "my reminders",
        "due reminders",
        "check reminders",
        "complete reminder",
        "delete reminder",
        "start pomodoro",
        "stop pomodoro",
        "cancel pomodoro",
        "pomodoro status",
        "timer status",
        "daily briefing",
        "morning briefing",
        "briefing",
        "morning routine",
    ]
    if any(text.startswith(phrase) or text == phrase.strip() for phrase in productivity_phrases):
        return "productivity"

    browser_phrases = [
        "open website",
        "open site",
        "google search",
        "duckduckgo search",
        "duck duck go search",
        "new tab",
        "close tab",
        "close current tab",
        "next tab",
        "switch next tab",
        "previous tab",
        "prev tab",
        "switch previous tab",
        "refresh page",
        "reload page",
        "address bar",
        "focus address bar",
        "browser downloads",
        "show downloads",
        "download file",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in browser_phrases):
        return "browser"

    media_phrases = [
        "play music",
        "pause music",
        "play pause",
        "pause media",
        "resume media",
        "next song",
        "next track",
        "previous song",
        "previous track",
        "stop music",
        "stop media",
        "open youtube",
        "play youtube",
        "open spotify",
        "play spotify",
        "open netflix",
        "open vlc",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in media_phrases):
        return "media"

    coding_phrases = [
        "analyze project",
        "analyse project",
        "project summary",
        "code summary",
        "search code",
        "find in code",
        "explain file",
        "explain code",
        "review file",
        "review code",
        "run code check",
        "run compile check",
        "python compile check",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in coding_phrases):
        return "coding"

    git_phrases = [
        "git status",
        "repo status",
        "repository status",
        "git log",
        "git branch",
        "current branch",
        "git remotes",
        "git remote",
        "repo remotes",
        "git diff",
        "git commit",
        "git pull",
        "git push",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in git_phrases):
        return "git"

    if text.startswith(("schedule event", "add event", "create event", "calendar add")):
        return "calendar"

    automation_phrases = [
        "schedule command",
        "schedule ",
        "create workflow",
        "show automations",
        "list automations",
        "automation list",
        "run automations",
        "run due automations",
        "check automations",
        "delete automation",
        "pause automation",
        "resume automation",
    ]
    if any(text.startswith(phrase) or text == phrase.strip() for phrase in automation_phrases):
        return "automation"

    security_phrases = [
        "security status",
        "privacy status",
        "api key status",
        "security mode",
        "audit logs",
        "security logs",
        "check permission",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in security_phrases):
        return "security"

    analytics_phrases = [
        "analytics",
        "analytics summary",
        "usage stats",
        "usage statistics",
        "top tools",
        "most used tools",
        "recent errors",
        "error summary",
        "daily activity",
        "command activity",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in analytics_phrases):
        return "analytics"

    vision_phrases = [
        "take screenshot",
        "capture screenshot",
        "analyze screen",
        "analyse screen",
        "read screen",
        "screen summary",
        "analyze image",
        "analyse image",
        "ocr image",
        "read image text",
        "read text from image",
        "scan qr",
        "read qr",
        "scan barcode",
        "compare images",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in vision_phrases):
        return "vision"

    email_phrases = [
        "email status",
        "mail status",
        "email test",
        "test email",
        "email connection test",
        "read emails",
        "show emails",
        "show inbox",
        "inbox",
        "unread emails",
        "show unread emails",
        "unread mail",
        "search emails",
        "search mail",
        "send email to",
        "send mail to",
        "archive email",
        "delete email",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in email_phrases):
        return "email"

    calendar_phrases = [
        "calendar",
        "calendar agenda",
        "show calendar",
        "show events",
        "list events",
        "upcoming events",
        "today agenda",
        "agenda today",
        "today's agenda",
        "calendar today",
        "tomorrow agenda",
        "agenda tomorrow",
        "calendar tomorrow",
        "add event",
        "create event",
        "schedule event",
        "calendar add",
        "delete event",
        "remove event",
        "cancel event",
        "cancel calendar event",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in calendar_phrases):
        return "calendar"

    contacts_phrases = [
        "contacts",
        "show contacts",
        "list contacts",
        "address book",
        "add contact",
        "save contact",
        "new contact",
        "find contact",
        "search contact",
        "contact ",
        "set contact email",
        "set contact phone",
        "delete contact",
        "remove contact",
    ]
    if any(text.startswith(phrase) or text == phrase.strip() for phrase in contacts_phrases):
        return "contacts"

    clipboard_phrases = [
        "clipboard",
        "read clipboard",
        "clipboard status",
        "show clipboard",
        "copy text",
        "copy to clipboard",
        "paste text",
        "save snippet",
        "add snippet",
        "new snippet",
        "show snippets",
        "list snippets",
        "snippets",
        "search snippets",
        "copy snippet",
        "paste snippet",
        "delete snippet",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in clipboard_phrases):
        return "clipboard"

    finance_phrases = [
        "add expense",
        "record expense",
        "expense ",
        "add income",
        "record income",
        "income ",
        "finance summary",
        "money summary",
        "expense summary",
        "monthly summary",
        "monthly finance",
        "show expenses",
        "list expenses",
        "monthly expenses",
        "recent expenses",
        "show income",
        "list income",
        "recent income",
        "show transactions",
        "finance transactions",
        "recent transactions",
        "expense categories",
        "spending categories",
        "category expenses",
        "delete transaction",
        "delete expense",
        "delete income",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in finance_phrases):
        return "finance"

    health_phrases = [
        "health summary",
        "today health",
        "wellness summary",
        "daily health",
        "show health logs",
        "health logs",
        "recent health logs",
        "log water",
        "drank water",
        "water ",
        "log sleep",
        "slept ",
        "log workout",
        "log exercise",
        "workout ",
        "exercise ",
        "log weight",
        "weight ",
        "log mood",
        "mood ",
        "feeling ",
        "feel ",
        "delete health log",
        "delete health",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in health_phrases):
        return "health"

    suggestion_phrases = [
        "smart suggestions",
        "suggestions",
        "show suggestions",
        "what should i do",
        "learn from me",
        "dismiss suggestion",
        "snooze suggestion",
        "accept suggestion",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in suggestion_phrases):
        return "suggestions"

    integration_phrases = [
        "integration status",
        "integrations status",
        "cloud status",
        "mobile status",
        "phone status",
        "mobile bridge status",
        "phone bridge status",
        "android status",
        "smart home status",
        "cloud sync",
        "cloud sync now",
        "sync cloud",
        "mobile notifications",
        "show mobile notifications",
        "send mobile notification",
        "mobile notify",
        "phone vibrate",
        "mobile vibrate",
        "vibrate phone",
        "phone speak",
        "mobile speak",
        "phone bolo",
        "mobile bolo",
        "phone notify",
        "mobile notify phone",
        "phone open",
        "mobile open",
        "phone share",
        "mobile share",
        "phone call",
        "mobile call",
        "phone sms",
        "mobile sms",
        "phone message",
        "mobile message",
        "smart home turn on",
        "smart home turn off",
        "add integration",
        "list integrations",
        "show integrations",
    ]
    if any(text.startswith(phrase) or text == phrase for phrase in integration_phrases):
        return "integrations"

    if text.startswith(("search", "google", "find")):
        return "search"

    if text.startswith("open"):
        return "open"

    if text.startswith("close"):
        return "close"

    if any(word in text for word in ["screenshot", "scroll down", "scroll up", "click", "type"]):
        return "screen"

    if detect_system_command(text):
        return "system"

    if "whatsapp" in text:
        return "whatsapp"

    if "instagram" in text:
        return "instagram"

    return None


def agent_brain(user_text):
    direct_tool = detect_tool_without_ai(user_text)
    if direct_tool:
        return direct_tool

    if not client:
        return "none"

    prompt = f"""
You are STAR's action planner.

Decide which tool to use.

TOOLS:
open
close
screen
search
whatsapp
instagram
system
file
research
productivity
browser
media
coding
git
automation
security
analytics
vision
email
calendar
contacts
clipboard
finance
health
suggestions
integrations
voice
none

Reply ONLY with one tool name.

Command:
{user_text}
"""

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        tool = res.choices[0].message.content.strip().lower()
        return tool if tool in TOOLS else "none"
    except Exception as exc:
        print("Agent planner failed:", exc)
        return "none"


def run_tool(tool, command):
    if tool == "open":
        return "Done." if open_anything(command) else None

    if tool == "close":
        return "Done." if close_anything(command) else None

    if tool == "screen":
        return "Done." if control_screen(command) else None

    if tool == "search":
        return "Done." if search_web(command) else None

    if tool == "whatsapp":
        return handle_whatsapp_command(command)

    if tool == "instagram":
        return check_instagram()

    if tool == "system":
        return handle_system_command(command)

    if tool == "file":
        return handle_file_command(command)

    if tool == "research":
        return handle_research_command(command)

    if tool == "productivity":
        return handle_productivity_command(command)

    if tool == "browser":
        return handle_browser_command(command)

    if tool == "media":
        return star_media.handle_media_command(command)

    if tool == "coding":
        return handle_coding_command(command)

    if tool == "git":
        return handle_git_command(command)

    if tool == "automation":
        return handle_automation_command(command)

    if tool == "security":
        return handle_security_command(command)

    if tool == "analytics":
        return handle_analytics_command(command)

    if tool == "vision":
        return handle_vision_command(command)

    if tool == "email":
        return handle_email_command(command)

    if tool == "calendar":
        return handle_calendar_command(command)

    if tool == "contacts":
        return handle_contacts_command(command)

    if tool == "clipboard":
        return handle_clipboard_command(command)

    if tool == "finance":
        return handle_finance_command(command)

    if tool == "health":
        return handle_health_command(command)

    if tool == "suggestions":
        return handle_suggestions_command(command)

    if tool == "integrations":
        return handle_integrations_command(command)

    if tool == "voice":
        return handle_voice_command(command)

    return None


# ------------------- MEMORY -------------------

def clean_memory_key(raw_key):
    key = raw_key.strip().lower()
    prefixes = ["that my ", "that ", "my ", "the ", "about "]
    for prefix in prefixes:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    return storage.normalize_key(key)


def format_memory_items(items):
    if not items:
        return "I do not remember anything yet."

    parts = [f"{item['key']} is {item['value']}" for item in items[:8]]
    return "I remember " + ", ".join(parts) + "."


def handle_memory_command(user_text):
    text = user_text.strip()
    lower_text = text.lower()

    if lower_text in {"what do you remember", "show memory", "show my memory", "memory"}:
        return format_memory_items(storage.list_memory(limit=50))

    if lower_text in {"forget all memory", "clear memory", "clear my memory"}:
        storage.clear_memory()
        return "All memory cleared."

    if lower_text.startswith("forget "):
        raw_key = lower_text.replace("forget ", "", 1).strip()
        key = clean_memory_key(raw_key)
        if not key:
            return "Tell me what memory to forget."

        if storage.delete_memory(key):
            return f"Forgot {key}."

        matches = storage.search_memory(key, limit=1)
        if matches and storage.delete_memory(matches[0]["key"]):
            return f"Forgot {matches[0]['key']}."

        return f"I could not find {key} in memory."

    if lower_text.startswith("remember "):
        payload = text[len("remember "):].strip()
        payload_lower = payload.lower()

        if payload_lower.startswith("that "):
            payload = payload[5:].strip()
            payload_lower = payload.lower()

        splitter = " is "
        if splitter not in payload_lower and " = " in payload_lower:
            splitter = " = "

        if splitter in payload_lower:
            index = payload_lower.index(splitter)
            key = clean_memory_key(payload[:index])
            value = payload[index + len(splitter):].strip()
            if key and value:
                storage.set_memory(key, value, infer_memory_category(key), "user")
                return f"Remembered {key}."

    if lower_text.startswith("set my ") and " to " in lower_text:
        payload = text[len("set my "):].strip()
        payload_lower = payload.lower()
        index = payload_lower.index(" to ")
        key = clean_memory_key(payload[:index])
        value = payload[index + 4:].strip()
        if key and value:
            storage.set_memory(key, value, infer_memory_category(key), "user")
            return f"Updated {key}."

    return None


def extract_memory(user_text):
    if not client:
        return

    prompt = f"""
Extract personal user information from this text.

Return STRICT JSON only.
If no personal info return {{}}.

Examples:
{{"favourite_colour":"black"}}
{{"city":"Ahmedabad"}}
{{"name":"Bajrangi"}}

Text:
{user_text}
"""

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        data = res.choices[0].message.content.strip()
        new_memory = json.loads(data)
    except Exception as exc:
        print("Memory extraction failed:", exc)
        return

    if not isinstance(new_memory, dict) or not new_memory:
        return

    for key, value in new_memory.items():
        storage.set_memory(key, value, infer_memory_category(key), "ai")


def check_direct_memory(user_text):
    text = user_text.lower()

    memory_queries = {
        "favourite colour": "favourite_colour",
        "favorite color": "favourite_colour",
        "where do i live": "city",
        "my city": "city",
        "my name": "name",
    }

    for phrase, key in memory_queries.items():
        if phrase in text:
            return storage.get_memory_value(key)

    question_prefixes = ["what is my ", "what's my ", "tell me my "]
    for prefix in question_prefixes:
        if text.startswith(prefix):
            key = storage.normalize_key(text.replace(prefix, "", 1).strip(" ?"))
            direct = storage.get_memory_value(key)
            if direct:
                return direct

            matches = storage.search_memory(key, limit=1)
            if matches:
                return matches[0]["value"]

    return None


# ------------------- MAIN AI LOGIC -------------------

def record_interaction(user_text, tool, status, reply, adapt=True):
    if adapt:
        reply = adapt_reply_for_context(reply, user_text=user_text)
    storage.add_command(user_text, tool, status, reply)
    storage.add_conversation("assistant", reply)
    star_voice.remember_interaction(user_text, reply)
    storage.add_log(
        "info" if status == "ok" else "warning",
        "command_handled",
        {"tool": tool, "status": status},
    )
    return reply


def ask_star(user_text):
    global SPEECH_CONTEXT
    text = user_text.strip()
    lower_text = text.lower()

    if not text:
        return "Please say something."

    storage.add_conversation("user", text)
    SPEECH_CONTEXT = text

    try:
        if any(phrase in lower_text for phrase in ["stop server", "close server", "shutdown server", "kill server", "stop backend", "close backend"]):
            reply = "STAR server stays on in the background. Say stop to stop my speech, or sleep to stop listening until the wake word."
            speak(reply)
            return record_interaction(text, "runtime", "ok", reply)

        if star_voice.is_resume_command(text):
            star_voice.set_voice_quiet(False)
            reply = "Theek hai bhai, ab main baat kar sakta hoon."
            speak(reply)
            return record_interaction(text, "voice", "ok", reply, adapt=False)

        if star_voice.is_exit_listening_command(text):
            star_voice.set_voice_quiet(False)
            stop_speaking()
            reply = "Theek hai bhai, main sleep mode me hoon. Hello star bolo, fir main sununga."
            return record_interaction(text, "voice", "sleep", reply, adapt=False)

        if star_voice.is_quiet_command(text):
            star_voice.set_voice_quiet(True)
            stop_speaking()
            reply = "Theek hai, main chup ho gaya. Jab bolna ho, say ok star you can talk."
            return record_interaction(text, "voice", "ok", reply, adapt=False)

        if star_voice.is_voice_quiet():
            storage.add_command(text, "voice", "quiet", "")
            storage.add_log("info", "voice_quiet_ignored", {"command": text})
            return ""

        confirmation_reply = handle_confirmation_command(text)
        if confirmation_reply:
            speak(confirmation_reply)
            return record_interaction(text, "confirmation", "ok", confirmation_reply)

        action_text = star_language.normalize_command(text, client=client)
        lower_action_text = action_text.lower()
        if action_text != text:
            storage.add_log("info", "language_normalized", {"original": text, "normalized": action_text})

        memory_callback = lambda: handle_memory_command(action_text)
        if star_security.classify_command(action_text)["requires_confirmation"] and any(
            category == "memory_clear" for category in star_security.classify_command(action_text)["categories"]
        ):
            memory_reply = security_gate(action_text, "memory", memory_callback)
        else:
            memory_reply = memory_callback()
        if memory_reply:
            speak(memory_reply)
            return record_interaction(text, "memory", "ok", memory_reply)

        if open_chrome_and_search(action_text):
            return record_interaction(text, "search", "ok", "Done.")

        tool = agent_brain(action_text)
        if tool != "none":
            if tool in {"whatsapp", "browser", "automation", "email", "clipboard", "integrations"}:
                tool_reply = security_gate(action_text, tool, lambda: run_tool(tool, action_text))
            else:
                tool_reply = run_tool(tool, action_text)
            if tool_reply:
                if PENDING_CONFIRMATION and star_voice.parse_bool(star_voice.get_settings().get("voice_spoken_confirmations")):
                    speak(tool_reply)
                return record_interaction(text, tool, "ok", tool_reply)

        extract_memory(text)

        direct = check_direct_memory(action_text)
        if direct:
            reply = f"It is {direct}."
            speak(reply)
            return record_interaction(text, "memory", "ok", reply)

        internet_data = ""
        if any(word in lower_action_text for word in ["latest", "today", "news", "price"]):
            internet_data = search_internet(action_text)

        if not client:
            reply = "Groq API key is missing, so I can only run local commands right now."
            speak(reply)
            return record_interaction(text, "none", "error", reply)

        context = f"""
You are STAR, Bajrangi's personal AI assistant.

User memory:
{storage.get_memory_dict()}

Recent conversation:
{storage.recent_conversation_text(limit=8)}

Internet data:
{internet_data}

Rules:
Reply short and natural.
Detect the user's language and reply in the same language/script.
Detect the user's emotional tone and match it with empathy.
If the user is excited, sound excited. If frustrated, be calm and helpful. If sad, be gentle.
For Hinglish, reply like a real Indian friend: simple, warm, casual, not formal textbook Hindi.
For Hindi, use normal spoken Hindi, not literal translation.
Avoid robotic words like "sahayata pradan", "vartamaan", "kripya" unless the user is very formal.

User: {text}
"""

        try:
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.5,
                max_tokens=100,
                messages=[{"role": "user", "content": context}],
            )
            reply = res.choices[0].message.content.strip()
        except Exception as exc:
            print("AI response failed:", exc)
            reply = "I could not reach the AI service right now."

        first_sentence = reply.split(".")[0].strip()
        final_reply = f"{first_sentence}." if first_sentence else reply

        for sentence in reply.split("."):
            sentence = sentence.strip()
            if sentence:
                speak(sentence)

        return record_interaction(text, "none", "ok", final_reply)
    finally:
        SPEECH_CONTEXT = None


# ------------------- API ENDPOINTS -------------------

@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard():
    return FileResponse(WEB_DIR / "dashboard.html")


@app.get("/mobile")
def mobile_app():
    return FileResponse(WEB_DIR / "mobile.html")


@app.get("/ask-star")
def ask(q: str):
    return {"reply": ask_star(q)}


@app.get("/memory")
def show_memory(category: Optional[str] = None, limit: int = 100):
    return {
        "items": storage.list_memory(category=category, limit=limit),
        "memory": storage.get_memory_dict(),
    }


@app.post("/memory")
def edit_memory(key: str, value: str, category: Optional[str] = None):
    final_category = category or infer_memory_category(key)
    saved = storage.set_memory(key, value, final_category, "api")
    return {"status": "saved" if saved else "ignored", "key": storage.normalize_key(key)}


@app.delete("/memory/{key}")
def forget_memory(key: str):
    deleted = storage.delete_memory(key)
    return {"status": "deleted" if deleted else "not_found", "key": storage.normalize_key(key)}


@app.delete("/memory")
def forget_all_memory(confirm: bool = False):
    if not confirm:
        return {"status": "confirmation_required", "hint": "Call with confirm=true to clear all memory."}

    storage.clear_memory()
    return {"status": "cleared"}


@app.get("/history")
def conversation_history(limit: int = 20):
    return {"items": storage.list_conversations(limit=limit)}


@app.get("/commands")
def command_history(limit: int = 50):
    return {"items": storage.list_commands(limit=limit)}


@app.get("/logs")
def logs(limit: int = 50):
    return {"items": storage.list_logs(limit=limit)}


@app.get("/settings")
def settings():
    return {
        "groq_configured": bool(client),
        "picovoice_configured": bool(os.getenv("PICOVOICE_ACCESS_KEY")),
        "email_configured": star_email.is_configured(),
        "database": str(storage.DB_FILE),
        "wake_word_file_exists": (BASE_DIR / "Hello-STAR_en_windows_v4_0_0.ppn").exists(),
        "speaker_file_exists": SPEAKER_FILE.exists(),
        "pending_confirmation": PENDING_CONFIRMATION["description"] if PENDING_CONFIRMATION else None,
        "security_mode": star_security.get_mode(),
        "voice": star_voice.get_settings(),
    }


@app.get("/voice/status")
def voice_status():
    return {
        "settings": star_voice.get_settings(),
        "recognition_languages": star_voice.recognition_languages(),
        "last": star_voice.last_voice_state(),
        "pending_confirmation": PENDING_CONFIRMATION["description"] if PENDING_CONFIRMATION else None,
    }


@app.get("/voice/settings")
def voice_get_settings():
    settings_data = star_voice.get_settings()
    return {
        "settings": settings_data,
        "recognition_languages": star_voice.recognition_languages(settings_data),
    }


@app.post("/voice/settings")
def voice_update_settings(
    mode: Optional[str] = None,
    language: Optional[str] = None,
    primary_language: Optional[str] = None,
    timeout: Optional[float] = None,
    phrase_time_limit: Optional[float] = None,
    pause_threshold: Optional[float] = None,
    energy_threshold: Optional[int] = None,
    spoken_confirmations: Optional[bool] = None,
    wake_engine: Optional[str] = None,
    wake_phrases: Optional[str] = None,
    voice_quiet: Optional[bool] = None,
    tts_voice: Optional[str] = None,
    tts_rate: Optional[str] = None,
    tts_pitch: Optional[str] = None,
):
    changed = star_voice.update_settings(
        voice_mode=mode,
        voice_language=language,
        voice_primary_language=primary_language,
        voice_timeout=timeout,
        voice_phrase_time_limit=phrase_time_limit,
        voice_pause_threshold=pause_threshold,
        voice_energy_threshold=energy_threshold,
        voice_spoken_confirmations=spoken_confirmations,
        voice_quiet=voice_quiet,
        wake_engine=wake_engine,
        wake_phrases=wake_phrases,
        tts_voice=tts_voice,
        tts_rate=tts_rate,
        tts_pitch=tts_pitch,
    )
    settings_data = star_voice.get_settings()
    return {
        "updated": changed,
        "settings": settings_data,
        "recognition_languages": star_voice.recognition_languages(settings_data),
    }


@app.post("/voice/remember")
def voice_remember(command: str, reply: str = ""):
    star_voice.remember_interaction(command, reply)
    return {"status": "saved", **star_voice.last_voice_state()}


@app.post("/voice/quiet")
def voice_quiet():
    stop_speaking()
    star_voice.set_voice_quiet(True)
    return {"status": "quiet", "voice_quiet": True}


@app.post("/voice/resume")
def voice_resume():
    star_voice.set_voice_quiet(False)
    reply = "Theek hai bhai, ab main baat kar sakta hoon."
    speak(reply)
    return {"status": "resumed", "voice_quiet": False, "reply": reply}


@app.post("/voice/sleep")
def voice_sleep():
    star_voice.set_voice_quiet(False)
    stop_speaking()
    return {
        "status": "sleep",
        "voice_quiet": False,
        "reply": "Theek hai bhai, main sleep mode me hoon. Hello star bolo, fir main sununga.",
    }


@app.post("/voice/repeat")
def voice_repeat(speak_out: bool = True):
    last = star_voice.last_voice_state()
    reply = last.get("last_reply") or "I do not have a voice reply to repeat yet."
    if speak_out and last.get("last_reply"):
        speak(reply)
    return {"reply": reply, "spoken": bool(speak_out and last.get("last_reply"))}


@app.get("/system")
def system_status():
    return star_system.get_system_status()


@app.get("/system/processes")
def system_processes(limit: int = 25):
    return {"items": star_system.list_processes(limit=limit)}


@app.get("/system/apps")
def system_apps(limit: int = 100):
    return {"items": star_system.list_installed_apps(APP_DATABASE, limit=limit)}


@app.get("/security")
def security_get_status():
    return star_security.security_status(BASE_DIR)


@app.post("/security/mode")
def security_set_mode(mode: str):
    changed = star_security.set_mode(mode)
    return {"status": "updated" if changed else "invalid_mode", "mode": star_security.get_mode()}


@app.get("/security/check")
def security_check(command: str, tool: Optional[str] = None):
    return star_security.classify_command(command, tool=tool)


@app.get("/security/audit")
def security_audit(limit: int = 50):
    items = [item for item in storage.list_logs(limit=limit) if item["event"].startswith("security_")]
    return {"items": items}


@app.get("/analytics")
def analytics_summary():
    return star_analytics.full_summary()


@app.get("/analytics/commands")
def analytics_commands():
    return star_analytics.command_summary()


@app.get("/analytics/daily")
def analytics_daily(limit: int = 14):
    return {"items": star_analytics.daily_commands(limit=limit)}


@app.get("/analytics/tools")
def analytics_tools():
    return {"items": star_analytics.tool_breakdown()}


@app.get("/analytics/errors")
def analytics_errors(limit: int = 10):
    return star_analytics.recent_errors(limit=limit)


@app.post("/vision/screenshot")
def vision_screenshot():
    return {"path": star_vision.capture_screenshot()}


@app.get("/vision/analyze")
def vision_analyze(path: str):
    return star_vision.analyze_image(path)


@app.get("/vision/ocr")
def vision_ocr(path: str):
    return star_vision.ocr_image(path)


@app.get("/vision/qr")
def vision_qr(path: str):
    return star_vision.decode_qr(path)


@app.get("/vision/barcode")
def vision_barcode(path: str):
    return star_vision.decode_barcodes(path)


@app.get("/vision/screen")
def vision_screen():
    return star_vision.screen_summary()


@app.get("/vision/compare")
def vision_compare(first: str, second: str):
    return star_vision.compare_images(first, second)


@app.get("/email/status")
def email_status():
    return star_email.status()


@app.get("/email/test")
def email_test():
    return star_email.test_connection()


@app.get("/email/inbox")
def email_inbox(limit: int = 10, unread_only: bool = False):
    try:
        return {"items": star_email.list_emails(limit=limit, unread_only=unread_only)}
    except RuntimeError as exc:
        return {"error": str(exc), "items": []}


@app.get("/email/search")
def email_search(q: str, limit: int = 10):
    try:
        return {"items": star_email.search_emails(q, limit=limit)}
    except RuntimeError as exc:
        return {"error": str(exc), "items": []}


@app.post("/email/send")
def email_send(to: str, subject: str, body: str):
    try:
        return star_email.send_email(to, subject, body)
    except RuntimeError as exc:
        return {"error": str(exc), "status": "not_configured"}


@app.post("/email/{message_id}/archive")
def email_archive(message_id: str):
    try:
        return star_email.archive_email(message_id)
    except RuntimeError as exc:
        return {"error": str(exc), "status": "not_configured"}


@app.delete("/email/{message_id}")
def email_delete(message_id: str):
    try:
        return star_email.delete_email(message_id)
    except RuntimeError as exc:
        return {"error": str(exc), "status": "not_configured"}


@app.post("/calendar/events")
def calendar_create(title: str, starts_at: str, ends_at: Optional[str] = None, location: Optional[str] = None, notes: Optional[str] = None):
    try:
        start = datetime.datetime.fromisoformat(starts_at)
        end = datetime.datetime.fromisoformat(ends_at) if ends_at else None
    except ValueError:
        return {"status": "invalid_datetime"}

    event_id = star_calendar.add_event(title, start, ends_at=end, location=location, notes=notes)
    return {"status": "saved" if event_id else "ignored", "id": event_id}


@app.post("/calendar/events/from-text")
def calendar_create_from_text(text: str):
    result = star_calendar.create_event_from_text(text)
    if result.get("error"):
        return {"status": "invalid_event", "error": result["error"]}
    return {
        "status": "saved",
        "id": result["id"],
        "title": result["title"],
        "starts_at": result["starts_at"].isoformat(),
        "ends_at": result["ends_at"].isoformat(),
        "location": result["location"],
    }


@app.get("/calendar/events")
def calendar_events(limit: int = 20, status: str = "scheduled"):
    return {"items": star_calendar.list_events(limit=limit, status=status)}


@app.get("/calendar/upcoming")
def calendar_upcoming(limit: int = 10):
    return {"items": star_calendar.upcoming_events(limit=limit)}


@app.get("/calendar/agenda")
def calendar_agenda(day: str = "today"):
    clean_day = "tomorrow" if day.lower() == "tomorrow" else "today"
    return {"items": star_calendar.agenda(clean_day)}


@app.post("/calendar/events/{event_id}/cancel")
def calendar_cancel(event_id: int):
    return {"status": "cancelled" if star_calendar.cancel_event(event_id) else "not_found", "id": event_id}


@app.delete("/calendar/events/{event_id}")
def calendar_delete(event_id: int):
    return {"status": "deleted" if star_calendar.delete_event(event_id) else "not_found", "id": event_id}


@app.post("/contacts")
def contacts_create(name: str, email: Optional[str] = None, phone: Optional[str] = None, company: Optional[str] = None, notes: Optional[str] = None):
    contact_id = star_contacts.add_contact(name, email=email, phone=phone, company=company, notes=notes)
    return {"status": "saved" if contact_id else "ignored", "id": contact_id}


@app.get("/contacts")
def contacts_list(q: Optional[str] = None, limit: int = 50):
    if q:
        return {"items": star_contacts.search_contacts(q, limit=limit)}
    return {"items": star_contacts.list_contacts(limit=limit)}


@app.get("/contacts/{contact_id}")
def contacts_get(contact_id: int):
    contact = star_contacts.get_contact(contact_id)
    return contact or {"status": "not_found", "id": contact_id}


@app.patch("/contacts/{contact_id}")
def contacts_update(contact_id: int, name: Optional[str] = None, email: Optional[str] = None, phone: Optional[str] = None, company: Optional[str] = None, notes: Optional[str] = None):
    updated = star_contacts.update_contact(contact_id, name=name, email=email, phone=phone, company=company, notes=notes)
    return {"status": "updated" if updated else "not_found", "id": contact_id}


@app.delete("/contacts/{contact_id}")
def contacts_delete(contact_id: int):
    return {"status": "deleted" if star_contacts.delete_contact(contact_id) else "not_found", "id": contact_id}


@app.get("/clipboard")
def clipboard_get():
    try:
        text_value = star_clipboard.get_text()
        return {"text": text_value, "chars": len(text_value)}
    except Exception as exc:
        return {"error": str(exc), "text": "", "chars": 0}


@app.post("/clipboard")
def clipboard_set(text: str):
    try:
        return star_clipboard.set_text(text)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@app.post("/clipboard/paste")
def clipboard_paste(text: str):
    try:
        return star_clipboard.paste_text(text)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@app.post("/snippets")
def snippets_create(name: str, content: str, tags: Optional[str] = None):
    snippet_id = star_clipboard.add_snippet(name, content, tags=tags)
    return {"status": "saved" if snippet_id else "ignored", "id": snippet_id}


@app.get("/snippets")
def snippets_list(q: Optional[str] = None, limit: int = 50):
    if q:
        return {"items": star_clipboard.search_snippets(q, limit=limit)}
    return {"items": star_clipboard.list_snippets(limit=limit)}


@app.get("/snippets/{snippet_id}")
def snippets_get(snippet_id: int):
    snippet = star_clipboard.get_snippet(snippet_id)
    return snippet or {"status": "not_found", "id": snippet_id}


@app.patch("/snippets/{snippet_id}")
def snippets_update(snippet_id: int, name: Optional[str] = None, content: Optional[str] = None, tags: Optional[str] = None):
    updated = star_clipboard.update_snippet(snippet_id, name=name, content=content, tags=tags)
    return {"status": "updated" if updated else "not_found", "id": snippet_id}


@app.post("/snippets/{snippet_id}/copy")
def snippets_copy(snippet_id: int):
    snippet = star_clipboard.get_snippet(snippet_id)
    if not snippet:
        return {"status": "not_found", "id": snippet_id}
    result = star_clipboard.set_text(snippet["content"])
    return {"status": result["status"], "id": snippet_id, "chars": result["chars"]}


@app.post("/snippets/{snippet_id}/paste")
def snippets_paste(snippet_id: int):
    snippet = star_clipboard.get_snippet(snippet_id)
    if not snippet:
        return {"status": "not_found", "id": snippet_id}
    result = star_clipboard.paste_text(snippet["content"])
    return {"status": result["status"], "id": snippet_id, "chars": result["chars"]}


@app.delete("/snippets/{snippet_id}")
def snippets_delete(snippet_id: int):
    return {"status": "deleted" if star_clipboard.delete_snippet(snippet_id) else "not_found", "id": snippet_id}


@app.post("/finance/transactions")
def finance_create(kind: str, amount: float, category: str = "general", note: Optional[str] = None, currency: str = "INR"):
    transaction_id = star_finance.add_transaction(kind, amount, category=category, note=note, currency=currency)
    return {"status": "saved" if transaction_id else "ignored", "id": transaction_id}


@app.post("/finance/transactions/from-text")
def finance_create_from_text(kind: str, text: str):
    result = star_finance.create_from_text(kind.lower(), text)
    if result.get("error"):
        return {"status": "invalid_transaction", "error": result["error"]}
    return {"status": "saved", **result}


@app.get("/finance/transactions")
def finance_transactions(limit: int = 50, kind: Optional[str] = None):
    clean_kind = kind.lower() if kind else None
    return {"items": star_finance.list_transactions(limit=limit, kind=clean_kind)}


@app.get("/finance/summary")
def finance_summary():
    return star_finance.summary()


@app.get("/finance/categories")
def finance_categories(limit: int = 10):
    return {"items": star_finance.category_summary(limit=limit)}


@app.delete("/finance/transactions/{transaction_id}")
def finance_delete(transaction_id: int):
    return {"status": "deleted" if star_finance.delete_transaction(transaction_id) else "not_found", "id": transaction_id}


@app.post("/health/logs")
def health_logs_create(metric: str, value: Optional[float] = None, unit: Optional[str] = None, note: Optional[str] = None):
    log_id = star_health.add_log(metric, value=value, unit=unit, note=note)
    return {"status": "saved" if log_id else "ignored", "id": log_id}


@app.post("/health/logs/from-text")
def health_logs_from_text(kind: str, text: str):
    clean_kind = kind.lower().strip()
    if clean_kind == "water":
        result = star_health.log_water(text)
    elif clean_kind == "sleep":
        result = star_health.log_sleep(text)
    elif clean_kind in {"workout", "exercise"}:
        result = star_health.log_workout(text)
    elif clean_kind == "weight":
        result = star_health.log_weight(text)
    elif clean_kind == "mood":
        result = star_health.log_mood(text)
    else:
        return {"status": "invalid_metric"}
    if result.get("error"):
        return {"status": "invalid_log", "error": result["error"]}
    return {"status": "saved", **result}


@app.get("/health/logs")
def health_logs_list(limit: int = 50, metric: Optional[str] = None):
    return {"items": star_health.list_logs(limit=limit, metric=metric)}


@app.get("/health/summary")
def health_summary(day: str = "today"):
    clean_day = "yesterday" if day.lower() == "yesterday" else "today"
    return star_health.summary(clean_day)


@app.delete("/health/logs/{log_id}")
def health_logs_delete(log_id: int):
    return {"status": "deleted" if star_health.delete_log(log_id) else "not_found", "id": log_id}


@app.get("/suggestions")
def suggestions_list(limit: int = 10):
    return {"items": star_suggestions.generate_suggestions(limit=limit)}


@app.post("/suggestions/feedback")
def suggestions_feedback(key: str, action: str = "accept", details: Optional[str] = None):
    star_suggestions.add_feedback(key, action, details=details)
    return {"status": "saved", "key": key, "action": action}


@app.get("/integrations/status")
def integrations_status():
    return star_integrations.integration_status()


@app.get("/integrations/diagnostics")
def integrations_diagnostics():
    return {
        "status": star_integrations.integration_status(),
        "email": star_email.status(),
        "smart_home": star_integrations.home_assistant_status(),
        "mobile": star_integrations.mobile_pull(limit=5),
    }


@app.post("/integrations")
def integrations_create(name: str, kind: str, status: str = "planned"):
    integration_id = star_integrations.save_integration(name, kind, status=status)
    return {"status": "saved" if integration_id else "ignored", "id": integration_id}


@app.get("/integrations")
def integrations_list(kind: Optional[str] = None, limit: int = 50):
    return {"items": star_integrations.list_integrations(kind=kind, limit=limit)}


@app.delete("/integrations/{integration_id}")
def integrations_delete(integration_id: int):
    return {"status": "deleted" if star_integrations.delete_integration(integration_id) else "not_found", "id": integration_id}


@app.post("/cloud/sync")
def cloud_sync():
    return star_integrations.cloud_sync_snapshot(BASE_DIR)


@app.get("/mobile/notifications")
def mobile_notifications(status: str = "queued", limit: int = 50):
    return {"items": star_integrations.list_mobile_notifications(status=status, limit=limit)}


@app.get("/mobile/pull")
def mobile_pull(secret: Optional[str] = None, limit: int = 20):
    return star_integrations.mobile_pull(secret=secret, limit=limit)


@app.get("/mobile/status")
def mobile_status(secret: Optional[str] = None):
    authorized = star_integrations.validate_mobile_secret(secret)
    if not authorized:
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "status"})
        return {"authorized": False, "error": "invalid_secret"}
    voice_settings = star_voice.get_settings()
    return {
        "authorized": True,
        "server": "online",
        "mobile": star_integrations.integration_status()["mobile"],
        "voice": {
            "quiet": star_voice.is_voice_quiet(voice_settings),
            "wake_phrases": star_voice.wake_phrases(voice_settings),
            "languages": star_voice.recognition_languages(voice_settings),
        },
        "notifications": len(star_integrations.list_mobile_notifications(status="queued", limit=100)),
        "dashboard": "/dashboard",
        "mobile_app": "/mobile",
    }


@app.post("/mobile/devices/register")
def mobile_device_register(
    device_id: str,
    name: str = "STAR Phone",
    platform: str = "android",
    capabilities: str = "",
    secret: Optional[str] = None,
):
    if not star_integrations.validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "device_register"})
        return {"authorized": False, "error": "invalid_secret"}
    device = star_integrations.register_mobile_device(device_id, name=name, platform=platform, capabilities=capabilities)
    return {"authorized": True, "device": device}


@app.get("/mobile/devices")
def mobile_devices(secret: Optional[str] = None, limit: int = 50):
    if not star_integrations.validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "devices"})
        return {"authorized": False, "items": [], "error": "invalid_secret"}
    return {"authorized": True, "items": star_integrations.list_mobile_devices(limit=limit)}


@app.post("/mobile/actions")
def mobile_action_create(action: str, payload: str = "", device_id: Optional[str] = None, secret: Optional[str] = None):
    if not star_integrations.validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "action_create"})
        return {"authorized": False, "error": "invalid_secret"}
    action_id = star_integrations.queue_mobile_action(action, payload=payload, device_id=device_id)
    return {"authorized": True, "status": "queued" if action_id else "ignored", "id": action_id}


@app.get("/mobile/actions")
def mobile_actions(status: str = "queued", limit: int = 50, secret: Optional[str] = None):
    if not star_integrations.validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "actions"})
        return {"authorized": False, "items": [], "error": "invalid_secret"}
    return {"authorized": True, "items": star_integrations.list_mobile_actions(status=status, limit=limit)}


@app.get("/mobile/actions/pull")
def mobile_action_pull(device_id: str, secret: Optional[str] = None, limit: int = 5):
    return star_integrations.mobile_action_pull(device_id=device_id, secret=secret, limit=limit)


@app.post("/mobile/actions/{action_id}/complete")
def mobile_action_complete(action_id: int, device_id: str, status: str = "done", result: str = "", secret: Optional[str] = None):
    if not star_integrations.validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "action_complete"})
        return {"authorized": False, "error": "invalid_secret"}
    completed = star_integrations.complete_mobile_action(action_id, device_id=device_id, status=status, result=result)
    return {"authorized": True, "status": "updated" if completed else "not_found", "id": action_id}


@app.post("/mobile/command")
def mobile_command(command: str, secret: Optional[str] = None):
    if not star_integrations.validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "command"})
        return {"authorized": False, "reply": "", "error": "invalid_secret"}
    tts_token = SUPPRESS_TTS.set(True)
    try:
        reply = ask_star(command)
    finally:
        SUPPRESS_TTS.reset(tts_token)
    settings = star_voice.get_settings()
    return {
        "authorized": True,
        "reply": reply,
        "voice": {
            "quiet": star_voice.is_voice_quiet(settings),
            "sleep_requested": star_voice.is_exit_listening_command(command),
            "resume_requested": star_voice.is_resume_command(command),
        },
        "last": star_voice.last_voice_state(),
    }


@app.post("/mobile/notifications")
def mobile_notification_create(title: str, body: str):
    notification_id = star_integrations.queue_mobile_notification(title, body)
    return {"status": "queued" if notification_id else "ignored", "id": notification_id}


@app.post("/mobile/notifications/{notification_id}/read")
def mobile_notification_read(notification_id: int):
    return {"status": "read" if star_integrations.mark_mobile_notification_read(notification_id) else "not_found", "id": notification_id}


@app.delete("/mobile/notifications/{notification_id}")
def mobile_notification_delete(notification_id: int):
    return {"status": "deleted" if star_integrations.delete_mobile_notification(notification_id) else "not_found", "id": notification_id}


@app.get("/smart-home/status")
def smart_home_status():
    return star_integrations.home_assistant_status()


@app.post("/smart-home/service")
def smart_home_service(domain: str, service: str, entity_id: Optional[str] = None):
    return star_integrations.call_home_assistant_service(domain, service, entity_id=entity_id)


@app.get("/files/search")
def files_search(q: str, folder: Optional[str] = None, limit: int = 20):
    return {"items": star_files.search_files(q, folder=folder, limit=limit)}


@app.get("/files/read")
def files_read(path: str, max_chars: int = 12000):
    return star_files.read_file(path, max_chars=max_chars)


@app.get("/files/analyze")
def files_analyze(path: Optional[str] = None):
    return star_files.analyze_folder(path)


@app.get("/files/summarize")
def files_summarize(path: str):
    result = star_files.read_file(path, max_chars=30000)
    if result.get("error"):
        return result
    return {
        "path": result["path"],
        "summary": star_files.summarize_text(result["text"], max_sentences=6),
        "truncated": result["truncated"],
    }


@app.get("/research/search")
def research_search(q: str, limit: int = 5):
    return star_research.research_summary(q, max_results=limit)


@app.get("/research/news")
def research_news(q: str = "latest news", limit: int = 5):
    return star_research.latest_news(q, max_results=limit)


@app.get("/research/weather")
def research_weather(location: str):
    return star_research.weather(location)


@app.get("/research/webpage")
def research_webpage(url: str):
    return star_research.summarize_webpage(url)


@app.post("/browser/open")
def browser_open(target: str):
    return {"reply": star_browser.open_website(target)}


@app.post("/browser/search")
def browser_search(q: str, engine: str = "google"):
    if engine.lower() in {"duckduckgo", "ddg"}:
        reply = star_browser.search_duckduckgo(q)
    else:
        reply = star_browser.search_google(q)
    return {"reply": reply}


@app.post("/browser/tab/new")
def browser_new_tab(target: Optional[str] = None):
    return {"reply": star_browser.new_tab(target)}


@app.post("/browser/tab/close")
def browser_close_tab():
    return {"reply": star_browser.close_tab()}


@app.post("/browser/tab/next")
def browser_next_tab():
    return {"reply": star_browser.next_tab()}


@app.post("/browser/tab/previous")
def browser_previous_tab():
    return {"reply": star_browser.previous_tab()}


@app.post("/browser/refresh")
def browser_refresh():
    return {"reply": star_browser.refresh_page()}


@app.post("/browser/download")
def browser_download(url: str):
    return star_browser.download_file(url)


@app.post("/media/play-pause")
def media_play_pause():
    return {"reply": star_media.play_pause()}


@app.post("/media/next")
def media_next():
    return {"reply": star_media.next_track()}


@app.post("/media/previous")
def media_previous():
    return {"reply": star_media.previous_track()}


@app.post("/media/stop")
def media_stop():
    return {"reply": star_media.stop_media()}


@app.post("/media/youtube")
def media_youtube(q: Optional[str] = None):
    return {"reply": star_media.open_youtube(q)}


@app.post("/media/spotify")
def media_spotify(q: Optional[str] = None):
    return {"reply": star_media.open_spotify(q)}


@app.post("/whatsapp/send")
def whatsapp_send(contact: str, message: str):
    driver = None
    try:
        driver = create_chrome_driver()
        reply = star_whatsapp.send_message(driver, contact, message)
        return {"reply": reply}
    finally:
        if driver:
            driver.quit()


@app.get("/whatsapp/status")
def whatsapp_status():
    driver = None
    try:
        driver = create_chrome_driver()
        return star_whatsapp.open_whatsapp(driver)
    except Exception as exc:
        storage.add_log("warning", "whatsapp_status_failed", str(exc))
        return {"logged_in": False, "needs_login": True, "message": "WhatsApp status check failed.", "error": str(exc)}
    finally:
        if driver:
            driver.quit()


@app.get("/whatsapp/url")
def whatsapp_url(phone: str, message: str = ""):
    return {"url": star_whatsapp.web_send_url(phone, message)}


@app.get("/coding/analyze")
def coding_analyze(path: Optional[str] = None):
    return star_coding.analyze_project(path)


@app.get("/coding/search")
def coding_search(q: str, path: Optional[str] = None, limit: int = 20):
    return {"items": star_coding.search_code(q, root=path, limit=limit)}


@app.get("/coding/explain")
def coding_explain(path: str):
    return star_coding.explain_file(path)


@app.get("/coding/review")
def coding_review(path: str):
    return star_coding.review_python_file(path)


@app.post("/coding/compile")
def coding_compile():
    return star_coding.compile_python()


@app.get("/git/status")
def git_status():
    return star_git.status()


@app.get("/git/log")
def git_log(limit: int = 5):
    return star_git.log(limit=limit)


@app.get("/git/diff")
def git_diff(path: Optional[str] = None):
    return star_git.diff(path=path)


@app.get("/git/branch")
def git_branch():
    return star_git.branch()


@app.get("/git/remotes")
def git_remotes():
    return star_git.remotes()


@app.post("/automations")
def automation_create(command: str, schedule: str, name: Optional[str] = None, interval_minutes: Optional[int] = None):
    due_at = star_automation.parse_schedule(schedule)
    if not due_at:
        return {"status": "invalid_schedule"}
    automation_id = star_automation.create_command_automation(
        name=name or command[:60],
        command=command,
        next_run_at=due_at,
        interval_minutes=interval_minutes,
    )
    return {"status": "saved" if automation_id else "ignored", "id": automation_id, "next_run_at": due_at.isoformat()}


@app.post("/automations/workflow")
def automation_workflow_create(name: str, steps: str, schedule: Optional[str] = None):
    step_list = [item.strip() for item in steps.split("|") if item.strip()]
    due_at = star_automation.parse_schedule(schedule) if schedule else None
    automation_id = star_automation.create_workflow(name=name, steps=step_list, next_run_at=due_at)
    return {"status": "saved" if automation_id else "ignored", "id": automation_id}


@app.get("/automations")
def automation_list(status: str = "active", limit: int = 50):
    return {"items": star_automation.list_automations(status=status, limit=limit)}


@app.get("/automations/due")
def automation_due(limit: int = 20):
    return {"items": star_automation.due_automations(limit=limit)}


@app.post("/automations/run-due")
def automation_run_due(limit: int = 10):
    return {"items": run_due_automations(limit=limit)}


@app.post("/automations/{automation_id}/pause")
def automation_pause(automation_id: int):
    changed = star_automation.pause_automation(automation_id)
    return {"status": "paused" if changed else "not_found", "id": automation_id}


@app.post("/automations/{automation_id}/resume")
def automation_resume(automation_id: int):
    changed = star_automation.resume_automation(automation_id)
    return {"status": "active" if changed else "not_found", "id": automation_id}


@app.delete("/automations/{automation_id}")
def automation_delete(automation_id: int):
    deleted = star_automation.delete_automation(automation_id)
    return {"status": "deleted" if deleted else "not_found", "id": automation_id}


@app.get("/automations/runs")
def automation_runs(automation_id: Optional[int] = None, limit: int = 50):
    return {"items": star_automation.list_runs(automation_id=automation_id, limit=limit)}


@app.post("/notes")
def notes_create(content: str, title: Optional[str] = None, category: str = "general"):
    note_id = star_productivity.add_note(content, title=title, category=category)
    return {"status": "saved" if note_id else "ignored", "id": note_id}


@app.get("/notes")
def notes_list(q: Optional[str] = None, limit: int = 20):
    return {"items": star_productivity.list_notes(query=q, limit=limit)}


@app.delete("/notes/{note_id}")
def notes_delete(note_id: int):
    deleted = star_productivity.delete_note(note_id)
    return {"status": "deleted" if deleted else "not_found", "id": note_id}


@app.post("/tasks")
def tasks_create(title: str, priority: str = "normal", due: Optional[str] = None):
    due_at = star_productivity.parse_due_time(due or "") if due else None
    task_id = star_productivity.add_task(title, priority=priority, due_at=due_at)
    return {"status": "saved" if task_id else "ignored", "id": task_id}


@app.get("/tasks")
def tasks_list(status: str = "open", limit: int = 20):
    return {"items": star_productivity.list_tasks(status=status, limit=limit)}


@app.post("/tasks/{task_id}/complete")
def tasks_complete(task_id: int):
    completed = star_productivity.complete_task(task_id)
    return {"status": "completed" if completed else "not_found", "id": task_id}


@app.delete("/tasks/{task_id}")
def tasks_delete(task_id: int):
    deleted = star_productivity.delete_task(task_id)
    return {"status": "deleted" if deleted else "not_found", "id": task_id}


@app.post("/reminders")
def reminders_create(text: str, due: str):
    due_at = star_productivity.parse_due_time(due)
    if not due_at:
        return {"status": "invalid_due_time"}
    reminder_id = star_productivity.add_reminder(text, due_at)
    return {"status": "saved" if reminder_id else "ignored", "id": reminder_id, "due_at": due_at.isoformat()}


@app.get("/reminders")
def reminders_list(status: str = "open", limit: int = 20):
    return {"items": star_productivity.list_reminders(status=status, limit=limit)}


@app.get("/reminders/due")
def reminders_due(limit: int = 20):
    return {"items": star_productivity.due_reminders(limit=limit)}


@app.post("/reminders/{reminder_id}/complete")
def reminders_complete(reminder_id: int):
    completed = star_productivity.complete_reminder(reminder_id)
    return {"status": "completed" if completed else "not_found", "id": reminder_id}


@app.delete("/reminders/{reminder_id}")
def reminders_delete(reminder_id: int):
    deleted = star_productivity.delete_reminder(reminder_id)
    return {"status": "deleted" if deleted else "not_found", "id": reminder_id}


@app.post("/pomodoro/start")
def pomodoro_start(minutes: int = 25, label: str = "focus"):
    return star_productivity.start_pomodoro(minutes=minutes, label=label)


@app.post("/pomodoro/stop")
def pomodoro_stop():
    return {"stopped": star_productivity.stop_pomodoro()}


@app.get("/pomodoro")
def pomodoro_get_status():
    return star_productivity.pomodoro_status()


@app.get("/briefing")
def briefing():
    status = star_system.get_system_status()
    return {"briefing": star_productivity.daily_briefing(star_system.format_system_summary(status))}


@app.post("/confirm")
def confirm_action():
    reply = handle_confirmation_command("confirm")
    return {"reply": reply or "Nothing is waiting for confirmation."}


@app.post("/cancel")
def cancel_action():
    reply = handle_confirmation_command("cancel")
    return {"reply": reply or "Nothing is waiting for cancellation."}


@app.get("/stop")
def stop():
    stopped = stop_speaking()
    return {"status": "stopped" if stopped else "idle"}


@app.get("/health")
def health():
    stats = storage.get_stats()
    return {
        "status": "ok",
        "groq_configured": bool(client),
        "picovoice_configured": bool(os.getenv("PICOVOICE_ACCESS_KEY")),
        "pending_confirmation": bool(PENDING_CONFIRMATION),
        "security_mode": star_security.get_mode(),
        **stats,
    }
