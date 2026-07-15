# Voice Assistant — Production Hardening & Modular Refactor: Issues

> Source spec: [spec.md](spec.md)

---

# 01 — Config & Prompts Module with Fail-Fast Validation

**What to build:** A `config.py` module that loads every environment variable into a single typed, frozen dataclass and fails immediately at startup with a human-readable error if any required value is missing or any value is the wrong type. A `prompts.py` module that holds the system prompt (overridable via `SYSTEM_PROMPT` env var) and the greeting message — fixing the current bug where the greeting injects a duplicate system-role message instead of a user-role message. A `.env.example` file with safe placeholder values for every supported variable. `bot.py` updated to import config and prompts instead of calling `os.getenv` directly. Bot still runs end-to-end identically.

**Blocked by:** None — can start immediately.

**Status:** completed

- [x] `config.py` exports a frozen dataclass with typed fields for all env vars (CARTESIA_API_KEY, CARTESIA_VOICE_ID, OLLAMA_BASE_URL, OLLAMA_MODEL, WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, VAD_STOP_SECS, VAD_START_SECS, LOG_LEVEL)
- [x] Missing `CARTESIA_API_KEY` raises `SystemExit` with a message pointing to `.env.example`
- [x] Invalid float for `VAD_STOP_SECS` / `VAD_START_SECS` raises `SystemExit` with a descriptive message
- [x] Invalid `WHISPER_MODEL` (not in `tiny`, `base`, `small`, `medium`, `large-v3`) raises `SystemExit`
- [x] `prompts.py` exports `SYSTEM_PROMPT` (overridable via env var) and `GREETING_MESSAGE` (user-role, not system-role)
- [x] `.env.example` created with placeholder values for every env var — no real keys
- [x] `bot.py` imports from `config` and `prompts` — zero remaining `os.getenv` calls in `bot.py`
- [x] `uv run bot.py` still works end-to-end (mic → speaker loop)

---

# 02 — Services Module with Error-Handled Factories

**What to build:** A `services.py` module with factory functions that create each Pipecat service (WhisperSTTService, OLLamaLLMService, CartesiaTTSService) from the config dataclass. Each factory wraps initialization in try/except and raises a clear, actionable error if a service fails to start. When Ollama isn't running, the developer sees "Failed to initialize Ollama LLM: connection refused to http://localhost:11434/v1" instead of a raw traceback.

**Blocked by:** 01 — Config & Prompts Module

**Status:** completed

- [x] `services.py` exports factory functions: `create_stt(config)`, `create_llm(config)`, `create_tts(config)`
- [x] Each factory accepts the config dataclass (not raw strings)
- [x] Each factory wraps service init in try/except and re-raises with a human-readable message naming the service and the cause
- [x] `bot.py` calls these factories instead of inline service construction
- [x] `uv run bot.py` with Ollama stopped produces a clear error message (not a stack trace)

---

# 03 — Logging Configuration

**What to build:** Structured loguru configuration at startup, controlled by the `LOG_LEVEL` env var from the config dataclass. The default loguru handler is replaced with a level-filtered stderr handler. All modules use loguru consistently. A developer can run with `LOG_LEVEL=DEBUG` for verbose output or `LOG_LEVEL=WARNING` for quiet production.

**Blocked by:** 01 — Config & Prompts Module

**Status:** completed

- [x] Loguru default handler removed at startup
- [x] New stderr handler added with level from `config.log_level` (default: `INFO`)
- [x] `LOG_LEVEL` env var documented in `.env.example`
- [x] Running with `LOG_LEVEL=DEBUG` produces verbose Pipecat/service output
- [x] Running with `LOG_LEVEL=WARNING` suppresses info-level chatter

---

# 04 — Handlers Module with Graceful Shutdown

**What to build:** A `handlers.py` module containing standalone event handler functions for transport and worker lifecycle events. The `on_client_disconnected` handler uses `asyncio.wait_for` with a 5-second timeout to prevent the process from hanging on disconnect. The `on_client_connected` handler uses the fixed user-role greeting from the prompts module. An `on_pipeline_error` handler logs errors instead of crashing silently.

**Blocked by:** 01 — Config & Prompts Module

**Status:** ready-for-agent

- [ ] `handlers.py` exports handler functions: `on_client_connected`, `on_client_disconnected`, `on_pipeline_error`
- [ ] `on_client_disconnected` wraps `worker.cancel()` in `asyncio.wait_for(timeout=5.0)` and logs a warning on timeout
- [ ] `on_client_connected` injects the greeting as a user-role message (from prompts module), not a duplicate system message
- [ ] `on_pipeline_error` logs the error with context
- [ ] Handler functions are pure (take worker/context/transport as args, no module-level globals)

---

# 05 — Pipeline Module Assembly

**What to build:** A `pipeline.py` module with a factory function that takes a config dataclass and transport, creates all services (via the services module), assembles the Pipecat Pipeline processor chain (transport input → STT → user aggregator → LLM → TTS → transport output → assistant aggregator), and returns a configured PipelineWorker with metrics enabled.

**Blocked by:** 01 — Config & Prompts Module, 02 — Services Module

**Status:** ready-for-agent

- [ ] `pipeline.py` exports a factory function `create_pipeline(config, transport)` that returns `(PipelineWorker, LLMContext)`
- [ ] Pipeline processor chain matches the correct ordering: transport.input → STT → user_aggregator → LLM → TTS → transport.output → assistant_aggregator
- [ ] VAD parameters (stop_secs, start_secs) sourced from config dataclass
- [ ] LLMContext initialized with system prompt from prompts module
- [ ] PipelineWorker created with `enable_metrics=True` and `enable_usage_metrics=True`
- [ ] No `os.getenv` calls — everything comes from config

