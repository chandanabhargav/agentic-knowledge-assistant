# backend/routers/agent.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.core.auth import bearer_auth
from backend.agent.agent import run_agent

router = APIRouter(tags=["agent"])

class AgentReq(BaseModel):
    query: str

@router.post("/agent-chat")
def agent_chat(req: AgentReq, _ok: bool = Depends(bearer_auth)):
    return run_agent(req.query)
