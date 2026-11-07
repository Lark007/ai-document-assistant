# services/agent/agent.py
"""最小 Agent 循环：调模型 → 看它要不要用工具 → 执行 → 结果回填 → 再调，最多 3 轮。"""

import json
import logging
import re

from services.agent.registry import tools_schema, available_functions
from services.llm_client import client, model_name

logger = logging.getLogger(__name__)

MAX_ROUNDS = 3          # 计划要求 2~3 轮，给个上限防止模型反复调工具烧钱

SYSTEM_PROMPT = """你是一个文档助手，可以调用工具来查资料。
- 用户按文件名提问（例如「doc.md 讲了什么」）或者你不确定有哪些文档时，先调用 list_documents 拿到编号，再用编号去检索或总结，不要拿文件名当关键词乱搜。
- 不确定有哪些文档时，先用 search_documents 查一下。
- 用户问某份文档「主要内容是什么」「讲了什么」这类整体性问题时，用 summarize_document 按编号取整篇，而不是只检索几个片段。
- 需要通读一整份文档时用 summarize_document。
- 用户要求对比两份文档时用 compare_documents。
- 资料里没有的内容不要编造；工具返回错误时，把情况如实告诉用户。
"""


async def run_agent(user_message: str, rag) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    used_tools = []          # 记录调用过哪些工具，返回给前端 / 方便调试

    for _ in range(MAX_ROUNDS):
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature=0.1,
        )
        message = response.choices[0].message

        # 没有工具调用 → 这就是最终回答，收敛
        if not message.tool_calls:
            return {
                "answer": message.content or "（模型没有返回内容）",
                "tool_calls": used_tools,
            }

        # 有工具调用：先把这条 assistant 消息放进历史（顺序不能反）
        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            used_tools.append(name)

            # ① 参数解析要防住非法 JSON（模型真的会给空串）
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                logger.warning("Agent 工具参数不是合法 JSON（工具 %s）：%r", name, tool_call.function.arguments)
                result = f"错误：参数不是合法 JSON（收到 {tool_call.function.arguments!r}），请重新给出参数。"
            else:
                func = available_functions.get(name)
                if not func:
                    logger.warning("Agent 调用了不存在的工具：%s", name)
                    result = (
                        f"错误：没有名为 {name} 的工具。"
                        f"可用的工具是：{', '.join(available_functions)}"
                    )
                else:
                    # ② 工具是 async，必须 await；参数按签名传
                    try:
                        result = await func(args, rag)
                    except Exception as e:
                        # 意外异常统一在这里兜住，转成文字让模型知道
                        logger.exception("Agent 工具 %s 执行出错", name)
                        result = f"函数执行出错：{type(e).__name__}: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

    # 轮数用完还没收敛 → 再问一次，但这次不给工具，强制它给结论
    messages.append({
        "role": "user",
        "content": (
            "本轮不能再调用任何工具了，工具调用也不会被处理。"
            "请只根据上面已经拿到的工具结果，用中文直接回答我最初的问题；"
            "如果这些结果不足以回答，就说明缺什么信息。"
            "不要输出任何工具调用的标记或代码块。"
        ),
    })
    final = client.chat.completions.create(
        model=model_name, messages=messages, temperature=0.1
    )
    return {
        "answer": _clean_answer(final.choices[0].message.content),
        "tool_calls": used_tools,
    }


def _clean_answer(text: str | None) -> str:
    """收尾回答的兜底清理：切掉模型自己写出来的「伪工具调用」文字。

    为什么需要：轮数用完后的那次调用不带 tools 参数，但上面的 messages 里
    还有助手请求调用工具的记录，模型有时会把本该由协议生成的调用片段
    （形如 <||DSML|| invoke name="search_documents">）当普通文字输出。
    这里只做展示层的清理，不影响 tool_calls 的统计。
    """
    text = (text or "").strip()
    if not text:
        return "（工具调用轮数已达上限，请换个更具体的问题再问一次）"

    # 从第一个「伪工具标记」处整体截断，保留它前面的正常回答。
    # 同时兼容半角 < > 和全角 ＜ ＞（模型两种都可能输出）
    match = re.search(r"[<＜][^>＞]*?(?:DSML|invoke|tool_calls|parameter)[^>＞]*[>＞]",
                      text, re.IGNORECASE)
    if match:
        text = text[:match.start()].strip()
        logger.warning("收尾回答里出现了伪工具调用标记，已截断（原长 %d 字）", len(match.string))

    return text or "（工具调用轮数已达上限，请换个更具体的问题再问一次）"