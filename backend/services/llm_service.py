# 提供调用大模型的各种使用接口

import json
import logging
from fastapi import HTTPException
from pydantic import ValidationError
from services.prompts import PROMPT
from services.llm_client import client, model_name
from schemas.schemas import DocumentAnalysis

logger = logging.getLogger(__name__)

async def json_out(document: str) -> dict:
    """调用大模型，完成格式化输出"""

    # 获取 Prompt 模板
    prompt = PROMPT["json_out"]

    try:
        # 调用大模型
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": prompt["system_prompt"]},
                {"role": "user", "content": prompt["user_prompt"] + document}
            ],
            response_format={
                'type': 'json_object'
            }
        )
        raw_text = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("调用大模型失败（模型 %s）：%s", model_name, e)
        raise HTTPException(status_code=500, detail=f"大模型调用失败: {str(e)}")

    # 清洗 Markdown 代码块（防止模型不听话加了 ```json）
    if raw_text.startswith("```"):
        # 去掉首尾的 ``` 和 ```json
        raw_text = raw_text.strip("`").replace("json", "", 1).strip()

    # 解析 JSON
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error("模型返回的不是合法 JSON（前 200 字）：%s", raw_text[:200])
        raise HTTPException(
            status_code=500,
            detail="大模型返回的不是合法 JSON，请检查 Prompt 或降低 temperature"
        )

    # Pydantic 校验
    try:
        # 核心：用 Pydantic 模型校验数据
        analysis = DocumentAnalysis(**data)
        return analysis.model_dump()  # 转回字典返回给前端
    except ValidationError as e:
        # 关键：不要直接把原始异常堆栈抛给前端
        # 提取清晰的错误信息，告诉前端哪个字段校验失败
        error_details = []
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            error_details.append(f"字段 [{field}]: {error['msg']}")

        logger.error("模型输出结构校验失败：%s", "; ".join(error_details))
        raise HTTPException(
            status_code=500,
            detail=f"模型输出结构校验失败: {'; '.join(error_details)}"
        )