import asyncio

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.idle_frame_processor import IdleFrameProcessor

import prompts
import services


def create_pipeline(config, transport):
    stt = services.create_stt(config)
    llm = services.create_llm(config)
    tts = services.create_tts(config)

    context = LLMContext([{"role": "system", "content": prompts.SYSTEM_PROMPT}])

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
        # Configure summarization
        summarizer_params={
            "token_limit": config.max_context_tokens,
        },
    )

    async def on_idle_prompt(processor):
        logger.info("No activity detected — prompting user")
        context.add_message({"role": "user", "content": prompts.IDLE_PROMPT_MESSAGE})
        await processor.push_frame(LLMRunFrame())

    async def on_idle_disconnect(processor):
        logger.info("No activity detected for too long — saying goodbye")
        context.add_message({"role": "user", "content": prompts.IDLE_FAREWELL_MESSAGE})
        await processor.push_frame(LLMRunFrame())
        await asyncio.sleep(2)
        await processor.push_frame(EndFrame())

    idle_disconnector = IdleFrameProcessor(
        callback=on_idle_disconnect,
        timeout=config.idle_disconnect_secs,
        name="idle_disconnector",
    )

    idle_prompter = IdleFrameProcessor(
        callback=on_idle_prompt,
        timeout=config.idle_prompt_secs,
        name="idle_prompter",
    )

    # Order: disconnector before prompter so prompter's LLMRunFrame
    # does not reset the disconnector's idle timer.
    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        idle_disconnector,
        idle_prompter,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    return worker, context
