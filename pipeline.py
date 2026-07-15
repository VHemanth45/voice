from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)

import prompts
import services


def _create_metrics_observer():
    """Return an observer that logs pipeline metrics frames at DEBUG level."""
    return MetricsLogObserver()


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
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=[_create_metrics_observer()],
    )

    return worker, context
