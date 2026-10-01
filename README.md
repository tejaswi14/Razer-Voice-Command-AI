# Razer Voice Command AI — Full-Stack Project

A professional local voice-command chatbot with a frontend, backend and lightweight SQLite database.

## What it does

Say commands such as:

- **Hey Razer, open Google**
- **Hey Razer, open YouTube**
- **Open Gmail**
- **Open ChatGPT**
- **Open Instagram**
- **Open WhatsApp**
- **Open GitHub**
- **Stop**

The browser recognizes the voice, sends the text to the FastAPI backend, the backend matches the command against the SQLite command library, returns the correct URL and response, and the frontend opens the website in a new tab and speaks the response.

## Architecture

```text
Microphone
   ↓
Browser Web Speech API
   ↓
Professional HTML/CSS/JS frontend
   ↓ HTTP JSON
FastAPI backend
   ↓
SQLite command library + history
   ↓
Response + URL
   ↓
Browser opens website + Speech Synthesis speaks response
```

## Run on Windows

1. Install Python 3.10+.
2. Open this project folder in Command Prompt.
3. Run `run.bat`.
4. Open **http://127.0.0.1:8000** in Chrome or Edge.
5. Allow microphone permission.
6. Click **Start listening** and say a command.

## Run on macOS/Linux

```bash
chmod +x run.sh
./run.sh
```

Then open http://127.0.0.1:8000.

## Database

No separate database server is required. The app automatically creates:

`data/assistant.db`

It contains:

- `commands` — website/action definitions and URLs.
- `command_history` — every recognized command and the assistant response.

You can add a new command through the backend API or directly in SQLite.

## Add a command through API

POST `/api/commands` with JSON:

```json
{
  "name": "linkedin",
  "trigger_text": "open linkedin",
  "url": "https://www.linkedin.com",
  "description": "Open LinkedIn"
}
```

## Important

The voice recognition is browser-based, so Chrome/Edge is recommended. The backend does not need Whisper, a separate model download, or a database server. SQLite is built into Python.
