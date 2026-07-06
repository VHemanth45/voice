# Voice Assistant — Pipecat MVP

Minimal mic-to-speaker voice loop running entirely in the browser.

```
browser mic → Silero VAD → Whisper STT → Ollama LLM → Cartesia TTS → browser speaker
```

## How to Run This Bot

Follow these steps to run the local voice assistant.

### 1. Prerequisites
Ensure you have the following installed on your machine:
- **Python 3.10+** (managed via `uv`)
- **uv** (fast Python package installer)
- **Ollama** (for local LLM inference)

### 2. Setup Environment Variables
Copy the `.env.example` to a `.env` file and add your keys:
```bash
cp .env.example .env
```
*Note: You must edit `.env` and add your `CARTESIA_API_KEY`.*

### 3. Start the Local LLM
Start Ollama and pull the Gemma 3 model in a separate terminal:
```bash
ollama serve
ollama pull gemma3:4b
```

### 4. Install Dependencies
Install all project requirements using `uv`:
```bash
uv sync
```

### 5. Run the Bot
Execute the main script:
```bash
uv run bot.py
```

### 6. Connect via Browser
1. Open your web browser and go to: **http://localhost:7860/client**
2. Allow microphone access when prompted.
3. Click "Connect" (or wait for it to connect).
4. Start talking to the bot!

## Env Knobs

| Variable          | Default                                  | What it controls              |
|-------------------|------------------------------------------|-------------------------------|
| `CARTESIA_API_KEY`| *(required)*                             | Cartesia TTS auth             |
| `CARTESIA_VOICE_ID`| `71a7ad14-091c-4e8e-a314-022ece01c121` | Cartesia voice                |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1`              | Ollama server                 |
| `OLLAMA_MODEL`    | `gemma3:4b`                              | Ollama model                  |
| `WHISPER_MODEL`   | `tiny`                                   | Faster-Whisper model size     |
| `WHISPER_DEVICE`  | `auto`                                   | `cpu` / `cuda` / `auto`      |
| `VAD_STOP_SECS`   | `0.3`                                    | Silence before turn ends      |
| `VAD_START_SECS`  | `0.2`                                    | Speech before turn starts     |

## Latency Tuning (3 knobs that matter)

1. **Whisper size** — `tiny` is fastest (~100ms), `small` is more accurate (~300ms)
2. **Ollama model** — `gemma3:4b` is the sweet spot; drop to `gemma3:1b` if slow
3. **VAD thresholds** — lower `VAD_STOP_SECS` = faster response, more false triggers

## Files

```
bot.py          # single entrypoint — the entire pipeline
.env.example    # env template
pyproject.toml  # deps
README.md       # this file
```
