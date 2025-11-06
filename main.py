from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
import asyncio
from services import rag_faiss

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
        
origins = [
    "http://localhost:5173",  # Vite default dev port
    "http://127.0.0.1:5173",  # Sometimes needed
]

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         # Or ["*"] to allow all (not recommended for prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api import rag, helpers, cv

app.include_router(rag.router, prefix="/rag", tags=["RAG"])
app.include_router(helpers.router, prefix="/helpers", tags=["Helpers"])
app.include_router(cv.router, prefix="/cv", tags=["CV"])