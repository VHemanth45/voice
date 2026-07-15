"""Tests for the pipeline module."""

from unittest.mock import MagicMock, patch

import pytest

from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver
from pipecat.pipeline.worker import PipelineParams

import pipeline


@pytest.fixture
def base_config():
    config = MagicMock()
    config.vad_stop_secs = 0.3
    config.vad_start_secs = 0.2
    config.whisper_model = "small"
    config.whisper_device = "auto"
    config.whisper_compute_type = "int8"
    config.ollama_base_url = "http://localhost:11434/v1"
    config.ollama_model = "gemma3:4b"
    config.cartesia_api_key = "test_key"
    config.cartesia_voice_id = "test_voice_id"
    config.max_context_tokens = 4096
    config.idle_prompt_secs = 15.0
    config.idle_disconnect_secs = 60.0
    return config


def test_create_pipeline_attaches_metrics_observer(base_config):
    """A MetricsLogObserver should be attached to the PipelineWorker."""
    transport = MagicMock()

    with (
        patch.object(pipeline, "services") as mock_services,
        patch.object(pipeline, "Pipeline") as mock_pipeline_class,
        patch.object(pipeline, "PipelineWorker") as mock_worker_class,
    ):
        mock_services.create_stt.return_value = MagicMock()
        mock_services.create_llm.return_value = MagicMock()
        mock_services.create_tts.return_value = MagicMock()
        mock_pipeline_class.return_value = MagicMock()
        mock_worker = MagicMock()
        mock_worker_class.return_value = mock_worker

        pipeline.create_pipeline(base_config, transport)

        mock_worker_class.assert_called_once()
        _, kwargs = mock_worker_class.call_args

        assert "observers" in kwargs
        assert len(kwargs["observers"]) == 1
        assert isinstance(kwargs["observers"][0], MetricsLogObserver)

        params: PipelineParams = kwargs["params"]
        assert params.enable_metrics is True
        assert params.enable_usage_metrics is True
