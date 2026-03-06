import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel
from services.agents import DraftingAgent, ReviewAgent, RefinementAgent
from models.cv import CVSchema
from lib.llm import get_llm_response
from services.rag_faiss import merge_records_on_the_fly, build_index

class EvaluationResult(BaseModel):
    score: int
    reasoning: str
    completeness: str
    professionalism: str
    hallucinations: str  # New field to track hallucinations

def evaluate_cv(original_data: dict, generated_cv: dict, stage: str):
    """
    Evaluate CV quality at a specific pipeline stage.
    
    Args:
        original_data: Source employee data
        generated_cv: Generated CV
        stage: Pipeline stage name (for context)
    """
    system_prompt = f"""You are a QA specialist for CV generation software.
    Evaluate the generated CV against the source data.
    
    This CV is from the {stage} stage of the pipeline.
    Be strict about hallucinations - any information not in source data."""
    
    user_prompt = f"""
    SOURCE DATA:
    {json.dumps(original_data, indent=2)}

    GENERATED CV:
    {json.dumps(generated_cv, indent=2)}

    Evaluate on:
    1. score (1-10): Overall quality
    2. reasoning: Why this score?
    3. completeness: Did it miss any source info?
    4. professionalism: Is the tone good?
    5. hallucinations: Any fabricated information? (List specific examples or "None detected")
    """

    response = get_llm_response(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1,  # Low temp for consistent evaluation
        response_model=EvaluationResult
    )
    return response.parsed

