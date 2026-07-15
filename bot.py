"""Minimal Pipecat voice assistant.

Pipeline: browser mic → Silero VAD → Whisper STT → Ollama LLM → Cartesia TTS → browser speaker.

Run:  uv run bot.py
Open: http://localhost:7860/client
"""

import sys

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.pipeline.runner import WorkerRunner
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams

# Import new config, prompts, services, and handlers modules
from config import load_config
import prompts
import services
import handlers

config = load_config()

logger.remove()
logger.add(sys.stderr, level=config.log_level, format="{time:HH:mm:ss.SSS} | {level:<7} | {message}")

MESSAGES = [{"role": "system", "content": prompts.SYSTEM_PROMPT}]


# ── Bot logic ─────────────────────────────────────────────

async def run_bot(transport, runner_args: RunnerArguments):
    """Wire up the full pipeline and run it."""

    # --- Services ---
    stt = services.create_stt(config)
    llm = services.create_llm(config)
    tts = services.create_tts(config)

    # --- Context & VAD turn-detection ---
    context = LLMContext(MESSAGES)

    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(
                    stop_secs=config.vad_stop_secs,
                    start_secs=config.vad_start_secs,
                ),
            ),
        ),
    )

    # --- Pipeline ---
    pipeline = Pipeline([
        transport.input(),       # browser mic audio
        stt,                     # Whisper STT
        user_aggregator,         # accumulate user turn → context
        llm,                     # Ollama LLM
        tts,                     # Cartesia TTS
        transport.output(),      # browser speaker audio
        assistant_aggregator,    # accumulate assistant turn → context
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    # --- Events ---
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await handlers.on_client_connected(transport, client, worker, context)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await handlers.on_client_disconnected(transport, client, worker)

    @worker.event_handler("on_error")
    async def on_pipeline_error(error):
        await handlers.on_pipeline_error(worker, error)

    # --- Run ---
    runner = WorkerRunner(handle_sigint=False)
    await runner.run(worker)


# ── Entrypoint ────────────────────────────────────────────

transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
}


async def bot(runner_args: RunnerArguments):
    """Main bot entry point — called by the Pipecat runner."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
