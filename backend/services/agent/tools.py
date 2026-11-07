# services/agent/tools.py
"""Agent 的四个工具函数。

约定（三个函数都遵守）：
1. 入参 args 是 dict，来自模型返回的 tool_calls，内容不可信，必须校验；
2. 返回 str，这段文字会被塞回模型；
3. 业务错误（参数不对 / 找不到 / 没结果）返回一句说明，不要抛异常；
   网络或模型报错这类意外异常，交给外面的 Agent 循环统一兜底。
"""

from database import get_db
from services.llm_service import json_out
from services.rag.llm import chat


def _as_int(value):
    """模型经常把数字写成字符串（"1" 而不是 1），统一转一下；转不了返回 None"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_document(document_id):
    """按 id 取一份文档；取不到返回 None"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename, content FROM documents WHERE id = ?",
            (document_id,),
        )
        return cursor.fetchone()


def _find_documents_by_name(filename):
    """按文件名模糊查找，返回 [(id, filename), ...]，最多 10 条。

    用户说的文档名往往不完整（少写扩展名、少几个字），所以用 LIKE 模糊匹配。
    """
    keyword = str(filename or "").strip()
    if not keyword:
        return []

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, filename FROM documents WHERE filename LIKE ? ORDER BY id LIMIT 10",
            (f"%{keyword}%",),
        )
        return [(row["id"], row["filename"]) for row in cursor.fetchall()]


async def list_documents(args: dict, rag) -> str:
    """列出文档库里所有文档的「编号 + 文件名」。

    为什么需要它：用户经常按文件名提问（「doc.md 讲了什么」），但工具参数
    只认编号，模型猜不出编号就会到处乱搜。有了这份清单，模型能自己把
    文件名对应到编号，再去调 search_documents / summarize_document。
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, LENGTH(content) AS length FROM documents ORDER BY id")
        rows = cursor.fetchall()

    if not rows:
        return "文档库里还没有任何文档，请先上传。"

    lines = [f"共 {len(rows)} 份文档："]
    for row in rows:
        lines.append(f"- 文档 {row['id']}：{row['filename']}（{row['length']} 字）")
    return "\n".join(lines)


async def search_documents(args: dict, rag) -> str:
    """在文档库里检索相关片段。只返回片段，不生成答案。"""
    # ---- 参数校验 ----
    query = str(args.get("query") or "").strip()
    if not query:
        return "错误：缺少参数 query（要检索的关键词或问题）。"

    top_k = _as_int(args.get("top_k")) or 3
    top_k = max(1, min(top_k, 10))          # 别让模型一次要 1000 条

    source_filter = None                    # None = 在所有文档里找
    if args.get("document_id") is not None:
        document_id = _as_int(args.get("document_id"))
        if document_id is None:
            return (f"错误：document_id 必须是整数，收到的是 {args.get('document_id')!r}。"
                    "如果这是文件名，请改用 filename 参数，或先调用 list_documents 拿到编号。")
        if not _get_document(document_id):
            return f"错误：文档 {document_id} 不存在。文档列表可以用 list_documents 查。"
        source_filter = str(document_id)
    elif args.get("filename"):
        # 用户/模型报的是文件名（可能只写了一半）→ 先翻译成编号
        matches = _find_documents_by_name(args["filename"])
        if not matches:
            return f"错误：没有文件名包含「{args['filename']}」的文档，请调用 list_documents 查看有哪些文档。"
        if len(matches) > 1:
            names = "、".join(f"文档 {i}（{n}）" for i, n in matches)
            return f"「{args['filename']}」匹配到多份文档：{names}。请改用 document_id 指明是哪一份。"
        source_filter = str(matches[0][0])

    # ---- 真正干活：复用你已经写好的检索 ----
    hits = rag.retrieve(query, top_k, source_filter)
    if not hits:
        return f"没有检索到和「{query}」相关的内容。"

    # ---- 拼成一段模型能读懂的文本 ----
    parts = []
    for i, hit in enumerate(hits, 1):
        # hit.source 里存的是 document_id 字符串，换成文件名更好读
        doc = _get_document(_as_int(hit.source))
        name = doc["filename"] if doc else f"文档 {hit.source}"
        parts.append(f"[{i}] 来源：{name}（文档 {hit.source}，相似度 {hit.score:.2f}）\n{hit.text}")

    return "\n\n".join(parts)


async def summarize_document(args: dict, rag) -> str:
    """把某一份文档总结成摘要 + 关键点 + 关键词。"""
    document_id = _as_int(args.get("document_id"))
    if document_id is None:
        return "错误：缺少参数 document_id（要总结哪份文档）。可以先调用 search_documents 查一下有哪些文档。"

    doc = _get_document(document_id)
    if not doc:
        return f"错误：文档 {document_id} 不存在。"

    # 复用你分析接口里那套：结构化输出 + Pydantic 校验
    result = await json_out(doc["content"])

    lines = [
        f"《{doc['filename']}》（文档 {document_id}）",
        f"摘要：{result['summary']}",
        "关键点：" + ("；".join(result["key_points"]) or "无"),
        "关键词：" + ("、".join(result["keywords"]) or "无"),
    ]
    return "\n".join(lines)

COMPARE_PROMPT = """请比较下面两份文档{aspect_part}。

【文档 A：{name_a}】
{content_a}

【文档 B：{name_b}】
{content_b}

请严格按这个格式回答，不要编造文档里没有的内容：
1. 相同点：...
2. 不同点：...
3. 结论：...（一句话）"""


async def compare_documents(args: dict, rag) -> str:
    """比较两份文档的某个方面。"""
    id_a = _as_int(args.get("document_id_a"))
    id_b = _as_int(args.get("document_id_b"))

    if id_a is None or id_b is None:
        return "错误：需要 document_id_a 和 document_id_b 两个参数。"
    if id_a == id_b:
        return f"错误：两个 id 相同（都是 {id_a}），请给两份不同的文档。"

    doc_a = _get_document(id_a)
    if not doc_a:
        return f"错误：文档 {id_a} 不存在。"
    doc_b = _get_document(id_b)
    if not doc_b:
        return f"错误：文档 {id_b} 不存在。"

    aspect = str(args.get("aspect") or "").strip()
    prompt = COMPARE_PROMPT.format(
        aspect_part=f"的{aspect}" if aspect else "",
        name_a=doc_a["filename"],
        content_a=doc_a["content"][:6000],   # 先各截 6000 字，避免两份长文档一起超上下文
        name_b=doc_b["filename"],
        content_b=doc_b["content"][:6000],
    )
    return chat([{"role": "user", "content": prompt}])