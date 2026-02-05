# Evaluation Report

## Methodology

We implemented an automated evaluation pipeline (`scripts/evaluate.py`) that uses an **LLM-as-a-judge** approach to grade generated CVs against the source employee data.

### Evaluation Metrics
1.  **Completeness**: Does the CV contain all critical info (work history, skills, education) present in the source?
2.  **Accuracy**: Are there hallucinations or incorrectly inferred details?
3.  **Professionalism**: Is the tone and formatting appropriate for a potential employer?
4.  **Overall Score (1-10)**: A holistic quality score.

### Process
1.  **Data Generation**: We generated synthetic employee profiles (HRM + xOPS + Custom data) using `scripts/generate_data.py`.
2.  **CV Drafting**: The `DraftingAgent` processed these profiles to create initial CV drafts.
3.  **Grading**: An LLM judge compared the Source Data vs. Generated CV and produced a structured evaluation.

## Findings

**Average Overall Score**: 7.3/10 (Based on initial n=3 run)

### Strengths
- **Structure**: The system consistently produces valid JSON that adheres to the schema.
- **Tone**: The "Professionalism" score is consistently high; the generated summaries are well-written.
- **Data Integration**: Core employment history and education are correctly mapped.

### Areas for Improvement
- **Hallucination**: The model occasionally infers "Fluent English" or generic "Soft Skills" that strictly weren't in the source data (though often true, strict RAG should avoid this).
- **Omissions**: Phone numbers or specific minor details sometimes get dropped if the prompt mapping isn't weighted heavily enough.
- **Context Handling**: Merging xOPS project details into the main "Relevant Projects" section works well but can sometimes lose the specific "role" nuance if the project list is long.

## Recommendations
- **Prompt Refinement**: Tighten instructions to "NEVER infer languages unless specified".
- **Weighting**: Increase importance of "Contact Info" in the drafting prompt.
- **RAG Tuning**: Experiment with `top_p` in the Draft Agent to reduce creativity/hallucination.

## References
- **Ragas**: Inspired our "Faithfulness" metric (checking against source).
- **Arelion Framework**: Similar to our "Completeness" check.
