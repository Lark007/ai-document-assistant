# rag/config.py
#
# Day 22 整理说明：这里原本放 RAG 用到的 5 个环境变量。
# 后来发现读这些变量的地方只有 services/rag/llm.py 一个文件，
# 于是把变量搬进了 llm.py（少一次跳转），这里改成**只做转发的兼容入口**。
#
# 为什么还留着这个文件：一是项目里已经有人习惯了 `from . import config` 这种写法，
# 留着不会突然报 ModuleNotFoundError；二是环境变量的**说明**保留在这里，
# 想知道 RAG 用哪些变量、默认值是什么，看这个文件就够了。
#
# 值只有一份，就是 llm.py 里那份，所以这里不会出现「两处默认值不一致」的问题。
# 用相对导入，不管从哪个目录启动都不会出问题
from .llm import (  # noqa: F401
    API_KEY,
    BASE_URL,
    CHAT_MODEL,
    EMBED_MODEL,
    RERANK_MODEL,
    RERANK_URL,
)

__all__ = [
    "API_KEY",
    "BASE_URL",
    "EMBED_MODEL",
    "CHAT_MODEL",
    "RERANK_MODEL",
    "RERANK_URL",
]
