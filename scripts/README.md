# Scripts Directory

This directory contains utility scripts for data generation, evaluation, and testing.

## Available Scripts

### 1. `generate_data.py`
**Purpose**: Generate synthetic employee data using LLM

**Usage**:
```bash
cd cvgen-api
python scripts/generate_data.py
```

**Output**: Creates/appends to `data/hrm.json`, `data/xops.json`, `data/custom.json`

---

### 2. `evaluate.py`
**Purpose**: Manual CV generation evaluation (legacy)

**Usage**:
```bash
cd cvgen-api
python scripts/evaluate.py
```

**Requirements**: Run `generate_data.py` first to create test data

**Output**: `evaluation_report.md` with quality scores

---

### 3. `ragas_evaluate.py`
**Purpose**: Automated RAGAS-inspired evaluation with 5 metrics

**Usage**:
```bash
cd cvgen-api
python scripts/ragas_evaluate.py          # Evaluate 5 samples (default)
python scripts/ragas_evaluate.py 10       # Evaluate 10 samples
```

**Output**: 
- Console output with metrics
- `ragas_evaluation_report.json` with detailed results

**Metrics**:
- Context Relevancy (0-1)
- Answer Relevancy (0-1)
- Faithfulness (0-1) - hallucination detection
- Completeness (0-1)
- Overall Score (0-10)

---

### 4. `verify_startup.py`
**Purpose**: Test that FAISS index loads correctly and data generation works

**Usage**:
```bash
cd cvgen-api
python scripts/verify_startup.py
```

**Output**: Confirms data loading and displays sample record

---

## Notes

- All scripts must be run from the `cvgen-api` directory (not from `scripts/`)
- Scripts automatically add parent directory to Python path for imports
- Ensure `.env` file is configured with API keys before running
