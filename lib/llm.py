import openai
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str
    base_url: str
    model: str = "l2-gpt-4o"

    class Config:
        env_file = ".env"


settings = Settings()

client = openai.OpenAI(
    api_key=settings.api_key,
    base_url=settings.base_url,
)


def get_llm_response(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    top_p: float = 0.9,
    model: str | None = None,
):
    """
    Send a chat completion request using explicit system and user prompts.
    """
    response = client.chat.completions.create(
        model=model or settings.model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=temperature,
        top_p=top_p,
    )

    return response
