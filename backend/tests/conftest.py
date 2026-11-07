"""作用：pytest 公共配置 —— 让测试能导入后端代码，并且一个网络请求都不发。

关键点：
1. 必须在 import main 之前塞好环境变量；
   因为 services/llm_client.py 是在「模块导入时」就读取 .env 并创建客户端的，
   Key 为空它会直接 raise ValueError，测试根本跑不起来。
   load_dotenv() 默认不覆盖已存在的环境变量，所以这里先塞占位值就足够安全。
2. 这里用的都是假 Key，只为了让 OpenAI() 能构造成功，不会真的联网。
"""

import os
import sys
from pathlib import Path

# ---- 1. 先把 backend/ 加进 sys.path，测试里才能写 from database import ... ----
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ---- 2. 占位环境变量（必须在 import main 之前）----
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-not-real")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ.setdefault("OPENAI_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("EMBED_MODEL", "text-embedding-v3")
os.environ.setdefault("CHAT_MODEL", "deepseek-chat")

# ---- 3. 测试期间不许联网 ----
#    临时关闭代理，避免有人在本地配了代理时请求真的被打出去
for _var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_var, None)

import pytest
from fastapi.testclient import TestClient

from main import app


# ============ 假的外部依赖（替代真实网络调用）============

def fake_embed(texts, batch_size: int = 64):
    """假的 Embedding：给每段文字一个 8 维确定向量。

    不联网、可复现：同样的文本永远得到同样的向量，
    所以「提问文本 == 片段文本」时相似度一定是 1.0，便于断言检索行为。
    """
    vectors = []
    for index, text in enumerate(texts):
        base = float((len(text) + index) % 7 + 1) / 10
        vectors.append([base] * 8)
    return vectors


def fake_chat(messages, temperature: float = 0.2):
    """假的 RAG 生成回答：返回一段固定文本，不联网"""
    return "这是测试用的假回答。"


@pytest.fixture()
def client():
    """FastAPI 测试客户端（一个用例一个，互不影响）"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def rag():
    """取到 lifespan 里建好的 RAG 实例"""
    return app.state.rag_service


@pytest.fixture()
def no_network(monkeypatch):
    """把会联网的两处替换成假的：
    - services.rag.rag.embed  → 建索引 / 检索时的向量化
    - services.rag.rag.chat   → RAG 生成回答
    注意 rag.py 用的是 `from .llm import chat, embed`，
    所以必须打到 services.rag.rag 这个模块上，而不是 services.rag.llm。
    """
    from services.rag import rag as rag_module

    monkeypatch.setattr(rag_module, "embed", fake_embed)
    monkeypatch.setattr(rag_module, "chat", fake_chat)
    return monkeypatch


@pytest.fixture()
def clean_db():
    """每个用例开始前清空两张表，保证用例之间不互相干扰"""
    from database import get_db, init_db

    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM analysis_records")
        conn.execute("DELETE FROM documents")
        conn.commit()


@pytest.fixture()
def fake_json_out(monkeypatch):
    """让结构化分析走假模型，返回一份「结构完全正确」的结果。

    用法：
        def test_xxx(client, fake_json_out):
            fake_json_out({"summary": "..."})   # 想让它返回什么就传什么
    """
    from services import llm_service

    def _install(payload: dict):
        async def _fake(document: str) -> dict:
            return payload

        monkeypatch.setattr(llm_service, "json_out", _fake)
        # 上面改的是模块属性；api/analysis.py 是 `from ... import json_out`，
        # 已经绑定了旧函数，所以还要改它自己命名空间里的那份
        import api.analysis as analysis_module

        monkeypatch.setattr(analysis_module, "json_out", _fake)
        return payload

    # 提供一个「默认正确结果」，不调用也能用
    _install(
        {
            "summary": "假摘要",
            "key_points": ["要点一"],
            "keywords": ["关键词"],
            "action_items": ["待办一"],
            "questions": ["追问一"],
        }
    )
    return _install


def add_document(content: str = "FastAPI 是一个现代的 Python Web 框架。", filename: str = "demo.md") -> int:
    """直接往数据库塞一份文档，返回 document_id（不经过上传接口，方便单独测某个错误）"""
    from database import get_db

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (filename, file_type, content) VALUES (?, ?, ?)",
            (filename, filename.rsplit(".", 1)[-1], content),
        )
        conn.commit()
        return cursor.lastrowid
