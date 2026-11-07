from __future__ import annotations

import logging
from fastapi import Path
from .llm import chat, embed
from .splitter import *
from .store import Hit, VectorStore

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """你是一个严谨的问答助手。请严格依据下面提供的资料回答问题。
如果资料中没有相关信息，就直接回答"资料中没有提到"，不要编造。

资料：
{context}

问题：{question}
"""


class RAG:
    def __init__(self, chunk_size: int = 500, overlap: int = 80, top_k: int = 3):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.top_k = top_k
        self.store = VectorStore()

    # ---------- 写入侧 ----------
    def index_text(self, text: str, source: str = "") -> int:
        """切片 + 索引。先删后加，返回chunk切成几段"""
        # 1. 如果这个 source 之前索引过，先清掉旧的
        if source:
            removed = self.store.remove_by_source(source)
            if removed:
                logger.info("清理旧索引：%s 删除 %d 个片段", source, removed)

        # 2. 切块
        chunks = split_text_line(text, self.chunk_size, self.overlap)
        if not chunks:
            return 0

        # 3.入库
        # batch_size 就是一次 API 请求里，最多塞几条文本,
        # 阿里云百炼, 单次最多 10 条
        self.store.add(chunks, embed(chunks, 10), source)
        return len(chunks)

    # ---------- 读取侧 ----------
    def retrieve(self, question: str, top_k: int | None = None, source_filter: str | None = None) -> list[Hit]:
        """召回：根据问题，检索相关的文本块，返回最相似的文本块列表。
            可指定 source_filter 限定在单文档内检索。"""
        return self.store.search(embed([question])[0], top_k or self.top_k, source_filter)


    def answer(self, question: str, top_k: int | None = None, source_filter: str | None = None) -> str:
        """生成：根据问题，检索相关的文本块，并调用 LLM 生成答案"""
        hits = self.retrieve(question, top_k, source_filter)
        if not hits:
            if source_filter:
                return f"（文档「{source_filter}」尚未建立索引，请先索引）"
            return "（知识库为空，请先索引文档）"
        # 把检索到的文本块拼成一个上下文，传给 LLM
        # enumerate 会给 hits 列表编号，i 从 0 开始
        context = "\n\n".join(f"[{i + 1}] {h.text}" for i, h in enumerate(hits))
        return chat([{"role": "user",
                        "content": PROMPT_TEMPLATE.format(context=context, question=question)}])

    def answer_with_references(self, question: str, top_k: int | None = None, source_filter: str | None = None) -> dict:
        """生成：根据问题，检索相关的文本块，并调用 LLM 生成答案，并且返回命中的信息"""
        hits = self.retrieve(question, top_k, source_filter)
        if not hits:
            if source_filter:
                return {"answer": f"（文档「{source_filter}」尚未建立索引，请先索引）",
                        "references": []}
                # return f"（文档「{source_filter}」尚未建立索引，请先索引）"
            return {"answer": "（知识库为空，请先索引文档）",
                    "references": []}
            # return "（知识库为空，请先索引文档）"
        # 把检索到的文本块拼成一个上下文，传给 LLM
        # enumerate 会给 hits 列表编号，i 从 0 开始
        context = "\n\n".join(f"[{i + 1}] {h.text}" for i, h in enumerate(hits))
        answer  = chat([{"role": "user",
                        "content": PROMPT_TEMPLATE.format(context=context, question=question)}])
        references = [
            {"text": h.text, "score": round(h.score, 4), "source": h.source}
            for i, h in enumerate(hits)
        ]

        return {"answer": answer, "references": references}

    # ---------- 索引持久化 ----------
    # 保存
    def save_index(self, path: str | Path) -> None:
        self.store.save(path)
        logger.info("索引已保存到 %s，当前 %d 个片段", path, len(self.store))

    # 加载
    def load_index(self, path: str | Path) -> bool:
        return self.store.load(path)

    def has_source(self, source: str) -> bool:
        """这个文件索引过没有"""
        return source in self.store.sources

