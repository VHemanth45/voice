"""Minimal Pipecat voice assistant.

Pipeline: browser mic → Silero VAD → Whisper STT → Ollama LLM → Cartesia TTS → browser speaker.

Run:  uv run bot.py
Open: http://localhost:7860/client
"""

import sys
from loguru import logger
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams
from pipecat.pipeline.runner import WorkerRunner
from config import load_config
import pipeline
import handlers

config = load_config()
logger.remove()
logger.add(sys.stderr, level=config.log_level, format="{time:HH:mm:ss.SSS} | {level:<7} | {message}")

async def run_bot(transport, runner_args: RunnerArguments):
    worker, context = pipeline.create_pipeline(config, transport)
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        await handlers.on_client_connected(transport, client, worker, context)
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await handlers.on_client_disconnected(transport, client, worker)
    @worker.event_handler("on_error")
    async def on_pipeline_error(error):
        await handlers.on_pipeline_error(worker, error)
    await WorkerRunner(handle_sigint=False).run(worker)

async def bot(runner_args: RunnerArguments):
    transport = await create_transport(runner_args, {"webrtc": lambda: TransportParams(audio_in_enabled=True, audio_out_enabled=True)})
    await run_bot(transport, runner_args)

if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
