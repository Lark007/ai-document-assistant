# 给 RAG 提供统一的 LLM 调用入口。
# 说明：Day 22 整理时把原来的 rag/config.py 合并进来了——它只有 5 个环境变量，
#       而这里是唯一读这些变量的地方，分成两个文件反而要多跳一次。
#       合并后，原来写 `from . import config` 的地方改成直接用本模块的常量。
from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

# 加载 backend/.env 里的变量
load_dotenv()

# ============ 环境变量（原来在 rag/config.py） ============
# 阿里云百炼的 Key 优先，兼容早期已经配成 OPENAI_API_KEY 的情况
API_KEY = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-v3")
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-chat")

# 预留：重排模型的配置。当前检索流程还没有接重排，先留着不删。
RERANK_MODEL = os.getenv("RERANK_MODEL", "gte-rerank-v2")
RERANK_URL = os.getenv("RERANK_URL", "")

_client: OpenAI | None = None

# 创建 OpenAI 客户端
def client() -> OpenAI:
    """懒加载单例，避免 import 时就要求环境变量齐全。"""
    global _client
    if _client is None:
        if not API_KEY:
            raise RuntimeError("缺少 OPENAI_API_KEY，请检查 .env")
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


def embed(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """把一批文本转成向量。分批是为了避免单次请求体过大。默认一次发 64 个向量过去。"""
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = client().embeddings.create(model=EMBED_MODEL, input=batch)
        out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
    return out


# 进行对话
def chat(messages: list[dict], temperature: float = 0.2) -> str:
    resp = client().chat.completions.create(
        model=CHAT_MODEL, messages=messages, temperature=temperature
    )
    return resp.choices[0].message.content or ""
