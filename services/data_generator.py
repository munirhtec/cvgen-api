import json
from typing import List
from pydantic import BaseModel
from lib.llm import get_llm_response

from models.record import SyntheticDataBatch

from lib.prompts import load_prompt

def generate_batch(count: int = 5) -> SyntheticDataBatch:
    """
    Generate a batch of synthetic employee data.
    Returns a Pydantic model containing linked HRM, xOPS, and Custom records.
    """
    prompts = load_prompt("data_generation")
    
    user_prompt = prompts["user"].replace("{{ count }}", str(count))

    print(f"Generating {count} synthetic records...")
    
    try:
        response = get_llm_response(
            system_prompt=prompts["system"],
            user_prompt=user_prompt,
            temperature=0.7,
            model="l2-gpt-4o-mini",  # Use cheaper model for data generation
            response_model=SyntheticDataBatch
        )
        return response.parsed
    except Exception as e:
        print(f"Data generation failed: {e}")
        # Return empty batch on failure to prevent crash
        return SyntheticDataBatch(hrm=[], xops=[], custom=[])
