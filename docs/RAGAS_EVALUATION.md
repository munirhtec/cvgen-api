# RAGAS Evaluation Implementation

## Overview

We've implemented automated RAG evaluation metrics inspired by the [RAGAS framework](https://docs.ragas.io/), providing objective, LLM-based assessment of CV generation quality.

## Metrics Implemented

### 1. **Context Relevancy** (0-1)
Measures how relevant the retrieved employee data is for CV generation.
- **1.0**: All source fields useful for CV
- **0.5**: Some irrelevant fields
- **0.0**: Source data not useful

### 2. **Answer Relevancy** (0-1)
Measures how relevant the generated CV is to the source data.
- **1.0**: CV perfectly matches source data scope
- **0.5**: Some CV sections not grounded in source
- **0.0**: CV unrelated to source

### 3. **Faithfulness** (0-1)
Measures hallucination rate - does CV only contain info from source?
- **1.0**: Zero hallucinations, all facts from source
- **0.5**: Minor inferences (e.g., "Fluent English" not in source)
- **0.0**: Major hallucinations

### 4. **Completeness** (0-1)
Measures if CV includes all critical source information.
- **1.0**: All work history, skills, education included
- **0.5**: Missing some important details
- **0.0**: Major omissions

### 5. **Overall Score** (0-10)
Holistic quality assessment for employer use.

## Usage

### Run Evaluation

```bash
# Evaluate 5 samples (default)
python scripts/ragas_evaluate.py

# Evaluate custom number of samples
python scripts/ragas_evaluate.py 10
```

### Output

The script generates:
1. **Console output**: Real-time metrics for each CV
2. **JSON report**: `ragas_evaluation_report.json` with detailed metrics

Example output:
```
🔍 Running RAGAS evaluation on 5 samples...

📄 Evaluating CV 1/5: Alice Johnson
  ✓ Faithfulness: 0.95
  ✓ Completeness: 0.88
  ✓ Overall: 8.2/10

============================================================
📊 RAGAS EVALUATION SUMMARY
============================================================
Average Context Relevancy:  0.92
Average Answer Relevancy:   0.89
Average Faithfulness:       0.91
Average Completeness:       0.85
Average Overall Score:      8.1/10
============================================================
```

## Implementation Details

### LLM-as-Judge Approach
- Uses `get_model_for_task("cv_review")` (high-quality model) for consistent evaluation
- Low temperature (0.1) for deterministic scoring
- Structured output via Pydantic `EvaluationMetrics` model

### Evaluation Prompt
The system prompt defines strict criteria for each metric, ensuring:
- Objective scoring (no bias)
- Heavy penalties for hallucinations
- Detailed reasoning for each score

## Comparison to Manual Evaluation

| Metric | Manual (evaluation_report.md) | RAGAS (Automated) |
|--------|-------------------------------|-------------------|
| Sample Size | 3 | Configurable (5+ recommended) |
| Time | ~30 min manual review | ~2 min automated |
| Consistency | Subjective | Objective (LLM-based) |
| Metrics | Overall score only | 5 detailed metrics |
| Scalability | Low | High |

## References

- [RAGAS Documentation](https://docs.ragas.io/en/latest/concepts/metrics/index.html)
- [Confident AI RAG Evaluation Guide](https://www.confident-ai.com/blog/a-complete-guide-to-rag-evaluation)
- [RAG Evaluation Best Practices](https://www.rungalileo.io/blog/mastering-rag-evaluation-metrics-testing-and-best-practices)

## Future Enhancements

1. **Context Precision**: Measure if retrieved context is focused (no noise)
2. **Context Recall**: Measure if all necessary context was retrieved
3. **Answer Similarity**: Compare generated CV to reference CVs
4. **Automated Regression Testing**: Run on every code change
