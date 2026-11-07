# 向量存储

# 启用“延迟注解求值”。让 Python 把类型注解（如 np.ndarray）当成字符串处理，而不是在代码运行时立刻求值。
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import json


@dataclass
class Hit:
    text: str
    score: float
    source: str = ""

# 对一批向量做 L2 归一化
def _normalize(m: np.ndarray) -> np.ndarray:
    # 得到每一行的向量长度
    # 假设 m 是 3 行 4 列（3 个 4 维向量），
    # axis=1 会算出 3 个长度，keepdims=True 让结果变成 3 行 1 列，这样才能和 3 行 4 列的 m 逐行相除
    norm = np.linalg.norm(m, axis=1, keepdims=True)
    # 避免除以 0
    norm[norm == 0] = 1e-10
    # 每一行除以它的长度，得到单位向量
    return m / norm

"""向量库：内存里的一个矩阵 + 一堆原文。
    向量库类方法：入库、查询"""
class VectorStore:

    def __init__(self) -> None:
        self.vectors: np.ndarray | None = None
        self.chunks: list[str] = []
        self.sources: list[str] = []

    # 添加向量和对应的文本块
    def add(self, chunks: list[str], vectors: list[list[float]], source: str = "") -> None:
        # 把传入的 vectors（Python 列表）转换成 NumPy 数组，并指定数据类型为 float32
        v = np.asarray(vectors, dtype=np.float32)
        if v.size == 0:
            return
        # 对 v 的每一行做 L2 归一化
        v = _normalize(v)
        # 把已有的向量和新向量垂直堆叠起来
        self.vectors = v if self.vectors is None else np.vstack([self.vectors, v])
        self.chunks.extend(chunks)
        self.sources.extend([source] * len(chunks))

    # 查询向量库，返回最相似的文本块
    def search(self, query_vector: list[float], top_k: int = 3, source_filter: str | None = None) -> list[Hit]:
        if self.vectors is None:
            return []
        q = _normalize(np.asarray([query_vector], dtype=np.float32))[0]
        scores = self.vectors @ q          # 向量已归一化，点积 == 余弦相似度

        # 单文档过滤：把不属于该 source 的分数置为 -inf，天然排到最后
        if source_filter is not None:
            mask = np.array([s == source_filter for s in self.sources])
            if not mask.any():
                return []  # 该 source 一个 chunk 都没索引过
            candidates = np.flatnonzero(mask)   # 只保留命中的下标
            order = np.argsort(-scores[candidates])[:top_k] # 在候选里排序
            idx = candidates[order]
        else:
            idx = np.argsort(-scores)[:top_k]

        return [Hit(self.chunks[i], float(scores[i]), self.sources[i]) for i in idx]

    # 返回向量库中有多少个文本块
    def __len__(self) -> int:
        return len(self.chunks)

# ============ 持久化 ============
    def save(self, directory: str | Path) -> None:
        """把索引写到磁盘。"""
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)

        # 向量存成 .npy（numpy 原生格式）
        if self.vectors is not None:
            np.save(d / "vectors.npy", self.vectors)

        # chunks 和 sources 一起存成 JSON
        meta = {"chunks": self.chunks, "sources": self.sources}
        (d / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False), encoding="utf-8"
        )

    def load(self, directory: str | Path) -> bool:
        """从磁盘加载索引。返回 True 表示加载成功，False 表示磁盘上没有。"""
        d = Path(directory)
        vectors_path = d / "vectors.npy"
        meta_path = d / "meta.json"

        if not vectors_path.exists() or not meta_path.exists():
            return False

        self.vectors = np.load(vectors_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.chunks = meta["chunks"]
        self.sources = meta["sources"]

        # 防御性校验：三者数量必须一致，否则索引已损坏
        if len(self.chunks) != len(self.sources) or self.vectors.shape[0] != len(self.chunks):
            raise ValueError("索引文件损坏：chunks / sources / vectors 数量不一致")

        return True

    def remove_by_source(self, source: str) -> int:
        """删除某个 source 的所有 chunk。返回删除的数量。"""
        if not self.sources:
            return 0

        # 找出要保留的下标
        keep = [i for i, s in enumerate(self.sources) if s != source]
        removed = len(self.sources) - len(keep)
        if removed == 0:
            return 0

        # chunks 和 sources 用列表推导过滤
        self.chunks = [self.chunks[i] for i in keep]
        self.sources = [self.sources[i] for i in keep]

        # 向量矩阵用 numpy 的 fancy indexing 按行过滤
        if self.vectors is not None:
            if keep:
                self.vectors = self.vectors[keep]
            else:
                self.vectors = None

        return removed