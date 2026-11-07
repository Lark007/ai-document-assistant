from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.agent.agent import run_agent

router = APIRouter()

class AgentRequest(BaseModel):
    question: str


# 路径写空字符串，接口地址就是 /agent；写成 "/" 会变成 /agent/ 并触发 307 跳转
@router.post("")
async def agent(req: AgentRequest, request: Request):
    rag = request.app.state.rag_service
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG 服务未就绪")

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    return await run_agent(req.question, rag)