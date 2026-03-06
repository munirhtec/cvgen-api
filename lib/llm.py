import openai
import json
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str
    base_url: str
    model: str = "l2-gpt-4.1-mini"
    embedding_model: str = "l2-text-embedding-3-small"

    class Config:
        env_file = ".env"


settings = Settings()

client = openai.OpenAI(
    api_key=settings.api_key,
    base_url=settings.base_url,
)


# Model selection strategy based on task complexity
MODEL_STRATEGY = {
    "data_generation": "l2-gpt-4o-mini",      # Cheaper, creative tasks
    "cv_drafting": "l2-gpt-4.1",              # Higher quality for drafting
    "cv_review": "l2-gpt-4.1",                # Higher quality for review
    "cv_refinement": "l2-gpt-4.1",            # Higher quality for refinement
    "default": "l2-gpt-4.1"                   # Fallback
}


def get_model_for_task(task: str) -> str:
    """
    Select appropriate model based on task complexity.
    
    Args:
        task: Task identifier (data_generation, cv_drafting, cv_review, cv_refinement)
    
    Returns:
        Model name from MODEL_STRATEGY
    """
    return MODEL_STRATEGY.get(task, MODEL_STRATEGY["default"])


def get_llm_response(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    top_p: float = 0.9,
    model: str | None = None,
    response_model: type[BaseModel] | None = None,
):
    """
    Send a chat completion request.
    If `response_model` is provided, uses structured outputs (parsing).
    Otherwise, returns the raw ChatCompletion object.
    """
    model_name = model or settings.model
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    print(f"🤖 [LLM] Requesting model: {model_name} (Temp: {temperature})")
    if response_model:
        # Inject schema into prompt for reliable JSON generation
        schema = response_model.model_json_schema()
        messages[1]["content"] += f"\n\nReturn the response in valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        
        try:
            # Try native structured outputs if supported (often fails on proxies)
            # return client.beta.chat.completions.parse(...) 
            # Fallback to standard JSON mode
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            print(f"📥 [LLM] Received {len(content)} chars.")
            parsed = response_model.model_validate_json(content)
            # Mock the 'parsed' attribute logic from beta client
            response.parsed = parsed
            return response
        except Exception as e:
            print(f"💥 [LLM] Structured output error: {e}")
            raise e

    print(f"🤖 [LLM] Raw message sent: {messages[1]['content'][:50]}...")
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
    )
    print(f"📥 [LLM] Raw response received.")
    return response
