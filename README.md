# STAR Assistant

STAR is a local voice assistant for Windows. It listens for the custom wake word, sends spoken commands to a FastAPI backend, uses Groq for AI responses, and can run local PC actions such as opening apps, searching the web, taking screenshots, and basic WhatsApp/Instagram automation.

## Features

- Free keyless wake activation with speech phrases such as `hello star`, `hey star`, and `star`.
- Optional Picovoice Porcupine wake word support if you install `pvporcupine` and provide an AccessKey.
- Continuous speech recognition after wake word detection.
- Background runtime scripts for duplicate-safe start, status, manual stop, and Windows logon auto-start.
- Voice brain settings for language fallback, listening timeout, phrase length, TTS voice/rate/pitch, repeat, stop, sleep, and spoken confirmation shortcuts.
- FastAPI backend with `/ask-star`, `/voice/status`, `/voice/settings`, `/memory`, `/history`, `/commands`, `/logs`, `/settings`, `/stop`, and `/health`.
- Web dashboard at `/dashboard` with chat, status, memory, tasks, reminders, voice settings, integrations, suggestions, logs, and command history.
- Groq-powered assistant replies and action planning.
- Edge TTS voice output.
- Female Edge TTS voice by default, currently `en-US-JennyNeural`.
- Emotion-aware replies that infer the user's tone and answer in the same language or style, with spoken Indian Hindi/Hinglish instead of stiff translation.
- Persistent SQLite memory in `star.db`.
- Conversation history, command history, and local logs.
- Memory edit, recall, and forget commands.
- App, website, and folder opening.
- Strong close commands for apps/browsers with English, Hinglish, and Hindi-style phrases like `close chrome`, `chrome band karo`, and `notepad bandh karo`.
- Screenshot, click, scroll, and typing controls through PyAutoGUI.
- System status for CPU, RAM, disk, battery, network, Windows info, processes, and installed apps.
- Volume and brightness controls.
- Confirmation flow for shutdown, restart, sleep, and lock commands.
- File search, file reading, file summary, and folder analysis.
- Research search, latest news, weather lookup, Wikipedia-style lookup, and webpage summary.
- Notes, tasks/to-do list, reminders, daily briefing, and Pomodoro timer.
- Calendar events, today/tomorrow agenda, upcoming events, cancel, and delete.
- Contacts/address book for saved names, email addresses, phone numbers, lookup, update, and delete.
- Clipboard and snippets helper for copy/read/paste plus reusable text templates.
- Finance tracker for income, expenses, category breakdowns, monthly balance, and transaction history.
- Health and habit tracker for water, mood, sleep, workout, weight, and daily wellness summaries.
- Multilingual command normalization for Hinglish/Hindi/local phrases, with optional Groq-powered command translation.
- Hinglish-friendly voice cleanup for common misheard words such as confirm/cancel, plus English/Hindi recognition fallback.
- Worldwide same-language response adaptation for natural conversation tone and emotion matching.
- Self-learning smart suggestions from usage patterns, tasks, reminders, health, finance, and recent errors.
- Cloud/mobile/smart-home foundation with local cloud snapshots, mobile notification queue, integration registry, and Home Assistant hooks.
- Browser tab controls, Google/DuckDuckGo search, and file download helper.
- Media controls for play/pause, next/previous, YouTube, Spotify, Netflix, and VLC.
- WhatsApp chat search/send helpers through WhatsApp Web.
- WhatsApp persistent Chrome profile, login status checks, and better Selenium waits for WhatsApp Web.
- Email IMAP/SMTP connection diagnostics, timeout settings, and retry handling.
- Mobile pull endpoint with optional shared-secret auth for queued notifications.
- Smart-home validation and retry handling for Home Assistant service calls.
- Coding helper for project analysis, code search, explain/review file, and Python compile checks.
- Git helper for status, log, diff, branch, remotes, and confirmed commit/pull/push.
- Smart automation for scheduled commands, simple workflows, due runs, and automation history.
- Security mode, permission checks, confirmation gates, secret health, and audit logs.
- Analytics for command success rate, top tools, daily activity, productivity, memory, and recent issues.
- Vision helper for screenshots, image analysis, OCR, QR/barcode scan, and image comparison.
- Email helper for IMAP inbox, unread/search, SMTP send, archive, and delete.
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
EMAIL_ADDRESS=your_email_address
EMAIL_APP_PASSWORD=your_email_app_password
```

`PICOVOICE_ACCESS_KEY` is optional now. Without it, STAR uses the free keyless speech wake mode.

4. Start STAR manually.

```powershell
.\scripts\start_star.ps1
```

This starts the backend and wake-word listener in the background. It is duplicate-safe, so running it again will not start extra backend copies.

5. Open the dashboard.

```text
http://127.0.0.1:8000/dashboard
```

6. Install auto-start once.

```powershell
.\scripts\install_startup.ps1
```

After this, STAR starts automatically when this Windows user logs in. It keeps running until the laptop shuts down, restarts, or you manually stop it.

Useful runtime scripts:

```powershell
.\scripts\status_star.ps1
.\scripts\stop_star.ps1
.\scripts\uninstall_startup.ps1
```

Voice behavior:

- `stop` stops STAR's current speech only. It does not stop the server.
- `sleep` exits conversation mode and keeps wake-word listening alive.
- `stop server`, `close backend`, and similar commands are blocked from voice so the server stays on.
- To fully stop STAR manually, use `.\scripts\stop_star.ps1`.
- If Picovoice fails or no key is configured, STAR falls back to free keyless speech wake mode.

## Useful Commands

- `open chrome`
- `close chrome`
- `chrome band karo`
- `notepad bandh karo`
- `close current tab`
- `close current window`
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
- `add event dentist tomorrow at 5 pm for 30 minutes location clinic`
- `today agenda`
- `tomorrow agenda`
- `upcoming events`
- `cancel event 1`
- `delete event 1`
- `add contact Bajrangi email bajrangi@example.com phone +919999999999`
- `show contacts`
- `find contact Bajrangi`
- `set contact email Bajrangi to bajrangi@example.com`
- `set contact phone Bajrangi to +919999999999`
- `delete contact 1`
- `read clipboard`
- `copy text hello from STAR`
- `paste text hello from STAR` then `confirm` or `cancel`
- `save snippet greeting as hello, how are you?`
- `show snippets`
- `search snippets greeting`
- `copy snippet 1`
- `paste snippet 1` then `confirm` or `cancel`
- `delete snippet 1`
- `add expense 250 for food note lunch`
- `add income 5000 for salary`
- `finance summary`
- `monthly expenses`
- `expense categories`
- `show transactions`
- `delete transaction 1`
- `log water 500 ml`
- `log sleep 7 hours`
- `log workout 30 minutes running`
- `log weight 72 kg`
- `log mood happy`
- `health summary`
- `show health logs`
- `delete health log 1`
- `chrome kholo`
- `aaj ka agenda`
- `suggestion do`
- `smart suggestions`
- `dismiss suggestion log_water`
- `integration status`
- `email test`
- `whatsapp status`
- `cloud sync now`
- `send mobile notification STAR message Check your tasks`
- `mobile notifications`
- `smart home status`
- `smart home turn on light.kitchen` then `confirm` or `cancel`
- `voice status`
- `voice language hindi`
- `voice language hinglish`
- `voice language english`
- `wake engine speech`
- `repeat`
- `dobara bolo`
- `stop`
- `sleep`
- `haan` or `kar de` for confirmation
- `nahi` or `mat kar` to cancel confirmation
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
- `security status`
- `security mode strict`
- `security mode normal`
- `check permission send whatsapp to Bajrangi message hello`
- `audit logs`
- `analytics summary`
- `usage stats`
- `top tools`
- `daily activity`
- `recent errors`
- `take screenshot`
- `analyze screen`
- `read screen`
- `analyze image screenshot_153709.png`
- `ocr image screenshot_153709.png`
- `scan qr qr.png`
- `compare images first.png and second.png`
- `email status`
- `read emails`
- `unread emails`
- `search emails invoice`
- `send email to friend@example.com subject Hello message Hi there`
- `send email to Bajrangi subject Hello message Hi there`
- `archive email 123`
- `delete email 123`
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
- `POST /calendar/events?title=Meeting&starts_at=2026-07-18T09:00:00` - create a calendar event.
- `POST /calendar/events/from-text?text=meeting tomorrow at 9 am` - create event from natural text.
- `GET /calendar/events` - list calendar events.
- `GET /calendar/upcoming` - upcoming calendar events.
- `GET /calendar/agenda?day=today` - today or tomorrow agenda.
- `POST /calendar/events/1/cancel` - cancel an event.
- `DELETE /calendar/events/1` - delete an event.
- `POST /contacts?name=Bajrangi&email=bajrangi@example.com&phone=919999999999` - create a contact.
- `GET /contacts` - list contacts.
- `GET /contacts?q=Bajrangi` - search contacts.
- `GET /contacts/1` - get one contact.
- `PATCH /contacts/1?email=new@example.com` - update a contact.
- `DELETE /contacts/1` - delete a contact.
- `GET /clipboard` - read clipboard text.
- `POST /clipboard?text=hello` - copy text to clipboard.
- `POST /clipboard/paste?text=hello` - paste text into the active app.
- `POST /snippets?name=greeting&content=hello` - save a snippet.
- `GET /snippets` - list snippets.
- `GET /snippets?q=greeting` - search snippets.
- `PATCH /snippets/1?content=updated` - update a snippet.
- `POST /snippets/1/copy` - copy snippet content to clipboard.
- `POST /snippets/1/paste` - paste snippet content into the active app.
- `DELETE /snippets/1` - delete a snippet.
- `POST /finance/transactions?kind=expense&amount=250&category=food` - save income or expense.
- `POST /finance/transactions/from-text?kind=expense&text=250 for food note lunch` - save transaction from text.
- `GET /finance/transactions` - list finance transactions.
- `GET /finance/summary` - current month income, expense, and balance.
- `GET /finance/categories` - current month expense categories.
- `DELETE /finance/transactions/1` - delete a transaction.
- `POST /health/logs?metric=water_ml&value=500&unit=ml` - save a health log.
- `POST /health/logs/from-text?kind=water&text=500 ml` - save a health log from text.
- `GET /health/logs` - list health logs.
- `GET /health/summary` - today health summary.
- `DELETE /health/logs/1` - delete a health log.
- `GET /suggestions` - smart suggestions generated from local usage and activity.
- `POST /suggestions/feedback?key=log_water&action=dismiss` - save suggestion feedback.
- `GET /integrations/status` - cloud/mobile/smart-home configuration status.
- `POST /integrations?name=home&kind=smart_home` - save a planned integration.
- `GET /integrations` - list saved integrations.
- `DELETE /integrations/1` - delete a saved integration.
- `POST /cloud/sync` - write a local cloud-sync snapshot.
- `GET /mobile/notifications` - list queued mobile notifications.
- `POST /mobile/notifications?title=STAR&body=Hello` - queue a mobile notification.
- `POST /mobile/notifications/1/read` - mark mobile notification read.
- `DELETE /mobile/notifications/1` - delete mobile notification.
- `GET /smart-home/status` - Home Assistant status if configured.
- `POST /smart-home/service?domain=light&service=turn_on&entity_id=light.kitchen` - call a Home Assistant service.
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
- `GET /security` - security and secret configuration status.
- `POST /security/mode?mode=strict` - set security mode.
- `GET /security/check?command=send whatsapp message` - classify command risk.
- `GET /security/audit` - security audit logs.
- `GET /analytics` - full analytics summary.
- `GET /analytics/commands` - command totals and success rate.
- `GET /analytics/daily` - daily command counts.
- `GET /analytics/tools` - tool usage breakdown.
- `GET /analytics/errors` - recent errors and warnings.
- `POST /vision/screenshot` - capture a screenshot.
- `GET /vision/analyze?path=image.png` - image metadata, brightness, and colors.
- `GET /vision/ocr?path=image.png` - OCR image text if Tesseract is installed.
- `GET /vision/qr?path=image.png` - scan QR code.
- `GET /vision/barcode?path=image.png` - scan barcode if decoder is available.
- `GET /vision/screen` - screenshot plus image analysis and OCR attempt.
- `GET /vision/compare?first=a.png&second=b.png` - compare two images.
- `GET /email/status` - email configuration status.
- `GET /email/inbox?limit=10&unread_only=false` - list inbox email summaries.
- `GET /email/search?q=invoice` - search emails.
- `POST /email/send?to=friend@example.com&subject=Hello&body=Hi` - send email.
- `POST /email/123/archive` - archive one email by IMAP id.
- `DELETE /email/123` - delete one email by IMAP id.
- `POST /confirm` - confirm a pending risky action.
- `POST /cancel` - cancel a pending risky action.

## Notes

- WhatsApp and Instagram automation depend on the current web UI and may need selector updates over time.
- Memory, history, commands, and logs are saved locally in `star.db`; this file is ignored by git because it can contain personal data.
- If `star_memory.json` exists from an older version, STAR imports it into SQLite on startup.
- PDF reading needs `pypdf` or `PyPDF2`; OCR will need an OCR engine in a later batch.
- OCR uses `pytesseract`, but Windows also needs the Tesseract OCR engine installed and available on PATH.
- Email defaults to Gmail IMAP/SMTP. For Gmail, enable IMAP and use an app password in `.env`; never paste email passwords into chat.
- Email send can use a saved contact name if the contact has an email address.
- Clipboard paste actions type into the currently active app, so STAR asks for confirmation in normal/strict security modes.
- Health logs are personal tracking only, not medical advice.
- Multilingual support uses local Hinglish/Hindi mappings first; if Groq is configured, STAR can normalize broader language commands before routing.
- Smart-home control uses Home Assistant env keys `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN`; device actions require confirmation.
- Cloud sync writes local snapshots to `CLOUD_SYNC_DIR` or `cloud_sync/`; mobile support exposes a notification queue for a future app/client.
- WhatsApp send/search requires WhatsApp Web login and may need selector updates if WhatsApp changes its UI.
- Security modes: `relaxed` confirms only highest-risk actions, `normal` confirms messaging/download/automation/power/git write actions, and `strict` confirms every recognized risky action.
- Keep `.env` private.
