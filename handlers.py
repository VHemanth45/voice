"""Handlers module with graceful shutdown.

This module contains standalone event handler functions for transport and worker lifecycle events.
Handler functions are pure — they take worker/context/transport as args, no module-level globals.
"""

import asyncio
import logging

from loguru import logger

import prompts
from pipecat.frames.frames import LLMRunFrame


async def on_client_connected(transport, client, worker, context):
    """Handle client connection event.
    
    Args:
        transport: The transport instance.
        client: The client instance.
        worker: The PipelineWorker instance.
        context: The LLMContext instance.
    
    Logs the connection and injects the greeting as a user-role message from the prompts module.
    """
    logger.info("Client connected")
    context.add_message({"role": "user", "content": prompts.GREETING_MESSAGE})
    await worker.queue_frames([LLMRunFrame()])


async def on_client_disconnected(transport, client, worker):
    """Handle client disconnection event with graceful shutdown.
    
    Args:
        transport: The transport instance.
        client: The client instance.
        worker: The PipelineWorker instance.
    
    Uses asyncio.wait_for with a 5-second timeout to prevent the process from hanging.
    Logs a warning if the worker doesn't cancel within the timeout.
    """
    logger.info("Client disconnected")
    try:
        await asyncio.wait_for(worker.cancel(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("Worker cancel timed out after 5 seconds")


async def on_pipeline_error(worker, error):
    """Handle pipeline error events.
    
    Args:
        worker: The PipelineWorker instance.
        error: The error that occurred.
    
    Logs the error with context instead of crashing silently.
    """
    logger.error(f"Pipeline error: {error}")
    # Log additional context if available
    if hasattr(error, '__traceback__'):
        logger.exception("Pipeline error with traceback")
