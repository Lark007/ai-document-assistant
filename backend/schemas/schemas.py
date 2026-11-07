# 作用：项目里所有 Pydantic 模型集中放这里。

from typing import List, Optional
from pydantic import BaseModel, Field


# ============ 文档结构化分析的输出结构 ============
# 它同时被两处使用：
#   1. services/llm_service.py：校验大模型返回的 JSON，字段不对就报错；
#   2. 下面 AnalysisRecordResponse：读取已保存结果时再校验一次。
class DocumentAnalysis(BaseModel):
    summary: str = Field(..., description="文档整体摘要")
    key_points: List[str] = Field(default_factory=list, description="关键要点")
    keywords: List[str] = Field(default_factory=list, description="核心关键词")
    action_items: List[str] = Field(default_factory=list, description="待办事项")
    questions: List[str] = Field(default_factory=list, description="可探讨的问题")


# ============ POST /analysis/document 的请求体 ============
class AnalysisRequest(BaseModel):
    """document_id 故意设成可选。

    这样「传了 body 但字段写错」会被 Pydantic 拦下（422），
    而「完全没传 body」还能落到 api/analysis.py 里手工解析的老逻辑上，不会误报 422。
    """

    document_id: Optional[int] = Field(default=None, description="要分析的文档 ID")


# ============ GET /analysis/document/{document_id} 的响应体 ============
class AnalysisRecordResponse(BaseModel):
    """
    document_id  : 这份结果属于哪份文档
    record_id    : analysis_records 表里的自增 ID，同一份文档多次分析时可以靠它区分
    analysis_type: 记录类型，当前只有 "structured_output"
    created_at   : 这条记录存进数据库的时间
    result       : 真正的结构化分析结果（五个字段）
    """

    document_id: int
    record_id: Optional[int] = None
    analysis_type: str = "structured_output"
    created_at: Optional[str] = None
    result: DocumentAnalysis
