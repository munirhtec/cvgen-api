from typing import List
from pydantic import BaseModel

class LLMFeedback(BaseModel):
    """Structured self-critique produced by the LLM before the review pass."""
    issues: List[str]
    suggestions: List[str]
    summary: str
