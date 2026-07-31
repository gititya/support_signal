import os

import openai

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_client() -> openai.OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY environment variable not set.")
    return openai.OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
