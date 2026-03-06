from typing import List
from pydantic import BaseModel

class EvaluationMetrics(BaseModel):
    """Quality metrics for a single CV generation (LLM-judged only)."""
    context_relevancy: float   # 0-1  real retrieval similarity from FAISS
    answer_relevancy: float    # 0-1  LLM: CV maps back to source fields
    faithfulness: float        # 0-1  LLM: zero hallucinations
    completeness: float        # 0-1  LLM: all critical info present
    overall_score: float       # 0-10 LLM holistic quality
    reasoning: str             # Explanation of LLM-judged scores

class LLMEvaluationScores(BaseModel):
    """Internal schema for the LLM judge response (no context_relevancy)."""
    answer_relevancy: float
    faithfulness: float
    completeness: float
    overall_score: float
    reasoning: str

class RAGASEvaluationReport(BaseModel):
    """Aggregated report across all successful CV evaluations."""
    total_samples: int
    successful_evaluations: int
    failed_samples: int
    evaluations: List[EvaluationMetrics]
    average_context_relevancy: float
    average_answer_relevancy: float
    average_faithfulness: float
    average_completeness: float
    average_overall_score: float
