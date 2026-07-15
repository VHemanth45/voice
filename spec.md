# Spec: Voice Assistant — Production Hardening & Modular Refactor

## Problem Statement

The voice assistant is a working MVP that pipes browser audio through a Silero VAD → Whisper STT → Ollama LLM → Cartesia TTS pipeline using Pipecat. However, it has critical security, reliability, and maintainability problems that prevent it from being used beyond a local demo:

- A real API key is committed to git history and exposed to anyone who clones the repo.
- Missing environment variables cause silent runtime failures instead of clear startup errors.
- The README references files that don't exist (`.env.example`) and documents defaults that don't match the code.
- The entire application lives in a single 140-line file with no separation of concerns, making it difficult to extend with new features (function calling, idle detection, context management).
- There is no error handling, no graceful shutdown, no context window management, no logging configuration, and no observability — the bot will crash on any transient failure and silently degrade on long conversations.

## Solution

Refactor the monolithic `bot.py` into a modular, production-hardened voice assistant with:

1. **Fail-fast configuration** — a dedicated config module that validates all required environment variables at startup and raises clear errors for missing or invalid values.
2. **Modular architecture** — separate modules for config, services, pipeline assembly, event handlers, and prompts — each with a single responsibility.
3. **Runtime resilience** — error handling on service initialization, graceful shutdown with timeouts, context window management via Pipecat's built-in summarizer, and proper logging configuration.
4. **Documentation accuracy** — a corrected README with accurate defaults, a working `.env.example`, troubleshooting guidance, and a complete env knobs table.
5. **Production features** — idle detection, metrics logging, and interruption handling using Pipecat processors already available in the dependency tree.

## User Stories

1. As a developer cloning this repo, I want a `.env.example` file with placeholder values, so that I know exactly which environment variables to set without reading through source code.
2. As a developer, I want the bot to crash immediately with a clear error if `CARTESIA_API_KEY` is missing, so that I don't waste time debugging cryptic runtime TTS failures.
3. As a developer, I want the bot to validate all environment variable types at startup (e.g., `VAD_STOP_SECS` must be a valid float), so that typos in `.env` are caught before the pipeline starts.
4. As a developer, I want the README's documented defaults to exactly match the code's actual defaults, so that I can trust the documentation when tuning latency.
5. As a developer, I want the README to list every supported environment variable including `WHISPER_COMPUTE_TYPE` and `LOG_LEVEL`, so that I have a complete reference.
6. As a developer, I want a troubleshooting section in the README, so that I can self-diagnose common issues (Ollama not running, mic permissions, CUDA errors).
7. As a developer, I want the codebase split into focused modules (config, services, pipeline, handlers, prompts), so that I can modify one concern without reading the entire bot.
8. As a developer, I want the system prompt to be configurable via an environment variable or external file, so that I can change the bot's personality without editing Python code.
9. As a user having a long conversation, I want the bot to automatically summarize older context, so that it doesn't lose coherence or crash when the context window fills up.
10. As a user, I want the bot to greet me when I connect, so that I know the connection is working and I can start talking.
11. As a user, I want the bot to handle my interruptions (barge-in) gracefully, so that it stops speaking and listens to me when I start talking.
12. As a user, I want the bot to prompt me if I've been silent for too long, so that I know it's still listening and haven't lost the connection.
13. As a user, I want the bot to say goodbye and disconnect after extended inactivity, so that resources aren't wasted on abandoned sessions.
14. As a developer, I want structured logging with configurable log levels, so that I can debug issues in development without noise in production.
15. As a developer, I want the bot to log per-turn latency metrics (TTFB for STT, LLM, TTS), so that I can identify performance bottlenecks.
16. As a developer, I want the bot to shut down gracefully when a client disconnects (with a timeout), so that resources are always cleaned up and the process doesn't hang.
17. As a developer, I want the bot to catch and log service initialization errors (Ollama unreachable, Whisper model download fails), so that I get actionable error messages instead of stack traces.
18. As a developer, I want the pipeline event handlers to be in a separate module, so that I can add new behaviors (e.g., function calling, memory) without modifying the pipeline assembly code.
19. As a security-conscious developer, I want the git history scrubbed of any committed secrets, so that the repo is safe to share publicly.
20. As a developer, I want the greeting message to be a user-role context injection (not a duplicate system message), so that the LLM context doesn't accumulate stale system prompts on reconnects.
21. As a developer, I want the config module to expose a single typed dataclass, so that all downstream code gets IDE autocomplete and type checking instead of raw `os.getenv` calls scattered everywhere.
22. As a developer, I want metrics enabled in the pipeline to actually be logged somewhere, so that enabling `enable_metrics=True` produces observable output.

## Implementation Decisions

### Module Architecture

The single `bot.py` will be split into six modules following separation of concerns:

- **Config module** — Loads and validates all environment variables at import time. Exports a frozen dataclass containing every config value with proper types (str, float, int). Raises `SystemExit` with a human-readable message if any required variable is missing or any value fails type coercion. This is the only module that touches `os.getenv`.

- **Prompts module** — Contains the system prompt as a constant with env-override support (`SYSTEM_PROMPT` env var). Also contains the greeting injection message. Separates prompt engineering from pipeline plumbing.

- **Services module** — Factory functions that instantiate Pipecat services (WhisperSTTService, OLLamaLLMService, CartesiaTTSService) from the config dataclass. Each factory wraps initialization in try/except and raises clear errors if a service fails to initialize (e.g., "Failed to initialize Whisper STT: model 'xyz' not found").

- **Pipeline module** — Assembles the Pipecat Pipeline from services, aggregators, and processors. This is where context summarization, idle detection, and metrics processors are wired in. Takes a config + transport, returns a configured PipelineWorker.

