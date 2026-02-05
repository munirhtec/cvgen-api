import json
import random
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.data_generator import generate_batch, SyntheticDataBatch

def main():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Generate data
    batch = generate_batch(5)
    
    # Save/Append to files
    files = {
        "hrm.json": [r.model_dump() for r in batch.hrm],
        "xops.json": [r.model_dump() for r in batch.xops],
        "custom.json": [r.model_dump() for r in batch.custom]
    }
    
    for filename, new_records in files.items():
        path = data_dir / filename
        existing = []
        if path.exists():
            try:
                with open(path, "r") as f:
                    existing = json.load(f)
            except:
                pass
        
        # Simple append (duplicates allowed for now or could filter)
        combined = existing + new_records
        
        with open(path, "w") as f:
            json.dump(combined, f, indent=2)
        print(f"Saved {len(new_records)} records to {filename}")

if __name__ == "__main__":
    main()
