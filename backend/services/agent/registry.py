#  工具“注册中心”,保存工具说明书和注册
# 导入所有工具函数  
from services.agent.tools import *                     # 改后

# 💡 1. 函数路由表（用于实际执行）
available_functions = {
# 名字 → 函数，循环里用 TOOL_FUNCS[name](args, rag) 调用
    "list_documents": list_documents,
    "search_documents": search_documents,
    "summarize_document": summarize_document,
    "compare_documents": compare_documents,
}

# 💡 2. 工具说明书
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "list_documents",
            # description 要写「什么时候用它」，模型就是靠这句话选工具的
            "description": "列出文档库里所有文档的编号和文件名。当用户按文件名提问（例如「doc.md 讲了什么」）或者你不知道有哪些文档时，先调用它拿到编号。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "在文档库里检索相关片段。当用户问『哪份文档提到过 X』『帮我找一下 X』时用它。它只返回原文片段，不生成答案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索用的关键词或问题"},
                    "document_id": {"type": "integer", "description": "可选。只在某一份文档里检索时填，编号从 list_documents 拿"},
                    "filename": {"type": "string", "description": "可选。用户报的是文件名时填（可以是文件名的一部分），会自动翻译成文档编号"},
                    "top_k": {"type": "integer", "description": "可选。返回几条，默认 3，最多 10"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_document",
            "description": "把一整份文档总结成摘要、关键点和关键词。用户问某份文档『主要内容是什么』『讲了什么』时用它。注意：它按编号取整篇，不是检索；编号从 list_documents 拿。",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "integer", "description": "要总结的文档 id"},
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_documents",
            "description": "比较两份文档的相同点和不同点。当用户说『比较文档 1 和文档 2』『这两份 JD 哪个更适合我』时用它。",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id_a": {"type": "integer", "description": "第一份文档 id"},
                    "document_id_b": {"type": "integer", "description": "第二份文档 id"},
                    "aspect": {"type": "string", "description": "可选。只比较某个方面，例如「技术要求」"},
                },
                "required": ["document_id_a", "document_id_b"],
            },
        },
    },
]

