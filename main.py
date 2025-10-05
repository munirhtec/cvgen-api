from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from services import rag_faiss  # import your service module

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("🚀 Loading FAISS index at startup...")
        records = rag_faiss.merge_records_on_the_fly()
        rag_faiss.build_index(records)
        print("✅ FAISS index ready.")
        yield
    except asyncio.CancelledError:
        print("⚠️ Lifespan task cancelled.")
        raise
    finally:
        print("👋 Shutting down...")

app = FastAPI(lifespan=lifespan)

from routers import llm, rag, helpers

app.include_router(llm.router, prefix="/llm", tags=["LLM"])
app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(helpers.router, prefix="/helpers", tags=["Helpers"])