---

# 06 — Bot Entrypoint Rewrite

**What to build:** Rewrite `bot.py` as a thin entrypoint shell (~30 lines) that imports config, calls the pipeline factory, registers handlers from the handlers module, and runs. This completes the full module split. The external interface (`uv run bot.py`, connect at `http://localhost:7860/client`) remains identical.

**Blocked by:** 04 — Handlers Module, 05 — Pipeline Module

**Status:** ready-for-agent

- [ ] `bot.py` is under 40 lines
- [ ] `bot.py` imports from `config`, `pipeline`, and `handlers` — no inline service/pipeline construction
- [ ] `bot.py` registers transport event handlers from the handlers module
- [ ] `uv run bot.py` works end-to-end identically to before the refactor
- [ ] Connecting via browser at `http://localhost:7860/client` produces a greeting and two-way voice conversation

---

# 07 — Context Summarization

**What to build:** Wire Pipecat's built-in `LLMContextSummarizer` into the pipeline so that long conversations automatically compress older messages when the context window approaches its limit. Prevents the bot from losing coherence or crashing on extended conversations with Gemma 3 4B's 8K token window.

**Blocked by:** 06 — Bot Entrypoint Rewrite

**Status:** ready-for-agent

- [ ] `LLMContextSummarizer` wired into the pipeline's aggregator setup
- [ ] Auto-summarization triggers when context exceeds a configurable token threshold (default: 4096 tokens)
- [ ] `MAX_CONTEXT_TOKENS` env var added to config dataclass and `.env.example`
- [ ] After summarization, the system prompt is preserved and recent turns remain uncompressed
- [ ] A 20+ turn conversation does not crash or produce incoherent responses

---

# 08 — Idle Detection and Auto-Disconnect

**What to build:** Wire Pipecat's `IdleFrameProcessor` into the pipeline to handle user inactivity. After a configurable silence period, the bot prompts the user ("Are you still there?"). After a longer silence period, it says goodbye and disconnects. Both thresholds are configurable via env vars.

**Blocked by:** 06 — Bot Entrypoint Rewrite

**Status:** ready-for-agent

- [ ] `IdleFrameProcessor` added to the pipeline
- [ ] After `IDLE_PROMPT_SECS` (default: 15) of silence, bot speaks a configurable prompt
- [ ] After `IDLE_DISCONNECT_SECS` (default: 60) of silence, bot speaks a farewell and disconnects
- [ ] Both thresholds added to config dataclass and `.env.example`
- [ ] An active conversation resets the idle timers

---

# 09 — Metrics Logging

**What to build:** Consume the pipeline metrics that are already being collected (`enable_metrics=True`) and log them so they're actually observable. Register a handler on the PipelineWorker that logs `MetricsFrame` data (TTFB, processing latencies) at DEBUG level. A developer running with `LOG_LEVEL=DEBUG` can now see per-turn latency breakdowns.

**Blocked by:** 03 — Logging Configuration, 06 — Bot Entrypoint Rewrite

**Status:** ready-for-agent

- [ ] PipelineWorker `on_metrics` or equivalent handler registered to capture MetricsFrame data
- [ ] Metrics logged at DEBUG level with service name and latency values
- [ ] Running with `LOG_LEVEL=DEBUG` shows per-turn TTFB for STT, LLM, and TTS
- [ ] Running with `LOG_LEVEL=INFO` (default) does not show metrics noise

---

# 10 — README Rewrite

**What to build:** Rewrite the README to accurately reflect the refactored codebase. Fix all documented defaults to match the code, add every env var to the Env Knobs table (including new ones like `LOG_LEVEL`, `MAX_CONTEXT_TOKENS`, `IDLE_PROMPT_SECS`, `IDLE_DISCONNECT_SECS`, `SYSTEM_PROMPT`), update the file tree to show the new module structure, and add a troubleshooting section for common issues.

**Blocked by:** 06 — Bot Entrypoint Rewrite

**Status:** ready-for-agent

- [ ] Env Knobs table lists every supported env var with correct defaults
- [ ] `WHISPER_MODEL` default documented as `small` (matching code, not the old `tiny`)
- [ ] `WHISPER_COMPUTE_TYPE` included in the table
- [ ] New env vars (`LOG_LEVEL`, `SYSTEM_PROMPT`, `MAX_CONTEXT_TOKENS`, `IDLE_PROMPT_SECS`, `IDLE_DISCONNECT_SECS`) documented
- [ ] File tree updated to show `config.py`, `prompts.py`, `services.py`, `pipeline.py`, `handlers.py`
- [ ] Troubleshooting section covers: Ollama not running, mic permissions denied, CUDA not available, Cartesia key invalid
- [ ] `.env.example` is in sync with all documented env vars

---

# 11 — Test Infrastructure and Config Tests

**What to build:** Bootstrap the test infrastructure with pytest and write tests for the config module (the primary testing seam). Tests verify external behavior: missing required keys raise SystemExit, invalid types raise SystemExit, valid env produces a correctly typed dataclass, defaults are applied correctly.

**Blocked by:** 01 — Config & Prompts Module

**Status:** completed

- [x] `pytest` added as a dev dependency in `pyproject.toml`
- [x] `tests/` directory created with `conftest.py` containing env-patching fixtures
- [x] Test: missing `CARTESIA_API_KEY` → `SystemExit`
- [x] Test: `VAD_STOP_SECS=notanumber` → `SystemExit`
- [x] Test: `WHISPER_MODEL=nonexistent` → `SystemExit`
- [x] Test: all valid env vars → correctly typed config dataclass with expected values
- [x] Test: only required vars set → optional vars get documented defaults
- [x] `uv run pytest` passes all tests
