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

def get_llm_response(question: str):
    response = client.chat.completions.create(
        model=settings.model,
        messages=[
            {
                "role": "system",
                "content": "You are helpful CV bot."
            },
            {
                "role": "user",
                "content": question
            },
        ]
    )

    return response