"""Shared pytest fixtures for the voice assistant test suite."""

import pytest

# All configuration keys managed by config.load_config().
_CONFIG_KEYS = [
    "CARTESIA_API_KEY",
    "CARTESIA_VOICE_ID",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "WHISPER_MODEL",
    "WHISPER_DEVICE",
    "WHISPER_COMPUTE_TYPE",
    "VAD_STOP_SECS",
    "VAD_START_SECS",
    "LOG_LEVEL",
]

# Default values mirrored from config.load_config().
_DEFAULTS = {
    "CARTESIA_API_KEY": "test_api_key",
    "CARTESIA_VOICE_ID": "test_voice_id",
    "OLLAMA_BASE_URL": "http://localhost:11434/v1",
    "OLLAMA_MODEL": "gemma3:4b",
    "WHISPER_MODEL": "small",
    "WHISPER_DEVICE": "auto",
    "WHISPER_COMPUTE_TYPE": "int8",
    "VAD_STOP_SECS": "0.3",
    "VAD_START_SECS": "0.2",
    "LOG_LEVEL": "INFO",
}


@pytest.fixture
def env(monkeypatch):
    """Apply a clean, patched environment for config tests.

    Usage::

        def test_something(env):
            env(CARTESIA_API_KEY=None)
            ...

    Passing ``None`` as a value deletes the variable. All other values are
    coerced to strings before being set.
    """

    def _apply_env(**overrides):
        # Remove any pre-existing values so a real .env file cannot leak.
        for key in _CONFIG_KEYS:
            monkeypatch.delenv(key, raising=False)

        env_vars = {**_DEFAULTS, **overrides}
        for key, value in env_vars.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, str(value))
        return env_vars

    return _apply_env
