from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.settings import settings
from routers.chat import router as chat_router
from routers.ingest import router as ingest_router
from routers.agent import router as agent_router
from routers.uploads import router as uploads_router

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
@app.head("/health")
def health():
    return {"ok": True}
