import yaml
from pathlib import Path


def load_prompt(name: str) -> dict:
    """
    Load a YAML prompt file from the root-level `prompts/` directory.

    Expected structure:
      [project_root]/
        ├── prompts/
        │   ├── drafting.yaml
        │   ├── review.yaml
        │   └── refinement.yaml
        └── lib/
            └── prompts.py
    """
    project_root = Path(__file__).resolve().parents[1]
    prompts_dir = project_root / "prompts"
    prompt_file = prompts_dir / f"{name}.yaml"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    with prompt_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
