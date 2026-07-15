"""Tests for the config module — the primary testing seam."""

import pytest

from config import Config, load_config


def test_missing_cartesia_api_key_raises_system_exit(env):
    env(CARTESIA_API_KEY=None)
    with pytest.raises(SystemExit):
        load_config()


def test_invalid_vad_stop_secs_raises_system_exit(env):
    env(VAD_STOP_SECS="notanumber")
    with pytest.raises(SystemExit):
        load_config()


def test_invalid_whisper_model_raises_system_exit(env):
    env(WHISPER_MODEL="nonexistent")
    with pytest.raises(SystemExit):
        load_config()


def test_all_valid_env_vars_produces_typed_config(env):
    env(
        CARTESIA_API_KEY="custom_api_key",
        CARTESIA_VOICE_ID="custom_voice_id",
        OLLAMA_BASE_URL="http://custom-ollama:11434/v1",
        OLLAMA_MODEL="custom_model",
        WHISPER_MODEL="base",
        WHISPER_DEVICE="cpu",
        WHISPER_COMPUTE_TYPE="float16",
        VAD_STOP_SECS="0.5",
        VAD_START_SECS="0.1",
        LOG_LEVEL="DEBUG",
    )

    config = load_config()

    assert isinstance(config, Config)
    assert config.cartesia_api_key == "custom_api_key"
    assert config.cartesia_voice_id == "custom_voice_id"
    assert config.ollama_base_url == "http://custom-ollama:11434/v1"
    assert config.ollama_model == "custom_model"
    assert config.whisper_model == "base"
    assert config.whisper_device == "cpu"
    assert config.whisper_compute_type == "float16"
    assert config.vad_stop_secs == 0.5
    assert config.vad_start_secs == 0.1
    assert config.log_level == "DEBUG"


def test_only_required_vars_applies_documented_defaults(env):
    env(
        CARTESIA_API_KEY="only_required_key",
        CARTESIA_VOICE_ID=None,
        OLLAMA_BASE_URL=None,
        OLLAMA_MODEL=None,
        WHISPER_MODEL=None,
        WHISPER_DEVICE=None,
        WHISPER_COMPUTE_TYPE=None,
        VAD_STOP_SECS=None,
        VAD_START_SECS=None,
        LOG_LEVEL=None,
    )

    config = load_config()

    assert config.cartesia_api_key == "only_required_key"
    assert config.cartesia_voice_id == "71a7ad14-091c-4e8e-a314-022ece01c121"
    assert config.ollama_base_url == "http://localhost:11434/v1"
    assert config.ollama_model == "gemma3:4b"
    assert config.whisper_model == "small"
    assert config.whisper_device == "auto"
    assert config.whisper_compute_type == "int8"
    assert config.vad_stop_secs == 0.3
    assert config.vad_start_secs == 0.2
    assert config.log_level == "INFO"