def main():
    print("="*80)
    print("3-AGENT PIPELINE PROGRESSIVE EVALUATION")
    print("="*80)
    print("\nThis script evaluates CV quality at each pipeline stage:")
    print("  Stage 1: Draft only (DraftingAgent)")
    print("  Stage 2: Draft + Review (fact-checking)")
    print("  Stage 3: Draft + Review + Refine (final polish)")
    print("\n" + "="*80 + "\n")
    
    # Load employee data
    print("Loading employee data...")
    records = merge_records_on_the_fly()
    build_index(records)
    
    # Use first 3 records for evaluation
    test_records = records[:3]
    print(f"Testing with {len(test_records)} employee records\n")
    
    # Initialize agents
    drafting_agent = DraftingAgent()
    review_agent = ReviewAgent()
    refinement_agent = RefinementAgent()
    
    all_results = []
    
    for idx, record in enumerate(test_records, 1):
        employee_name = record.get('full_name', 'Unknown')
        print(f"\n{'='*80}")
        print(f"EMPLOYEE {idx}/{len(test_records)}: {employee_name}")
        print(f"{'='*80}\n")
        
        # STAGE 1: Draft Only
        print("📝 STAGE 1: Drafting...")
        draft_output = drafting_agent.generate(record)
        draft_cv = draft_output["cv"]
        
        eval_draft = evaluate_cv(record, draft_cv, "Drafting")
        print(f"  ✓ Score: {eval_draft.score}/10")
        print(f"  ✓ Hallucinations: {eval_draft.hallucinations}")
        
        # STAGE 2: Draft + Review
        print("\n🔍 STAGE 2: Drafting + Review (fact-checking)...")
        reviewed_output = review_agent.review(draft_output.copy())
        reviewed_cv = reviewed_output["cv"]
        
        eval_reviewed = evaluate_cv(record, reviewed_cv, "Drafting + Review")
        print(f"  ✓ Score: {eval_reviewed.score}/10")
        print(f"  ✓ Hallucinations: {eval_reviewed.hallucinations}")
        print(f"  ✓ Improvement: {eval_reviewed.score - eval_draft.score:+d} points")
        
        # STAGE 3: Draft + Review + Refine
        print("\n✨ STAGE 3: Drafting + Review + Refine (final polish)...")
        refined_output = refinement_agent.refine(reviewed_output.copy(), record)
        refined_cv = refined_output["cv"]
        
        eval_refined = evaluate_cv(record, refined_cv, "Full Pipeline")
        print(f"  ✓ Score: {eval_refined.score}/10")
        print(f"  ✓ Hallucinations: {eval_refined.hallucinations}")
        print(f"  ✓ Improvement: {eval_refined.score - eval_reviewed.score:+d} points")
        print(f"  ✓ Total Improvement: {eval_refined.score - eval_draft.score:+d} points")
        
        # Store results
        all_results.append({
            "employee": employee_name,
            "stage_1_draft": {
                "score": eval_draft.score,
                "reasoning": eval_draft.reasoning,
                "completeness": eval_draft.completeness,
                "professionalism": eval_draft.professionalism,
                "hallucinations": eval_draft.hallucinations
            },
            "stage_2_reviewed": {
                "score": eval_reviewed.score,
                "reasoning": eval_reviewed.reasoning,
                "completeness": eval_reviewed.completeness,
                "professionalism": eval_reviewed.professionalism,
                "hallucinations": eval_reviewed.hallucinations,
                "improvement": eval_reviewed.score - eval_draft.score
            },
            "stage_3_refined": {
                "score": eval_refined.score,
                "reasoning": eval_refined.reasoning,
                "completeness": eval_refined.completeness,
                "professionalism": eval_refined.professionalism,
                "hallucinations": eval_refined.hallucinations,
                "improvement": eval_refined.score - eval_reviewed.score,
                "total_improvement": eval_refined.score - eval_draft.score
            }
        })
    
    # Calculate averages
    avg_draft = sum(r["stage_1_draft"]["score"] for r in all_results) / len(all_results)
    avg_reviewed = sum(r["stage_2_reviewed"]["score"] for r in all_results) / len(all_results)
    avg_refined = sum(r["stage_3_refined"]["score"] for r in all_results) / len(all_results)
    
    # Print summary
    print(f"\n\n{'='*80}")
    print("📊 PIPELINE EVALUATION SUMMARY")
    print(f"{'='*80}\n")
    print(f"Average Scores:")
    print(f"  Stage 1 (Draft only):           {avg_draft:.1f}/10")
    print(f"  Stage 2 (Draft + Review):       {avg_reviewed:.1f}/10  ({avg_reviewed - avg_draft:+.1f})")
    print(f"  Stage 3 (Full Pipeline):        {avg_refined:.1f}/10  ({avg_refined - avg_reviewed:+.1f})")
    print(f"\n  Total Pipeline Improvement:     {avg_refined - avg_draft:+.1f} points")
    print(f"\n{'='*80}\n")
    
    # Save detailed report
    with open("pipeline_evaluation_report.md", "w") as f:
        f.write("# 3-Agent Pipeline Evaluation Report\n\n")
        f.write("This report shows the progressive improvement of CV quality through each pipeline stage.\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"| Stage | Average Score | Improvement |\n")
        f.write(f"|-------|---------------|-------------|\n")
        f.write(f"| 1. Draft Only | {avg_draft:.1f}/10 | - |\n")
        f.write(f"| 2. Draft + Review | {avg_reviewed:.1f}/10 | {avg_reviewed - avg_draft:+.1f} |\n")
        f.write(f"| 3. Full Pipeline | {avg_refined:.1f}/10 | {avg_refined - avg_reviewed:+.1f} |\n")
        f.write(f"| **Total Improvement** | - | **{avg_refined - avg_draft:+.1f}** |\n\n")
        
        f.write("## Detailed Results\n\n")
        
        for res in all_results:
            f.write(f"### {res['employee']}\n\n")
            
            f.write(f"#### Stage 1: Draft Only\n")
            f.write(f"- **Score**: {res['stage_1_draft']['score']}/10\n")
            f.write(f"- **Reasoning**: {res['stage_1_draft']['reasoning']}\n")
            f.write(f"- **Completeness**: {res['stage_1_draft']['completeness']}\n")
            f.write(f"- **Professionalism**: {res['stage_1_draft']['professionalism']}\n")
            f.write(f"- **Hallucinations**: {res['stage_1_draft']['hallucinations']}\n\n")
            
            f.write(f"#### Stage 2: Draft + Review\n")
            f.write(f"- **Score**: {res['stage_2_reviewed']['score']}/10 ({res['stage_2_reviewed']['improvement']:+d} improvement)\n")
            f.write(f"- **Reasoning**: {res['stage_2_reviewed']['reasoning']}\n")
            f.write(f"- **Completeness**: {res['stage_2_reviewed']['completeness']}\n")
            f.write(f"- **Professionalism**: {res['stage_2_reviewed']['professionalism']}\n")
            f.write(f"- **Hallucinations**: {res['stage_2_reviewed']['hallucinations']}\n\n")
            
            f.write(f"#### Stage 3: Full Pipeline (Draft + Review + Refine)\n")
            f.write(f"- **Score**: {res['stage_3_refined']['score']}/10 ({res['stage_3_refined']['improvement']:+d} from stage 2, {res['stage_3_refined']['total_improvement']:+d} total)\n")
            f.write(f"- **Reasoning**: {res['stage_3_refined']['reasoning']}\n")
            f.write(f"- **Completeness**: {res['stage_3_refined']['completeness']}\n")
            f.write(f"- **Professionalism**: {res['stage_3_refined']['professionalism']}\n")
            f.write(f"- **Hallucinations**: {res['stage_3_refined']['hallucinations']}\n\n")
            
            f.write("---\n\n")
    
    print("✅ Detailed report saved to: pipeline_evaluation_report.md")
    
    # Save JSON for programmatic access
    with open("pipeline_evaluation_report.json", "w") as f:
        json.dump({
            "summary": {
                "avg_draft": avg_draft,
                "avg_reviewed": avg_reviewed,
                "avg_refined": avg_refined,
                "total_improvement": avg_refined - avg_draft
            },
            "results": all_results
        }, f, indent=2)
    
    print("✅ JSON report saved to: pipeline_evaluation_report.json\n")

if __name__ == "__main__":
    main()
