"""
RAGAS-Inspired Automated Evaluation Script
==========================================

Implements automated RAG evaluation metrics grounded in real FAISS retrieval:

  context_relevancy  — avg cosine similarity of top-k FAISS chunks retrieved
                       for this employee's query vs. the indexed corpus.
                       This is a genuine retrieval metric, not an LLM opinion.

  answer_relevancy   — LLM score: how well the generated CV maps back to the
                       source data fields.

  faithfulness       — LLM score: no hallucinations (all CV facts traceable
                       to the employee record).

  completeness       — LLM score: critical source fields present in final CV.

  overall_score      — LLM holistic quality score (0-10).

Pipeline per employee:
  1. Query FAISS index with employee profile string → retrieve top-k chunks.
  2. context_relevancy  = mean(chunk.similarity) / 100  (normalise 0-100→0-1)
  3. Draft CV with DraftingAgent.
  4. LLM self-critique (ReviewAgent._generate_llm_feedback) → structured issues.
  5. ReviewAgent refines CV using that critique + original employee record.
  6. Final CV evaluated by LLM judge for answer_relevancy / faithfulness /
     completeness / overall_score.

Errors are logged independently; failed samples are skipped rather than
injected as zero-scored entries.

References:
  https://docs.ragas.io/en/latest/concepts/metrics/index.html
  https://www.confident-ai.com/blog/a-complete-guide-to-rag-evaluation
"""

import json
import sys
import traceback
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel

from lib.llm import get_llm_response, get_model_for_task
from services.rag_faiss import (
    merge_records_on_the_fly,
    build_index,
    search_with_scores,
    serialize_record,
)
from services.agents import DraftingAgent, ReviewAgent




from models.evaluation import EvaluationMetrics, LLMEvaluationScores, RAGASEvaluationReport




def compute_context_relevancy(employee_record: dict, top_k: int = 5) -> float:
    """
    Retrieve the top-k chunks from the FAISS index using this employee's
    serialised profile as the query.  context_relevancy is the mean cosine
    similarity of the returned chunks (normalised from the 0-100 scale that
    search_with_scores uses to 0-1).

    This gives a genuine, data-driven retrieval quality metric.
    """
    query = serialize_record(employee_record, mode="detailed")
    try:
        results = search_with_scores(query, top_k=top_k)
        if not results:
            print("  ⚠ FAISS returned no results for this employee.")
            return 0.0
        # search_with_scores returns similarity in 0-100 range
        mean_similarity = sum(r["similarity"] for r in results) / len(results)
        return round(min(mean_similarity / 100.0, 1.0), 4)
    except Exception as e:
        print(f"  ⚠ FAISS retrieval error (context_relevancy set to None): {e}")
        raise




from lib.prompts import load_prompt

def evaluate_cv_with_llm(
    employee_record: dict,
    generated_cv: dict,
) -> LLMEvaluationScores:
    """
    Call the LLM judge to score faithfulness, completeness, answer_relevancy,
    and overall_score.  Raises on failure so callers can isolate errors.
    """
    prompts = load_prompt("ragas_judge")
    user_prompt = (
        prompts["user"]
        .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
        .replace("{{ generated_cv }}", json.dumps(generated_cv, indent=2))
    )
    response = get_llm_response(
        system_prompt=prompts["system"],
        user_prompt=user_prompt,
        temperature=0.1,
        model=get_model_for_task("cv_review"),
        response_model=LLMEvaluationScores,
    )
    return response.parsed




