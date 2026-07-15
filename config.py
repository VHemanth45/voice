import os
import sys
from dataclasses import dataclass
from typing import Literal
from dotenv import load_dotenv

# Load env variables
load_dotenv(override=True)

VALID_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large-v3"}
VALID_WHISPER_DEVICES = {"auto", "cpu", "cuda"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

@dataclass(frozen=True)
class Config:
    cartesia_api_key: str
    cartesia_voice_id: str
    ollama_base_url: str
    ollama_model: str
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    vad_stop_secs: float
    vad_start_secs: float
    idle_prompt_secs: float
    idle_disconnect_secs: float
    log_level: str

    def __post_init__(self):
        # 1. Validate CARTESIA_API_KEY
        if not self.cartesia_api_key or self.cartesia_api_key == "your_cartesia_api_key_here":
            print(
                "Error: CARTESIA_API_KEY is not configured or is set to the placeholder.\n"
                "Please set a valid CARTESIA_API_KEY in your .env file. "
                "See .env.example for details.",
                file=sys.stderr
            )
            sys.exit(1)

        # 2a. Validate IDLE_PROMPT_SECS and IDLE_DISCONNECT_SECS
        for name, val in [("IDLE_PROMPT_SECS", self.idle_prompt_secs), ("IDLE_DISCONNECT_SECS", self.idle_disconnect_secs)]:
            try:
                f_val = float(val)
                if f_val <= 0:
                    raise ValueError("Must be a positive float")
            except (ValueError, TypeError) as e:
                print(
                    f"Error: Invalid value for {name}: '{val}'. "
                    f"It must be a positive float.",
                    file=sys.stderr
                )
                sys.exit(1)

        # 2. Validate VAD_STOP_SECS and VAD_START_SECS
        for name, val in [("VAD_STOP_SECS", self.vad_stop_secs), ("VAD_START_SECS", self.vad_start_secs)]:
            try:
                f_val = float(val)
                if f_val <= 0:
                    raise ValueError("Must be a positive float")
            except (ValueError, TypeError) as e:
                print(
                    f"Error: Invalid value for {name}: '{val}'. "
                    f"It must be a positive float.",
                    file=sys.stderr
                )
                sys.exit(1)

        # 3. Validate WHISPER_MODEL
        if self.whisper_model not in VALID_WHISPER_MODELS:
            print(
                f"Error: Invalid WHISPER_MODEL '{self.whisper_model}'. "
                f"Must be one of: {', '.join(sorted(VALID_WHISPER_MODELS))}.",
                file=sys.stderr
            )
            sys.exit(1)

        # 4. Validate WHISPER_DEVICE
        if self.whisper_device not in VALID_WHISPER_DEVICES:
            print(
                f"Error: Invalid WHISPER_DEVICE '{self.whisper_device}'. "
                f"Must be one of: {', '.join(sorted(VALID_WHISPER_DEVICES))}.",
                file=sys.stderr
            )
            sys.exit(1)

        # 5. Validate LOG_LEVEL
        if self.log_level.upper() not in VALID_LOG_LEVELS:
            print(
                f"Error: Invalid LOG_LEVEL '{self.log_level}'. "
                f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}.",
                file=sys.stderr
            )
            sys.exit(1)


def load_config() -> Config:
    # Read raw environment variables and provide defaults where applicable
    cartesia_api_key = os.getenv("CARTESIA_API_KEY", "").strip()
    cartesia_voice_id = os.getenv("CARTESIA_VOICE_ID", "71a7ad14-091c-4e8e-a314-022ece01c121").strip()
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:4b").strip()
    whisper_model = os.getenv("WHISPER_MODEL", "small").strip()
    whisper_device = os.getenv("WHISPER_DEVICE", "auto").strip()
    whisper_compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip()
    
    # Try converting numeric idle timeout values
    try:
        idle_prompt_secs = float(os.getenv("IDLE_PROMPT_SECS", "15"))
    except ValueError:
        idle_prompt_secs = os.getenv("IDLE_PROMPT_SECS")

    try:
        idle_disconnect_secs = float(os.getenv("IDLE_DISCONNECT_SECS", "60"))
    except ValueError:
        idle_disconnect_secs = os.getenv("IDLE_DISCONNECT_SECS")

    # Try converting numeric values early, let dataclass post_init handle final validation
    try:
        vad_stop_secs = float(os.getenv("VAD_STOP_SECS", "0.3"))
    except ValueError:
        vad_stop_secs = os.getenv("VAD_STOP_SECS")  # type: ignore

    try:
        vad_start_secs = float(os.getenv("VAD_START_SECS", "0.2"))
    except ValueError:
        vad_start_secs = os.getenv("VAD_START_SECS")  # type: ignore

    log_level = os.getenv("LOG_LEVEL", "INFO").strip()

    config = Config(
        cartesia_api_key=cartesia_api_key,
        cartesia_voice_id=cartesia_voice_id,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        whisper_model=whisper_model,
        whisper_device=whisper_device,
        whisper_compute_type=whisper_compute_type,
        vad_stop_secs=vad_stop_secs,  # type: ignore
        vad_start_secs=vad_start_secs,  # type: ignore
        idle_prompt_secs=idle_prompt_secs,  # type: ignore
        idle_disconnect_secs=idle_disconnect_secs,  # type: ignore
        log_level=log_level
    )
    return config
