# 对ai提问的各种操作
from pydantic import ValidationError

from schemas.schemas import AnalysisRecordResponse, AnalysisRequest, DocumentAnalysis
from fastapi import APIRouter, Body, HTTPException, Query, Request
from services.llm_service import json_out
from database import get_db
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# 生成ai的分析结果（结构化的），存入本地并返回
@router.post("/document")
async def post_document(
    req: Request,
    regenerate: bool = Query(
        False,
        description="传 true 表示忽略已保存的结果，重新调用模型分析一次",
    ),
    body: AnalysisRequest | None = Body(
        default=None,
        description="请求体，只需要 document_id；旧的 Request 手工取法也仍然支持",
    ),
):

    # 拿到前端给的id。
    # 优先用 Pydantic 校验过的 body（传了 body 但字段不对会返回 422，而不是 500）；
    # 完全没传 body 时再退回手工读请求体，保证老的调用方式还能用。
    document_id = body.document_id if body else None
    if document_id is None:
        try:
            data = await req.json()
        except Exception:
            data = {}
        document_id = data.get("document_id")

    if document_id is None:
        raise HTTPException(status_code=400, detail="缺少 document_id")

    # document_id 必须是整数，否则 SQLite 查不到任何东西，会成为一次「假 404」
    try:
        document_id = int(document_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="document_id 必须是整数")

    # 从数据库拿文件
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM documents WHERE id = ?", (document_id,))

        row = cursor.fetchone()
        if not row:
            logger.warning("结构化分析：文档 %s 不存在", document_id)
            raise HTTPException(status_code=404, detail="文档不存在")
        content = row["content"]

    # 已经存过结果、又没要求重新分析时，直接返回上一次的结果，省钱也更快
    if not regenerate:
        saved = read_analysis_record(document_id)
        if saved is not None:
            return saved['result']

    # 调用大模型分析
    structured_data = await json_out(content)

    # 把分析结果存入 analysis_records
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO analysis_records (document_id, analysis_type, result) VALUES (?, ?, ?)",
            (document_id, "structured_output", json.dumps(structured_data, ensure_ascii=False))
        )
        conn.commit()

    return structured_data


# 读取某份文档上一次保存的分析结果
@router.get("/document/{document_id}", response_model=AnalysisRecordResponse)
async def get_analysis_record(document_id: int):

    # 先确认文档还在，否则返回明确的 404
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="文档不存在")

    record = read_analysis_record(document_id)
    if record is None:
        logger.warning("查看分析结果：文档 %s 还没有分析记录", document_id)
        raise HTTPException(status_code=404, detail="这份文档还没有分析结果，请先分析一次")

    return record


# 公共函数：从 analysis_records 里取最新一条并解析成 dict
# 没有记录、或者存进去的 JSON 已经解析不了时，都返回 None
def read_analysis_record(document_id: int) -> dict | None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, analysis_type, result, created_at
            FROM analysis_records
            WHERE document_id = ? AND analysis_type = 'structured_output'
            ORDER BY id DESC
            LIMIT 1
            """,
            (document_id,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    try:
        result = json.loads(row["result"])
    except (TypeError, json.JSONDecodeError):
        # 数据库里的内容坏了，当作没有结果处理，让用户在页面上重新分析
        return None

    return {
        "document_id": document_id,
        "record_id": row["id"],
        "analysis_type": row["analysis_type"],
        "created_at": row["created_at"],
        "result": result,
    }