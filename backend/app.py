from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.settings import settings
from backend.routers.chat import router as chat_router
from backend.routers.ingest import router as ingest_router
from backend.routers.agent import router as agent_router
from backend.routers.uploads import router as uploads_router

app = FastAPI(title="RAG Agentic Assistant Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")

@app.get("/health")
def health():
    return {"ok": True}
