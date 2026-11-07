from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from config import INDEX_DIR
from database import get_db
import logging

from services.rag import RAG

router = APIRouter()
logger = logging.getLogger(__name__)

# ============ 请求体模型 ============
class QARequest(BaseModel):
    document_id: int
    question: str

# 提供用户问题和文件id，对文件进行追问，前提是该id被索引
@router.post("/")
def qa(req: QARequest, request: Request):
    # 拿文件
    # 拿到前端给的id
    document_id = req.document_id
    question = req.question

    rag = request.app.state.rag_service
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG 服务未就绪")

    # 从数据库拿文件
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM documents WHERE id = ?", (document_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="文档不存在")
        filename = row["filename"]

    if not rag.has_source(str(document_id)):
        logger.warning("问答被拒：文档 %s 还没有建立索引", document_id)
        raise HTTPException(status_code=409, detail="这份文档还没有建立索引，请先建立索引")

    # reply = rag.answer(question, top_k=3, source_filter=str(document_id))

    return rag.answer_with_references(question, top_k=3, source_filter=str(document_id))

# """
#     按文档 ID 建索引。
#     从数据库里查出文档内容，然后索引。
#     """
@router.post("/index/{document_id}")
async def index_document(document_id: int, request: Request):
    rag = request.app.state.rag_service

    # 根据id拿文件
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content, filename FROM documents WHERE id = ?", (document_id,))

        doc = cursor.fetchone()
        if not doc:
            logger.warning("建立索引失败：文档 %s 不存在", document_id)
            raise HTTPException(status_code=404, detail="文档不存在")

    n = rag.index_text(doc["content"], source=str(document_id))

    # 建完立刻持久化到磁盘
    rag.save_index(INDEX_DIR)
    logger.info("文档 %s 索引完成，共 %d 个片段", document_id, n)

    return {
        "message": "索引完成",
        "doc_id": document_id,
        "chunks": n,
        "filename": doc["filename"],
    }


