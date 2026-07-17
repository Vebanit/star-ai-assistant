# STAR Assistant

STAR is a local voice assistant for Windows. It listens for the custom wake word, sends spoken commands to a FastAPI backend, uses Groq for AI responses, and can run local PC actions such as opening apps, searching the web, taking screenshots, and basic WhatsApp/Instagram automation.

## Features

- Wake word activation with Picovoice Porcupine.
- Continuous speech recognition after wake word detection.
- FastAPI backend with `/ask-star`, `/memory`, `/history`, `/commands`, `/logs`, `/settings`, `/stop`, and `/health`.
- Web dashboard at `/dashboard` with chat, status, memory, tasks, reminders, logs, and command history.
- Groq-powered assistant replies and action planning.
- Edge TTS voice output.
- Persistent SQLite memory in `star.db`.
- Conversation history, command history, and local logs.
- Memory edit, recall, and forget commands.
- App, website, and folder opening.
- Process closing by fuzzy matching running process names.
- Screenshot, click, scroll, and typing controls through PyAutoGUI.
- System status for CPU, RAM, disk, battery, network, Windows info, processes, and installed apps.
- Volume and brightness controls.
- Confirmation flow for shutdown, restart, sleep, and lock commands.
- File search, file reading, file summary, and folder analysis.
- Research search, latest news, weather lookup, Wikipedia-style lookup, and webpage summary.
- Notes, tasks/to-do list, reminders, daily briefing, and Pomodoro timer.
- Browser tab controls, Google/DuckDuckGo search, and file download helper.
- Media controls for play/pause, next/previous, YouTube, Spotify, Netflix, and VLC.
- WhatsApp chat search/send helpers through WhatsApp Web.
- Coding helper for project analysis, code search, explain/review file, and Python compile checks.
- Git helper for status, log, diff, branch, remotes, and confirmed commit/pull/push.
- Smart automation for scheduled commands, simple workflows, due runs, and automation history.
- Google search command support.
- Basic WhatsApp Web and Instagram DM automation through Selenium.

## Setup

1. Create or activate the virtual environment.

```powershell
python -m venv venv
.\venv\Scripts\activate
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create `.env` with these keys.

```env
GROQ_API_KEY=your_groq_key
PICOVOICE_ACCESS_KEY=your_picovoice_key
```

4. Start the backend.

```powershell
uvicorn main:app --reload
```

5. Open the dashboard.

```text
http://127.0.0.1:8000/dashboard
```

6. In another terminal, start wake word listening.

```powershell
python wake_word.py
```

## Useful Commands

- `open chrome`
- `open downloads`
- `search Python tutorials`
- `take screenshot`
- `scroll down`
- `close chrome`
- `what is my name`
- `remember my city is Ahmedabad`
- `what do you remember`
- `forget my city`
- `system status`
- `cpu usage`
- `battery status`
- `show running processes`
- `show installed apps`
- `volume up`
- `brightness down`
- `shutdown pc` then `confirm` or `cancel`
- `find file README`
- `read file README.md`
- `summarize file main.py`
- `analyze folder downloads`
- `weather Ahmedabad`
- `latest news AI`
- `research Python FastAPI`
- `wikipedia Alan Turing`
- `summarize webpage https://example.com`
- `add note buy milk`
- `show notes`
- `add task finish STAR dashboard`
- `show tasks`
- `complete task 1`
- `remind me to drink water in 10 minutes`
- `show reminders`
- `daily briefing`
- `start pomodoro 25`
- `pomodoro status`
- `open website openai.com`
- `google search FastAPI tutorial`
- `duckduckgo search Python automation`
- `new tab github.com`
- `close tab`
- `next tab`
- `refresh page`
- `download file https://example.com/file.zip`
- `play music`
- `next song`
- `open youtube lo-fi music`
- `open spotify`
- `open netflix`
- `send whatsapp to Bajrangi message hello`
- `open whatsapp chat Bajrangi`
- `analyze project`
- `search code FastAPI`
- `explain file main.py`
- `review file main.py`
- `run compile check`
- `git status`
- `git log 5`
- `git diff`
- `git commit update STAR features` then `confirm` or `cancel`
- `schedule command system status in 10 minutes`
- `schedule daily briefing at 9 am`
- `create workflow system status then show tasks`
- `show automations`
- `run automations`
- `pause automation 1`
- `resume automation 1`
- `delete automation 1`
- `check whatsapp`

