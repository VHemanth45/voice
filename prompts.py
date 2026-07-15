import os

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful voice assistant. "
    "Keep responses concise — one or two sentences. "
    "Be friendly and conversational."
)

# User-role instruction used to trigger the greeting from the LLM,
# preventing system context pollution on repeated connects.
GREETING_MESSAGE = "[System: The user just connected. Greet them briefly and introduce yourself.]"

# User-role instruction for idle prompt
# Used by IdleFrameProcessor to re-engage the user after inactivity.
IDLE_PROMPT_MESSAGE = "[System: The user has been silent for a while. Ask them if they are still there in a friendly way.]"

# User-role instruction for idle disconnect farewell
# Used by IdleFrameProcessor to say goodbye before disconnecting due to prolonged inactivity.
IDLE_FAREWELL_MESSAGE = "[System: The user has been silent for too long. Say a brief farewell and let them know they can reconnect later.]"
