from fastapi import APIRouter, Depends
from core.auth import bearer_auth
from core.models import ChatRequest, ChatResponse
from core.settings import settings
from rag.retriever import retrieve_topk
from rag.prompts import SYSTEM_PROMPT
from core.logging import log_interaction
from openai import OpenAI

router = APIRouter(tags=["chat"])

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# @router.get("/debug/search")
# def debug_search(q: str, _ok: bool = Depends(bearer_auth)):
#     from rag.retriever import retrieve_topk
#     hits = retrieve_topk(q, top_k=5)
#     for h in hits:
#         if len(h["text"]) > 240:
#             h["text"] = h["text"][:240] + "…"
#     return {"hits": hits}

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, _ok: bool = Depends(bearer_auth)):
    ctx = retrieve_topk(req.query, top_k=req.top_k)
    context_text = "\n\n---\n".join([f"[{i+1}] {c['text']}" for i, c in enumerate(ctx)])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {req.query}\n\nContext:\n{context_text}"},
    ]
    resp = client.chat.completions.create(model=settings.ANSWER_MODEL, messages=messages, temperature=0.2)
    answer = resp.choices[0].message.content
    citations = [{"id": c["id"], "meta": c["meta"]} for c in ctx]
    log_interaction(req.query, answer, citations)
    return {"answer": answer, "citations": citations}
