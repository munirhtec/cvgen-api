import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import rag_faiss
import os

def test_startup():
    print("Testing startup data generation...")
    # Ensure data files don't exist (we renamed data folder)
    if os.path.exists("data/hrm.json"):
        print("Warning: data/hrm.json exists, test may rely on file instead of generator.")
    else:
        print("Confirmed: data/*.json files are missing. Expecting generation.")

    records = rag_faiss.merge_records_on_the_fly()
    
    if len(records) > 0:
        print(f"SUCCESS: Loaded {len(records)} records.")
        print("Sample Record Name:", records[0].get('full_name'))
    else:
        print("FAILURE: No records loaded.")

if __name__ == "__main__":
    test_startup()