## API Helpers

- `GET /dashboard` - STAR web dashboard.
- `GET /memory` - view memory with metadata.
- `POST /memory?key=name&value=Bajrangi` - edit or add memory.
- `DELETE /memory/name` - forget one memory item.
- `DELETE /memory?confirm=true` - clear all memory.
- `GET /history` - recent conversation messages.
- `GET /commands` - recent command history.
- `GET /logs` - app logs.
- `GET /settings` - configuration status.
- `GET /system` - full system status.
- `GET /system/processes` - running processes.
- `GET /system/apps` - installed app shortcuts.
- `GET /files/search?q=README` - search files.
- `GET /files/read?path=README.md` - read a supported file.
- `GET /files/analyze?path=downloads` - analyze a folder.
- `GET /files/summarize?path=main.py` - summarize a supported file.
- `GET /research/search?q=FastAPI` - web research summary.
- `GET /research/news?q=AI` - latest news summary.
- `GET /research/weather?location=Ahmedabad` - weather summary.
- `GET /research/webpage?url=https://example.com` - webpage summary.
- `POST /notes?content=buy milk` - save a note.
- `GET /notes` - list notes.
- `POST /tasks?title=finish STAR` - create a task.
- `GET /tasks` - list tasks.
- `POST /tasks/1/complete` - complete a task.
- `POST /reminders?text=drink water&due=in 10 minutes` - create a reminder.
- `GET /reminders` - list reminders.
- `GET /reminders/due` - due reminders.
- `GET /briefing` - daily briefing.
- `POST /pomodoro/start?minutes=25` - start Pomodoro.
- `GET /pomodoro` - Pomodoro status.
- `POST /browser/open?target=openai.com` - open website/search target.
- `POST /browser/search?q=FastAPI&engine=google` - browser search.
- `POST /browser/tab/new?target=github.com` - new browser tab.
- `POST /browser/tab/close` - close current tab.
- `POST /browser/download?url=https://example.com/file.zip` - download a file.
- `POST /media/play-pause` - play/pause media.
- `POST /media/next` - next track.
- `POST /media/youtube?q=lo-fi` - open YouTube search.
- `POST /media/spotify` - open Spotify.
- `POST /whatsapp/send?contact=Name&message=Hello` - send via WhatsApp Web.
- `GET /whatsapp/url?phone=919999999999&message=Hello` - generate wa.me URL.
- `GET /coding/analyze` - project analysis.
- `GET /coding/search?q=FastAPI` - code search.
- `GET /coding/explain?path=main.py` - explain file structure.
- `GET /coding/review?path=main.py` - static Python review.
- `POST /coding/compile` - Python compile check.
- `GET /git/status` - git status.
- `GET /git/log?limit=5` - recent commits.
- `GET /git/diff` - current diff.
- `GET /git/branch` - current branch.
- `GET /git/remotes` - remotes.
- `POST /automations?command=system status&schedule=in 10 minutes` - schedule a command.
- `POST /automations/workflow?name=morning&steps=system status|show tasks` - create a workflow.
- `GET /automations` - list automations.
- `GET /automations/due` - due automations.
- `POST /automations/run-due` - run due automations.
- `POST /automations/1/pause` - pause automation.
- `POST /automations/1/resume` - resume automation.
- `DELETE /automations/1` - delete automation.
- `GET /automations/runs` - automation run history.
- `POST /confirm` - confirm a pending risky action.
- `POST /cancel` - cancel a pending risky action.

## Notes

- WhatsApp and Instagram automation depend on the current web UI and may need selector updates over time.
- Memory, history, commands, and logs are saved locally in `star.db`; this file is ignored by git because it can contain personal data.
- If `star_memory.json` exists from an older version, STAR imports it into SQLite on startup.
- PDF reading needs `pypdf` or `PyPDF2`; OCR will need an OCR engine in a later batch.
- WhatsApp send/search requires WhatsApp Web login and may need selector updates if WhatsApp changes its UI.
- Keep `.env` private.
