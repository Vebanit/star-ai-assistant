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

def speak(text):
    global current_process

    if not text:
        return False

    if current_process and current_process.poll() is None:
        current_process.terminate()

    try:
        current_process = subprocess.Popen(
            [sys.executable, str(SPEAKER_FILE), str(text)],
            cwd=str(BASE_DIR),
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
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service)


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


def open_anything(command):
    cmd = command.lower().replace("open ", "", 1).strip()

    aliases = {
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

    for key, target in aliases.items():
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


def close_anything(command):
    cmd = command.lower().replace("close ", "", 1).strip()
    processes = [p.info["name"] for p in psutil.process_iter(["name"]) if p.info.get("name")]
    match = difflib.get_close_matches(cmd, processes, n=1, cutoff=0.5)

    if not match:
        return False

    proc = match[0]
    speak(f"Closing {proc}")
    subprocess.run(["taskkill", "/IM", proc, "/F"], capture_output=True, text=True)
    return True


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
    text = command.lower().strip()

    if text in {"cancel", "cancel it", "no", "do not", "don't"}:
        if PENDING_CONFIRMATION:
            star_security.audit("confirmation_cancelled", "info", {"action": PENDING_CONFIRMATION["action"]})
            clear_pending_confirmation()
            return "Cancelled."
        return None

    if text not in {"confirm", "yes", "do it", "continue", "proceed"}:
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
    "none",
}


def detect_tool_without_ai(user_text):
    text = user_text.lower().strip()

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

def record_interaction(user_text, tool, status, reply):
    storage.add_command(user_text, tool, status, reply)
    storage.add_conversation("assistant", reply)
    storage.add_log(
        "info" if status == "ok" else "warning",
        "command_handled",
        {"tool": tool, "status": status},
    )
    return reply


def ask_star(user_text):
    text = user_text.strip()
    lower_text = text.lower()

    if not text:
        return "Please say something."

    storage.add_conversation("user", text)

    confirmation_reply = handle_confirmation_command(text)
    if confirmation_reply:
        speak(confirmation_reply)
        return record_interaction(text, "confirmation", "ok", confirmation_reply)

    memory_callback = lambda: handle_memory_command(text)
    if star_security.classify_command(text)["requires_confirmation"] and any(
        category == "memory_clear" for category in star_security.classify_command(text)["categories"]
    ):
        memory_reply = security_gate(text, "memory", memory_callback)
    else:
        memory_reply = memory_callback()
    if memory_reply:
        speak(memory_reply)
        return record_interaction(text, "memory", "ok", memory_reply)

    if open_chrome_and_search(text):
        return record_interaction(text, "search", "ok", "Done.")

    tool = agent_brain(text)
    if tool != "none":
        if tool in {"whatsapp", "browser", "automation"}:
            tool_reply = security_gate(text, tool, lambda: run_tool(tool, text))
        else:
            tool_reply = run_tool(tool, text)
        if tool_reply:
            return record_interaction(text, tool, "ok", tool_reply)

    extract_memory(text)

    direct = check_direct_memory(text)
    if direct:
        reply = f"It is {direct}."
        speak(reply)
        return record_interaction(text, "memory", "ok", reply)

    internet_data = ""
    if any(word in lower_text for word in ["latest", "today", "news", "price"]):
        internet_data = search_internet(text)

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

User: {text}
"""

    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            max_tokens=80,
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


# ------------------- API ENDPOINTS -------------------

@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard():
    return FileResponse(WEB_DIR / "dashboard.html")


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
        "database": str(storage.DB_FILE),
        "wake_word_file_exists": (BASE_DIR / "Hello-STAR_en_windows_v4_0_0.ppn").exists(),
        "speaker_file_exists": SPEAKER_FILE.exists(),
        "pending_confirmation": PENDING_CONFIRMATION["description"] if PENDING_CONFIRMATION else None,
        "security_mode": star_security.get_mode(),
    }


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