- **Handlers module** — Event handler functions for transport and worker events (`on_client_connected`, `on_client_disconnected`, `on_pipeline_error`, `on_idle_timeout`). Kept separate so new behaviors can be added without touching pipeline assembly.

- **Bot module (entrypoint)** — Thin shell that imports config, calls the pipeline factory, registers handlers, and runs. Remains the `uv run bot.py` entrypoint.

### Configuration Validation

The config dataclass will validate at construction time:
- `CARTESIA_API_KEY` is present and non-empty (required)
- `VAD_STOP_SECS`, `VAD_START_SECS` are valid positive floats
- `WHISPER_MODEL` is one of a known set (`tiny`, `base`, `small`, `medium`, `large-v3`)
- `WHISPER_DEVICE` is one of `auto`, `cpu`, `cuda`
- `LOG_LEVEL` is a valid Python log level string

### Context Window Management

Use Pipecat's built-in `LLMContextSummarizer` with the `LLMContextAggregatorPair`. Configure auto-summarization to trigger when context exceeds a configurable token threshold (default: 4096 tokens, suitable for Gemma 3 4B's 8K window). The summarizer will compress older messages into a summary while preserving recent turns.

### Idle Detection

Use Pipecat's `IdleFrameProcessor` to detect user inactivity:
- After 15 seconds of silence: push a prompt ("Are you still there?")
- After 60 seconds of silence: push a farewell message and disconnect

Both thresholds will be configurable via env vars (`IDLE_PROMPT_SECS`, `IDLE_DISCONNECT_SECS`).

### Graceful Shutdown

The `on_client_disconnected` handler will use `asyncio.wait_for(worker.cancel(), timeout=5.0)` to prevent indefinite hangs. On timeout, it logs a warning and forces shutdown.

### Greeting Fix

Replace the current duplicate system message injection with a user-role message:
```python
context.add_message({
    "role": "user",
    "content": "[The user just connected. Greet them briefly and introduce yourself.]"
})
```
This prevents context pollution from repeated system messages on reconnect.

### Logging

Configure loguru at startup with:
- Level from `LOG_LEVEL` env var (default: `INFO`)
- Remove default handler, add stderr handler with level filter
- Structured format for production readability

### Metrics Logging

Register a `on_metrics` handler on the PipelineWorker that logs `MetricsFrame` data at DEBUG level. This makes the existing `enable_metrics=True` flag actually produce visible output.

## Testing Decisions

### What Makes a Good Test

Tests should verify **external behavior at module boundaries**, not internal implementation details. A good test for this project:
- Calls a module's public function with controlled inputs
- Asserts the output or side-effect (error raised, correct type returned)
- Does NOT mock Pipecat internals or test framework behavior
- Does NOT require running services (Ollama, Cartesia, Whisper)

### Modules Under Test

1. **Config module** (primary seam):
   - Test that missing `CARTESIA_API_KEY` raises `SystemExit`
   - Test that invalid float values for `VAD_STOP_SECS` raise `SystemExit`
   - Test that valid env produces a correctly typed config dataclass
   - Test that defaults are applied when optional vars are absent
   - Test that `WHISPER_MODEL` rejects unknown model names

2. **Pipeline module** (supporting seam):
   - Test that the factory returns a PipelineWorker
   - Test that the pipeline processor chain contains the expected processor types in the correct order (STT → aggregator → LLM → TTS)
   - Use a mock transport to avoid WebRTC dependencies

### Prior Art

No existing tests in this codebase. Pipecat itself uses pytest. The test infrastructure will be bootstrapped with:
- `pytest` added to dev dependencies in `pyproject.toml`
- A `tests/` directory with `conftest.py` for shared fixtures (env var patching, mock transport)

## Out of Scope

- **Function calling / tool use** — While identified as a valuable enhancement, adding Ollama function calling requires designing a tool registry, handler dispatch, and result formatting. This is a separate feature spec.
- **Multi-client support** — The current architecture supports one client at a time. Supporting concurrent sessions requires pipeline-per-client isolation, which is a separate architectural change.
- **Alternative transports** — Adding WebSocket or Daily.co transport support is a separate feature.
- **Health check HTTP endpoint** — Useful but requires adding an HTTP server alongside the WebRTC transport, which is out of scope for this refactor.
- **Persistent memory across sessions** — Integrating long-term memory (e.g., hindsight-pipecat) is a separate feature.
- **Git history scrubbing** — While critical, this is an operational task the developer must perform manually (using `git filter-repo` or BFG Repo Cleaner). The spec covers preventing future leaks via `.env.example` and fail-fast validation, but the actual history rewrite is a one-time manual action.
- **CI/CD pipeline** — No GitHub Actions or automated deployment is included in this scope.

## Further Notes

- **Dependency impact**: No new pip dependencies are needed. All Pipecat processors used (IdleFrameProcessor, LLMContextSummarizer, MetricsFrame) are already included in the installed `pipecat-ai[silero,whisper,cartesia,webrtc,runner]` package. Only `pytest` is added as a dev dependency.

- **Breaking changes**: The module split changes the internal structure but the external interface (`uv run bot.py`, connect at `http://localhost:7860/client`) remains identical. No user-facing breaking changes.

- **Migration path**: Since there are only 2 commits and no downstream consumers, there is no migration concern. The refactor can be done as a single commit on `main`.

- **Python version**: The project pins `requires-python = ">=3.14"` which is extremely aggressive (Python 3.14 is in alpha as of mid-2026). Consider relaxing to `>=3.10` since nothing in the codebase uses 3.14-specific features. This would be a minor `pyproject.toml` change but dramatically improves developer accessibility.
