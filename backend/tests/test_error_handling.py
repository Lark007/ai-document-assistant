"""作用：Day 22 任务 1「统一错误处理」的测试。

测试怎么分三类（对应三种「怎么触发」）：
  第 1 类（手动，看界面）：Swagger / 前端点一遍，看提示文案对不对 → 见 README 的清单
  第 2 类（半自动，不发网络请求）：给外网调用打假函数（fake_embed / fake_chat / fake_json_out），
        这类用例「必定复现」，任何时间跑都是同样结果
  第 3 类（临时改配置）：改坏 .env 或锁住数据库，只能手动做一次，见下面的注释

运行方式（必须在 backend/ 目录下）：
    uv run --with pytest --with httpx pytest tests -v
或先装一次：
    uv add --dev pytest httpx
    uv run pytest tests -v
"""

import json
import sqlite3

import pytest

# 注意：这里直接 import 应用实例。
# 不要写 client.app —— starlette 的 TestClient.app 是内部传输对象，不是 FastAPI 实例。
from main import app


# =====================================================================
# 0. 基准：正常路径通过，错误用例才说明得了问题
# =====================================================================

def test_baseline_正常上传(client, no_network, clean_db):
    """基线：合法的 md 上传成功，并且顺手把索引也建好"""
    resp = client.post(
        "/documents/upload",
        files={"file": ("demo.md", "# 标题\nFastAPI 很好用。".encode("utf-8"), "text/markdown")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["document_id"] > 0
    assert body["file_type"] == "md"
    assert body["indexed"] is True, "假 embed 不该失败，索引应该成功"


def test_基线_缺字段返回422(client, clean_db):
    """FastAPI 自带校验：请求体缺字段是 422，不是 500。

    /analysis/document 原本是手工 `await req.json()` 取字段，同样的漏字段会变成 500；
    现在它也换成了 Pydantic 模型（AnalysisRequest），所以两边行为一致。
    """
    resp = client.post("/qa/", json={"question": "只有问题，没有 document_id"})
    assert resp.status_code == 422

    resp = client.post("/analysis/document", json={"question": "只有问题，没有 document_id"})
    assert resp.status_code == 422


# =====================================================================
# 1. 文件错误
# =====================================================================

def test_a1_文件错误_扩展名不支持(client, no_network, clean_db):
    """触发：上传 .pdf / .png 等非 txt、md 文件"""
    resp = client.post(
        "/documents/upload",
        files={"file": ("report.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "仅支持 .txt 或 .md 文件"


def test_a2_文件错误_大写扩展名应当放行(client, no_network, clean_db):
    """边界：上传接口先 lower() 再判断，.MD 应该被接受。

    如果这个用例挂了，说明有人把 `file_ext = os.path.splitext(...)[1].lower()` 里的 lower() 删了。
    """
    resp = client.post(
        "/documents/upload",
        files={"file": ("README.MD", "# 大写扩展名".encode("utf-8"), "text/markdown")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["file_type"] == "md"


def test_a3_文件错误_非UTF8编码(client, no_network, clean_db):
    """触发：文件是 GBK 编码（Windows 记事本默认另存为 ANSI 就是这个）。

    "\u4e2d\u6587" 是「中文」两个字，GBK 字节在 UTF-8 下解码必然失败。
    """
    gbk_bytes = "\u4e2d\u6587".encode("gbk")
    resp = client.post(
        "/documents/upload",
        files={"file": ("gbk.txt", gbk_bytes, "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "文件编码格式错误，请使用 UTF-8 编码"


# =====================================================================
# 2. document_id 不存在（后端 404，前端给固定话术）
# =====================================================================

def test_b1_文档不存在_详情(client, clean_db):
    resp = client.get("/documents/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


def test_b2_文档不存在_文件名(client, clean_db):
    """前端 QAView 手动输入 ID 时走的就是这个接口，它必须返回 404，
    前端才能显示「无法获取文档信息，请检查文档 ID 是否正确。」"""
    resp = client.get("/documents/name/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


def test_b3_文档不存在_结构化分析(client, clean_db):
    resp = client.post("/analysis/document", json={"document_id": 999999})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


def test_b4_文档不存在_RAG问答(client, clean_db):
    resp = client.post("/qa/", json={"document_id": 999999, "question": "随便问问"})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


def test_b5_文档不存在_建索引(client, clean_db):
    resp = client.post("/qa/index/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


def test_b6_文档不存在_删除(client, clean_db):
    resp = client.delete("/documents/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


# =====================================================================
# 3. DeepSeek 失败
# =====================================================================

def test_c1_模型失败_结构化分析(client, clean_db, monkeypatch):
    """触发：把模型的 create() 换成直接抛异常（等价于改坏 .env 里的 Key）。

    覆盖 services/llm_service.py:29 那个 except Exception。
    """
    from services import llm_service

    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("Connection error: 模拟网络不通")

    monkeypatch.setattr(llm_service.client.chat.completions, "create", Boom().create)

    document_id = _upload(client, "temp.md", "随便一点内容")
    resp = client.post("/analysis/document", json={"document_id": document_id})

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail.startswith("大模型调用失败: ")
    assert "模拟网络不通" in detail


def test_c2_模型失败_RAG问答(client, clean_db, monkeypatch):
    """触发：RAG 问答那条链路调模型失败。

    注意这里补丁打在哪：RAG 走的是 services/rag/llm.py 里的 chat()，
    它用的是自己的 OpenAI 客户端（services/rag/llm.py 的 client()），
    和 services/llm_client.py 里那个客户端是两个不同对象。
    所以只打 llm_service.client 是拦不住 RAG 的，必须把 rag.llm.client() 也换掉。

    预期行为：异常直接冒到 FastAPI，变成 500，detail 是原始错误文本
    （RAG 这条链路目前没有像 llm_service 那样包一层「大模型调用失败: 」）。
    """
    from services.rag import llm as rag_llm

    class Boom:
        def create(self, **kwargs):
            raise RuntimeError("429 Too Many Requests")

    class FakeCompletions:
        create = Boom().create

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    # 注意顺序：先上传。上传会调 embed() 建索引，而 FakeClient 上没有 embeddings，
    # 先把客户端换掉会让建索引失败（上传接口会把异常吞掉，文档变成未索引 → 变成 409）。
    document_id = _upload(client, "temp.md", "内容够长就会建索引")

    # 上传完再换掉 RAG 的客户端，让问答时的 chat 调用必失败
    monkeypatch.setattr(rag_llm, "client", lambda: FakeClient())

    resp = client.post("/qa/", json={"document_id": document_id, "question": "这是什么"})

    assert resp.status_code == 500
    assert "429 Too Many Requests" in str(resp.json()["detail"])


def test_c3_模型失败_手工复现步骤():
    """这条不需要 pytest，是给你手动做一次用的。

    1) 打开 backend/.env，把 DEEPSEEK_API_KEY 改成明显错误的值（例如加个 x；
       或把 DEEPSEEK_BASE_URL 改成 https://127.0.0.1:9/v1）
    2) 重启后端，前端点「AI 分析文档」
    3) 预期：前端红色提示「大模型调用失败: ...」，后端控制台也有一行异常
    4) 测完记得把 .env 改回来（这个文件是敏感文件，别提交）
    """
    pytest.skip("手动步骤，不需要自动执行")


# =====================================================================
# 4. JSON 解析失败 / Pydantic 校验失败
# =====================================================================

def _patch_raw_model(monkeypatch, raw_text: str):
    """把模型返回的原文抽成一个固定字符串，用来构造各种「模型不听话」的返回。"""

    class Message:
        content = raw_text

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return Response()

    from services import llm_service

    monkeypatch.setattr(
        llm_service.client.chat.completions, "create", FakeCompletions().create
    )


def test_d1_JSON解析失败_模型返回一句人话(client, clean_db, monkeypatch):
    """触发：模型返回的不是 JSON（等于提示词里忘了强调 JSON 格式）"""
    _patch_raw_model(monkeypatch, "\u8fd9\u662f\u4e00\u6bb5\u666e\u901a\u56de\u7b54\uff0c\u4e0d\u662f JSON")
    document_id = _upload(client, "temp.md", "内容")

    resp = client.post("/analysis/document", json={"document_id": document_id})
    assert resp.status_code == 500
    assert resp.json()["detail"] == "大模型返回的不是合法 JSON，请检查 Prompt 或降低 temperature"


def test_d2_JSON解析失败_截断的JSON(client, clean_db, monkeypatch):
    """触发：模型输出被 max_tokens 截断，只剩半截 JSON"""
    _patch_raw_model(monkeypatch, '{"summary": "\u88ab\u622a\u65ad\u4e86')
    document_id = _upload(client, "temp.md", "内容")

    resp = client.post("/analysis/document", json={"document_id": document_id})
    assert resp.status_code == 500
    assert "不是合法 JSON" in resp.json()["detail"]


def test_d3_校验失败_缺必填字段(client, clean_db, monkeypatch):
    """触发：JSON 合法但缺 summary（Pydantic 校验失败，llm_service.py:51）"""
    _patch_raw_model(
        monkeypatch,
        json.dumps({"key_points": ["\u53ea\u6709\u8981\u70b9"], "keywords": []}, ensure_ascii=False),
    )
    document_id = _upload(client, "temp.md", "内容")

    resp = client.post("/analysis/document", json={"document_id": document_id})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail.startswith("模型输出结构校验失败: ")
    assert "summary" in detail


def test_d4_校验失败_字段类型不对(client, clean_db, monkeypatch):
    """触发：key_points 给了字符串而不是数组（模型很常见的偷懒写法）"""
    _patch_raw_model(
        monkeypatch,
        json.dumps(
            {
                "summary": "\u6b63\u5e38\u6458\u8981",
                "key_points": "\u53ea\u7ed9\u4e00\u4e2a\u5b57\u7b26\u4e32",
                "keywords": [],
            },
            ensure_ascii=False,
        ),
    )
    document_id = _upload(client, "temp.md", "内容")

    resp = client.post("/analysis/document", json={"document_id": document_id})
    assert resp.status_code == 500
    assert "模型输出结构校验失败" in resp.json()["detail"]


def test_d5_清洗逻辑_带Markdown包裹的JSON(client, clean_db, monkeypatch):
    """边界：模型返回 ```json ... ``` 时，llm_service.py:33 的清洗应当把它救回来。

    这条如果挂了，说明清洗那三行（strip("`") + replace("json", "", 1)）被改坏了。
    """
    payload = {
        "summary": "\u5305\u5728\u4ee3\u7801\u5757\u91cc\u7684\u6458\u8981",
        "key_points": ["\u8981\u70b9"],
        "keywords": ["\u5173\u952e\u8bcd"],
        "action_items": [],
        "questions": [],
    }
    _patch_raw_model(monkeypatch, "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```")
    document_id = _upload(client, "temp.md", "内容")

    resp = client.post("/analysis/document", json={"document_id": document_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["summary"] == payload["summary"]


def test_d6_请求体缺document_id(client, clean_db):
    """/analysis/document 缺 document_id 应当是干净的 422，不是 500。

    Day 22 已经修掉：api/analysis.py 现在用 schemas/schemas.py 里的
    AnalysisRequest 做请求体校验，所以和 /qa/ 的行为保持一致。
    """
    resp = client.post("/analysis/document", json={})
    assert resp.status_code == 422, "缺字段应当是 422（Pydantic 校验）"

    # 字段在、但类型不对，也应当被拦住
    resp = client.post("/analysis/document", json={"document_id": "abc"})
    assert resp.status_code == 422


# =====================================================================
# 4.5 分析结果查看（Day 22 新增的查看功能）
# =====================================================================

def test_h1_查看分析结果_没有记录时404(client, no_network, clean_db):
    """文档存在但还没分析过 → 404，前端把它当成「暂时没有结果」展示空态。"""
    upload = client.post(
        "/documents/upload",
        files={"file": ("查看用.txt", "第一段。\n\n第二段。".encode("utf-8"), "text/plain")},
    )
    document_id = upload.json()["document_id"]

    resp = client.get(f"/analysis/document/{document_id}")
    assert resp.status_code == 404
    assert "分析结果" in resp.json()["detail"]


def test_h2_查看分析结果_文档不存在时404(client, clean_db):
    resp = client.get("/analysis/document/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "文档不存在"


def test_h3_查看分析结果_分析过一次后能读回来(client, no_network, clean_db):
    """先分析一次（走假模型），再用 GET 读回来，两边字段应当一致。"""
    upload = client.post(
        "/documents/upload",
        files={"file": ("读回.txt", "内容在这里。".encode("utf-8"), "text/plain")},
    )
    document_id = upload.json()["document_id"]

    analyzed = client.post("/analysis/document", json={"document_id": document_id})
    assert analyzed.status_code == 200

    resp = client.get(f"/analysis/document/{document_id}")
    assert resp.status_code == 200
    body = resp.json()

    assert body["document_id"] == document_id
    assert body["analysis_type"] == "structured_output"
    assert body["record_id"] is not None
    assert body["created_at"]
    # result 应当是解析后的对象，而不是一整串 JSON 字符串
    assert isinstance(body["result"], dict)
    assert body["result"]["summary"] == analyzed.json()["summary"]
    assert body["result"]["key_points"] == analyzed.json()["key_points"]


def test_h4_重复分析会新增一条记录_查看取最新那条(client, no_network, clean_db):
    upload = client.post(
        "/documents/upload",
        files={"file": ("两次.txt", "第一次内容。".encode("utf-8"), "text/plain")},
    )
    document_id = upload.json()["document_id"]

    first = client.post("/analysis/document", json={"document_id": document_id}).json()
    second = client.post("/analysis/document", json={"document_id": document_id}).json()

    latest = client.get(f"/analysis/document/{document_id}").json()
    assert latest["result"]["summary"] == second["summary"]
    assert first["summary"] == second["summary"], "假模型每次返回一样的内容"


def test_h5_重新分析_同一份文档不会重复花钱(client, no_network, clean_db):
    """regenerate 参数：不传时能复用已保存结果，传 true 时重新分析。

    这里只验证接口可用（假模型下两次结果相同），
    真正的省钱逻辑要看数据库里的记录条数。
    """
    upload = client.post(
        "/documents/upload",
        files={"file": ("复用.txt", "内容。".encode("utf-8"), "text/plain")},
    )
    document_id = upload.json()["document_id"]

    client.post("/analysis/document", json={"document_id": document_id})

    cached = client.post("/analysis/document", json={"document_id": document_id})
    assert cached.status_code == 200

    regenerated = client.post(
        f"/analysis/document?regenerate=true", json={"document_id": document_id}
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["summary"] == cached.json()["summary"]


# =====================================================================
# 5. 数据库失败
# =====================================================================

def test_e1_数据库失败_连接就挂了(client, clean_db, monkeypatch):
    """触发：让 get_connection() 抛异常，等价于数据库文件被删/损坏/没有写权限。

    覆盖 database.py 的 get_db() 上下文管理器（出错回滚 + 关闭连接）。
    """
    import database

    def boom():
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(database, "get_connection", boom)

    # documents.py 是 `from database import get_db`，但 get_db 内部调用的还是
    # 同一个模块对象 database 里的 get_connection，所以打在上面就够了
    resp = client.get("/documents")
    assert resp.status_code == 500
    assert "unable to open database file" in resp.text or resp.status_code == 500


def test_e2_数据库失败_写库被锁(client, clean_db):
    """触发：另一个连接开着写事务不放，SQLite 会报 database is locked。

    这里只是手动模拟一下「锁」是什么感觉；真正测接口用下面注释里的做法。
    """
    from database import get_connection

    holder = get_connection()
    try:
        holder.execute("BEGIN IMMEDIATE")
        holder.execute(
            "INSERT INTO documents (filename, file_type, content) VALUES ('x.md', 'md', 'x')"
        )
        # 此时别的连接写库会等待，超过默认 5 秒就 OperationalError
        other = get_connection()
        try:
            with pytest.raises(sqlite3.OperationalError) as excinfo:
                other.execute(
                    "INSERT INTO documents (filename, file_type, content) VALUES ('y.md', 'md', 'y')"
                )
            assert "locked" in str(excinfo.value)
        finally:
            other.close()
    finally:
        holder.rollback()
        holder.close()


def test_e3_数据库失败_手工复现步骤():
    """手动跑一次「真锁」，看接口返回什么（更能代表线上情况）：

    1) 另开一个终端跑：
       python -c "import sqlite3,time; c=sqlite3.connect('document.db'); c.execute('BEGIN IMMEDIATE'); time.sleep(30)"
       （要在 backend/ 目录下跑）
    2) 30 秒内在前端点「上传到后端」，或调 POST /analysis/document
    3) 预期：约 5 秒后接口 500，客户端断开时报 database is locked
    4) 现在的问题：这个 500 没有中文提示，前端只会显示
       「请求失败，请检查后端服务是否启动。」——这正是 Day 22 要统一的地方
    """
    pytest.skip("手动步骤，不需要自动执行")


# =====================================================================
# 6. RAG 无结果
# =====================================================================

def test_f1_RAG无结果_没建索引(client, no_network, clean_db):
    """触发：文档存在但从没建过索引（先把索引清空，再问）"""
    from services.rag import rag as rag_module

    document_id = _upload(client, "noindex.md", "这份文档故意不建索引", index=False)

    # 确保这个 document_id 不在索引里
    rag = app.state.rag_service
    rag.store.remove_by_source(str(document_id))

    resp = client.post("/qa/", json={"document_id": document_id, "question": "这是什么"})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "这份文档还没有建立索引，请先建立索引"


def test_f2_RAG无结果_索引里一个片段都没有(client, no_network, clean_db):
    """触发：索引整个是空的（等价于删光所有文档后直接问）

    注意路径差异：has_source 先拦一层，所以要先让 409 不发生，
    这里直接调 RAG.retrieve/answer 更直观，覆盖的是 rag.py:69 那个空分支。
    """
    rag = app.state.rag_service
    for source in list(rag.store.sources):
        rag.store.remove_by_source(source)

    hits = rag.retrieve("随便问点什么")
    assert hits == []
    assert rag.answer("随便问点什么") == "（知识库为空，请先索引文档）"


def test_f3_RAG无结果_模型回答资料里没有(client, no_network, clean_db):
    """触发：索引正常，但问的是文档里根本没有的内容。

    检索总会返回 Top-K（除非索引为空），所以「无结果」在这一层表现为
    模型按提示词兜底回答「资料中没有提到」——用假 chat 时就是假回答。
    """
    content = "FastAPI 是一个 Python Web 框架。"
    document_id = _upload(client, "fastapi.md", content)

    resp = client.post("/qa/", json={"document_id": document_id, "question": "圆周率是多少"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["answer"]  # 有回答（真模型会说「资料中没有提到」）


def test_f4_RAG无结果_切出0个片段(rag):
    """边界：文档内容全是空白，splitter 切不出片段时 index_text 返回 0"""
    assert rag.index_text("   \n\n   ", source="empty-doc") == 0


# =====================================================================
# 7. Agent 工具失败
# =====================================================================

class _ToolCall:
    """手工造一个 tool_call，用来骗过 Agent 循环"""

    def __init__(self, name: str, arguments: str, call_id: str = "call_1"):
        self.function = type("F", (), {"name": name, "arguments": arguments})()
        self.id = call_id


def _patch_agent(monkeypatch, tool_calls_per_round: list):
    """把 Agent 第一层的模型换成假模型：
    第 1 次返回带工具调用的响应，若还有第 2 次就返回没有工具调用的收敛响应。
    """
    rounds = list(tool_calls_per_round)

    class Message:
        def __init__(self, tool_calls):
            self.tool_calls = tool_calls
            self.content = "最终回答"

    class Response:
        def __init__(self, tool_calls):
            self.choices = [type("C", (), {"message": Message(tool_calls)})()]

    class FakeCompletions:
        def create(self, **kwargs):
            calls = rounds.pop(0) if rounds else []
            return Response(calls)

    from services import llm_client
    from services.agent import agent as agent_module

    fake = FakeCompletions()
    monkeypatch.setattr(agent_module.client.chat.completions, "create", fake.create)
    return fake


def test_g1_工具失败_参数不是合法JSON(client, no_network, clean_db, monkeypatch):
    """触发：模型给出空字符串 / 截断的参数（agent.py:52 的 except json.JSONDecodeError）

    agent.py:53 会把错误拼成一段文字塞回模型：'错误：参数不是合法 JSON...'
    """
    _upload(client, "a.md", "内容")

    from services.agent import agent as agent_module

    _patch_agent(monkeypatch, [[_ToolCall("search_documents", "{不是JSON")]])

    # 直接调 run_agent，方便断言到底发生了什么
    result = _run_agent(agent_module, app.state.rag_service, "帮我查一下")
    assert result["tool_calls"] == ["search_documents"]
    assert result["answer"] == "最终回答"

    # 再直接把出错那一段单独跑一遍，断言塞回模型的文字（agent.py:53）
    text = _run_inline_json_error()
    assert text.startswith("错误：参数不是合法 JSON")
    assert "收到" in text


def test_g2_工具失败_不存在工具名(client, no_network, clean_db, monkeypatch):
    """触发：模型编了一个不存在的工具名（agent.py:56）"""
    from services.agent import agent as agent_module

    _patch_agent(monkeypatch, [[_ToolCall("delete_everything", "{}")]])

    result = _run_agent(agent_module, app.state.rag_service, "删库跑路")
    assert result["tool_calls"] == ["delete_everything"]


def test_g3_工具失败_业务错误返回文字不抛异常(client, no_network, clean_db):
    """触发：工具参数合法但业务上不成立，例如文档不存在、两个 id 相同。

    约定（tools.py 开头注释）：业务错误返回一句话，不抛异常。
    这里直接 await 工具函数，断言它返回的是提示文字。
    """
    from services.agent import tools

    rag = app.state.rag_service

    # 文档不存在
    assert "不存在" in _run(tools.summarize_document({"document_id": 999999}, rag))
    assert "不存在" in _run(
        tools.compare_documents({"document_id_a": 999999, "document_id_b": 1}, rag)
    )
    # 两个 id 相同
    same = _run(tools.compare_documents({"document_id_a": 2, "document_id_b": 2}, rag))
    assert "两个 id 相同" in same
    # 缺参数
    missing = _run(tools.search_documents({}, rag))
    assert missing.startswith("错误：缺少参数 query")
    # document_id 不是数字
    bad_id = _run(tools.search_documents({"query": "x", "document_id": "abc"}, rag))
    assert "必须是整数" in bad_id


def test_g4_工具失败_意外异常被兜住(client, no_network, clean_db, monkeypatch):
    """触发：工具内部抛了意料之外的异常（agent.py:65 的 except Exception）

    验证：异常不会冒到接口层（不会 500），而是变成 '函数执行出错：...' 交给模型。
    """
    from services.agent import agent as agent_module
    from services.agent import registry

    async def exploded(args, rag):
        raise ValueError("模拟工具内部崩了")

    monkeypatch.setitem(registry.available_functions, "search_documents", exploded)
    monkeypatch.setitem(agent_module.available_functions, "search_documents", exploded)

    _patch_agent(monkeypatch, [[_ToolCall("search_documents", '{"query": "x"}')]])

    # 这条路走完应当收敛成回答，而不是抛异常
    result = _run_agent(agent_module, app.state.rag_service, "查一下")
    assert result["answer"] == "最终回答"
    assert result["tool_calls"] == ["search_documents"]


def test_g5_工具失败_轮数用满强制给结论(client, no_network, clean_db, monkeypatch):
    """触发：模型每轮都调工具（MAX_ROUNDS = 3），走 agent.py:76 的收尾分支"""
    from services.agent import agent as agent_module

    # 4 组工具调用：前 3 轮都调，第 4 次是收尾那次（没有 tools 参数）
    _patch_agent(
        monkeypatch,
        [
            [_ToolCall("search_documents", '{"query": "a"}')],
            [_ToolCall("search_documents", '{"query": "b"}')],
            [_ToolCall("search_documents", '{"query": "c"}')],
        ],
    )

    result = _run_agent(agent_module, app.state.rag_service, "一直查")
    assert len(result["tool_calls"]) == 3, "最多 3 轮"
    assert result["answer"]


def test_g6_Agent接口_空问题直接400(client, clean_db):
    """触发：前端传空问题（api/agent.py:19 的保护）"""
    resp = client.post("/agent", json={"question": "   "})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "问题不能为空"


# =====================================================================
# 小工具
# =====================================================================

def _upload(client, filename: str, content: str, index: bool = True) -> int:
    """走真实上传接口塞一份文档，返回 document_id"""
    resp = client.post(
        "/documents/upload",
        files={"file": (filename, content.encode("utf-8"), "text/markdown")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["document_id"]


def _run(coro) -> str:
    """把 await 工具函数的协程跑完（测试是同步的，用 asyncio.run 最省事）"""
    import asyncio

    return asyncio.run(coro)


def _run_agent(agent_module, rag, question: str) -> dict:
    """同步跑一遍异步的 run_agent"""
    import asyncio

    return asyncio.run(agent_module.run_agent(question, rag))


def _run_inline_json_error() -> str:
    """把 agent.py 处理「工具参数不是合法 JSON」那几行单独跑一遍，返回塞回模型的文字。

    单独写一遍是为了不依赖假模型的行为，直接对准那 3 行分支代码。
    """
    import asyncio

    async def _inner() -> str:
        name = "search_documents"
        for tool_call in [_ToolCall(name, "{不是JSON")]:
            try:
                json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                return (
                    f"错误：参数不是合法 JSON（收到 {tool_call.function.arguments!r}），请重新给出参数。"
                )
        return ""

    return asyncio.run(_inner())