def evaluate_single(
    record: dict,
    drafting_agent: DraftingAgent,
    review_agent: ReviewAgent,
    sample_index: int,
    total: int,
) -> Optional[EvaluationMetrics]:
    """
    Run the full pipeline for one employee record:
      FAISS retrieval → draft → LLM self-feedback → review → LLM judge

    Returns EvaluationMetrics on success, or None on any runtime failure
    (error already printed; caller must NOT treat None as a zero score).
    """
    name = record.get("full_name", "Unknown")
    print(f"\n📄 [{sample_index}/{total}] {name}")

    try:
        context_relevancy = compute_context_relevancy(record)
        print(f"  ✓ FAISS context_relevancy: {context_relevancy:.3f}")
    except Exception as e:
        print(f"  ✗ FAISS retrieval failed — skipping sample. Error: {e}")
        traceback.print_exc()
        return None

    try:
        draft = drafting_agent.generate(record)
    except Exception as e:
        print(f"  ✗ DraftingAgent failed — skipping sample. Error: {e}")
        traceback.print_exc()
        return None

    try:
        draft = review_agent.review(draft, employee_record=record)
    except Exception as e:
        # Review failure is non-fatal; proceed with the unreviewed draft.
        print(f"  ⚠ ReviewAgent failed (evaluating unreviewed draft). Error: {e}")
        traceback.print_exc()

    try:
        llm_scores = evaluate_cv_with_llm(record, draft["cv"])
    except Exception as e:
        print(f"  ✗ LLM judge failed — skipping sample. Error: {e}")
        traceback.print_exc()
        return None

    metrics = EvaluationMetrics(
        context_relevancy=context_relevancy,
        answer_relevancy=llm_scores.answer_relevancy,
        faithfulness=llm_scores.faithfulness,
        completeness=llm_scores.completeness,
        overall_score=llm_scores.overall_score,
        reasoning=llm_scores.reasoning,
    )

    print(f"  ✓ answer_relevancy: {metrics.answer_relevancy:.2f}")
    print(f"  ✓ faithfulness:     {metrics.faithfulness:.2f}")
    print(f"  ✓ completeness:     {metrics.completeness:.2f}")
    print(f"  ✓ overall_score:    {metrics.overall_score:.1f}/10")

    return metrics




def run_ragas_evaluation(num_samples: int = 5) -> RAGASEvaluationReport:
    """
    Run RAGAS-style evaluation on `num_samples` employee records.

    Skips (and counts) records that fail at any stage rather than polluting
    the aggregate scores with artificial zeros.

    Returns:
        RAGASEvaluationReport — aggregated metrics over successful samples only.
    """
    print(f"🔍 RAGAS evaluation — {num_samples} sample(s)")

    print("📦 Merging & indexing employee records…")
    all_records = merge_records_on_the_fly()
    if not all_records:
        raise RuntimeError("No employee records returned from merge_records_on_the_fly().")

    build_index(all_records, mode="detailed")
    print(f"  ✓ FAISS index built with {len(all_records)} records.")

    sample_records = all_records[:num_samples]

    drafting_agent = DraftingAgent()
    review_agent = ReviewAgent()

    evaluations: List[EvaluationMetrics] = []
    failed = 0

    for i, record in enumerate(sample_records, start=1):
        result = evaluate_single(record, drafting_agent, review_agent, i, len(sample_records))
        if result is None:
            failed += 1
        else:
            evaluations.append(result)

    if not evaluations:
        print("\n⚠️  No evaluations succeeded; returning empty report.")
        return RAGASEvaluationReport(
            total_samples=len(sample_records),
            successful_evaluations=0,
            failed_samples=failed,
            evaluations=[],
            average_context_relevancy=0.0,
            average_answer_relevancy=0.0,
            average_faithfulness=0.0,
            average_completeness=0.0,
            average_overall_score=0.0,
        )

    n = len(evaluations)
    avg_context   = sum(e.context_relevancy  for e in evaluations) / n
    avg_answer    = sum(e.answer_relevancy    for e in evaluations) / n
    avg_faith     = sum(e.faithfulness        for e in evaluations) / n
    avg_complete  = sum(e.completeness        for e in evaluations) / n
    avg_overall   = sum(e.overall_score       for e in evaluations) / n

    report = RAGASEvaluationReport(
        total_samples=len(sample_records),
        successful_evaluations=n,
        failed_samples=failed,
        evaluations=evaluations,
        average_context_relevancy=avg_context,
        average_answer_relevancy=avg_answer,
        average_faithfulness=avg_faith,
        average_completeness=avg_complete,
        average_overall_score=avg_overall,
    )

    print(f"\n{'='*60}")
    print("📊 RAGAS EVALUATION SUMMARY")
    print(f"{'='*60}")
    print(f"  Samples evaluated:          {n}/{len(sample_records)}  ({failed} failed)")
    print(f"  Avg context relevancy:      {avg_context:.3f}  (real FAISS similarity)")
    print(f"  Avg answer relevancy:       {avg_answer:.2f}")
    print(f"  Avg faithfulness:           {avg_faith:.2f}")
    print(f"  Avg completeness:           {avg_complete:.2f}")
    print(f"  Avg overall score:          {avg_overall:.1f}/10")
    print(f"{'='*60}\n")

    return report




if __name__ == "__main__":
    num_samples = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    report = run_ragas_evaluation(num_samples)

    output_file = "ragas_evaluation_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)

    print(f"✅ Full report saved to: {output_file}")
