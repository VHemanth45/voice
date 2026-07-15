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
