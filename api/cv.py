import copy
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Dict
from services.rag_faiss import find_employee
from services.agents import DraftingAgent, ReviewAgent, RefinementAgent
from fastapi.responses import StreamingResponse
import json
import asyncio
import queue

router = APIRouter()
from services.cv_service import create_pipeline, get_pipeline, pipelines

# FastAPI routes
@router.post("/start/{employee_query}")
async def start_cv(employee_query: str):
    employee = find_employee(employee_query)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    pipeline = create_pipeline(employee)
    pipeline_queue = queue.Queue()
    
    def log_cb(msg):
        pipeline_queue.put({"type": "message", "data": msg})

    async def process_generator():
        yield json.dumps({"type": "message", "data": f"🚀 Starting automated CV generation for {employee.get('full_name', 'Unknown')}"}) + "\n"
        
        loop = asyncio.get_event_loop()
        
        def run_pipeline():
            try:
                pipeline.draft(log_cb=log_cb)
                pipeline.review(log_cb=log_cb)
                final_result = pipeline.refine(log_cb=log_cb)
                
                pipeline_queue.put({
                    "type": "done",
                    "message": "CV generated through 3-agent pipeline",
                    "employee_id": pipeline.employee_id,
                    "draft": final_result,
                    "pipeline_stages": ["drafting", "review", "refinement"]
                })
            except Exception as e:
                pipeline_queue.put({"type": "error", "message": str(e)})

        task = loop.run_in_executor(None, run_pipeline)
        
        while True:
            try:
                msg = pipeline_queue.get_nowait()
                yield json.dumps(msg) + "\n"
                if msg["type"] in ["done", "error"]:
                    break
            except queue.Empty:
                await asyncio.sleep(0.1)
                
    return StreamingResponse(process_generator(), media_type="application/x-ndjson")


@router.get("/draft/{employee_id}")
def get_draft(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return {"draft": pipeline.cv}


@router.post("/review/{employee_id}")
def review_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return pipeline.review()


@router.post("/refine/{employee_id}")
def refine_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return pipeline.refine()


from models.api_cv import FeedbackRequest

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    pipeline = get_pipeline(request.employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    
    pipeline_queue = queue.Queue()
    
    def log_cb(msg):
        pipeline_queue.put({"type": "message", "data": msg})
        
    async def process_generator():
        yield json.dumps({"type": "message", "data": f"🚀 Processing feedback: '{request.feedback}'"}) + "\n"
        
        loop = asyncio.get_event_loop()
        def run_pipeline():
            try:
                pipeline.add_feedback(request.feedback, log_cb=log_cb)
                pipeline_queue.put({
                    "type": "done",
                    "success": True, 
                    "message": "Feedback applied", 
                    "draft": pipeline.cv
                })
            except Exception as e:
                pipeline_queue.put({"type": "error", "message": str(e)})

        task = loop.run_in_executor(None, run_pipeline)
        
        while True:
            try:
                msg = pipeline_queue.get_nowait()
                yield json.dumps(msg) + "\n"
                if msg["type"] in ["done", "error"]:
                    break
            except queue.Empty:
                await asyncio.sleep(0.1)

    return StreamingResponse(process_generator(), media_type="application/x-ndjson")
    

@router.post("/reset/{employee_id}")
def reset_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    pipeline.reset()
    return {"success": True, "message": "Pipeline reset"}
