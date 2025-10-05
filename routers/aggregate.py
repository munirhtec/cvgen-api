from fastapi import APIRouter
from services.aggregator import load_dataset, merge_records

router = APIRouter()

@router.get("/unified-records")
def get_unified_records():
    hrm = load_dataset("data/hrm.json")
    xops = load_dataset("data/xops.json")
    custom = load_dataset("data/custom.json")

    merged = merge_records(hrm, xops, custom)

    return {"records": list(merged.values())}
