"""Services module with error-handled factories.

This module provides factory functions to create Pipecat services from the config dataclass.
Each factory wraps initialization in try/except and raises a clear, actionable error
if a service fails to start.
"""

from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.whisper.stt import WhisperSTTService


def create_stt(config):
    """Create and return a WhisperSTTService from the config dataclass.
    
    Args:
        config: A Config dataclass instance containing whisper settings.
        
    Returns:
        WhisperSTTService: The initialized speech-to-text service.
        
    Raises:
        SystemExit: If the STT service fails to initialize with a clear error message.
    """
    try:
        stt = WhisperSTTService(
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
            settings=WhisperSTTService.Settings(
                model=config.whisper_model,
            ),
        )
        return stt
    except Exception as e:
        print(
            f"Failed to initialize Whisper STT: {e}\n"
            f"Check that WHISPER_MODEL='{config.whisper_model}' is valid "
            f"and WHISPER_DEVICE='{config.whisper_device}' is available.",
            file=sys.stderr
        )
        sys.exit(1)


def create_llm(config):
    """Create and return an OLLamaLLMService from the config dataclass.
    
    Args:
        config: A Config dataclass instance containing Ollama settings.
        
    Returns:
        OLLamaLLMService: The initialized language model service.
        
    Raises:
        SystemExit: If the LLM service fails to initialize with a clear error message.
    """
    try:
        llm = OLLamaLLMService(
            base_url=config.ollama_base_url,
            settings=OLLamaLLMService.Settings(
                model=config.ollama_model,
            ),
        )
        return llm
    except Exception as e:
        error_message = str(e).lower()
        if "connection" in error_message or "refused" in error_message:
            print(
                f"Failed to initialize Ollama LLM: connection refused to {config.ollama_base_url}\n"
                f"Make sure Ollama is running. You can start it with: `ollama serve`",
                file=sys.stderr
            )
        else:
            print(
                f"Failed to initialize Ollama LLM: {e}\n"
                f"Check that OLLAMA_MODEL='{config.ollama_model}' is valid "
                f"and OLLAMA_BASE_URL='{config.ollama_base_url}' is correct.",
                file=sys.stderr
            )
        sys.exit(1)


def create_tts(config):
    """Create and return a CartesiaTTSService from the config dataclass.
    
    Args:
        config: A Config dataclass instance containing Cartesia settings.
        
    Returns:
        CartesiaTTSService: The initialized text-to-speech service.
        
    Raises:
        SystemExit: If the TTS service fails to initialize with a clear error message.
    """
    try:
        tts = CartesiaTTSService(
            api_key=config.cartesia_api_key,
            settings=CartesiaTTSService.Settings(
                voice=config.cartesia_voice_id,
            ),
        )
        return tts
    except Exception as e:
        print(
            f"Failed to initialize Cartesia TTS: {e}\n"
            f"Check that CARTESIA_VOICE_ID='{config.cartesia_voice_id}' is valid.",
            file=sys.stderr
        )
        sys.exit(1)


import sys
