# AI 文档分析与知识助手平台（后端）

FastAPI + SQLite + DeepSeek/DashScope。负责文档上传解析、结构化分析、RAG 检索问答和最小 Agent 工具调用。

运行环境见 `pyproject.toml`（`requires-python = ">=3.14"`），依赖用 `uv` 管理（仓库里有 `uv.lock`）。

> 整体架构、接口完整示例和数据库表结构请先看仓库根目录的 [`README.md`](../README.md)；这里主要讲**文件职责**和**后端怎么跑起来**。

---

## 一、运行后端

```bash
cd backend

# 1. 安装依赖（推荐 uv）
uv sync
# 没有 uv 时也可以用 pip：
# python -m venv .venv && .venv\Scripts\activate && pip install -e .

# 2. 配置环境变量
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

# 3. 启动
python main.py                # 或 uv run python main.py
```

启动成功后：

| 地址 | 说明 |
|---|---|
| `http://127.0.0.1:8080` | 服务根路径 |
| `http://127.0.0.1:8080/health` | 健康检查，返回 `{"message": "Hello FastAPI"}` |
| `http://127.0.0.1:8080/docs` | Swagger 接口文档（前端联调主要看这个） |

> ⚠️ **必须在 `backend/` 目录下启动**，原因有两个：
> 1. 代码里用的是绝对导入（`from api.documents import ...`、`from database import ...`），工作目录不对就找不到模块；
> 2. 数据库路径是相对路径 `document.db`，换目录会**另外生成一个空库**。

启动日志里会看到：

```text
2026-01-01 10:00:00 [INFO] main: RAG 服务已就绪（等待按需索引）
2026-01-01 10:00:00 [INFO] main: 索引加载成功，共 N 个片段        # 或「未发现已有索引，等待文档上传后按需建立」
2026-01-01 10:00:00 [INFO] main: 数据库初始化成功
```

同样的内容也会写进 `backend/logs/app.log`（见第六节）。

索引文件损坏时（例如写入中途被强杀），启动会记录「索引加载失败（已忽略…）」，服务仍然能起来，到「文档管理」页重新建立索引即可。

---

## 二、目录职责

```text
backend/
├── main.py                  # 应用入口：初始化日志、lifespan 里初始化 RAG + 建表，挂载 4 个路由
├── config.py                # 路径常量：BASE_DIR / INDEX_DIR / DATA_DIR
├── logging_config.py        # 统一日志：控制台 + logs/app.log，setup_logging() 只在 main.py 调一次
├── database.py              # SQLite：连接、get_db() 上下文管理器、init_db() 建表
├── pyproject.toml / uv.lock # 依赖声明与锁定
├── api/                     # 路由层：只做参数校验 + 调 service，不写业务逻辑
│   ├── documents.py         # 上传、详情、文件名、列表（带索引状态）、删除
│   ├── analysis.py          # 结构化分析并落库 + 读取已保存结果
│   ├── qa.py                # RAG 问答 + 按 document_id 建索引
│   └── agent.py             # Agent 入口
├── schemas/
│   └── schemas.py           # Pydantic 模型：DocumentAnalysis / AnalysisRequest / AnalysisRecordResponse
├── services/
│   ├── llm_client.py        # DeepSeek 客户端（读 DEEPSEEK_* 环境变量，缺 Key 直接报错）
│   ├── llm_service.py       # json_out：结构化分析 + 解析 JSON + Pydantic 校验
│   ├── prompts.py           # Prompt 模板（目前只有 json_out 一个）
│   ├── rag/
│   │   ├── llm.py           # 环境变量 + embed() / chat()，懒加载单例客户端
│   │   ├── config.py        # 兼容入口：只把 llm.py 里的变量转发出来（值只有一份）
│   │   ├── splitter.py      # 切块：split_text_line（按段）/ split_text_length（滑窗）
│   │   ├── store.py         # VectorStore：内存矩阵 + chunks + sources，落盘/加载/删除
│   │   └── rag.py           # RAG 类：index_text / retrieve / answer / save_index / load_index
│   └── agent/
│       ├── registry.py      # 工具 schema 与名字到函数的映射
│       ├── tools.py         # list_documents / search_documents / summarize_document / compare_documents
│       └── agent.py         # 最小 Agent 循环（最多 3 轮）
├── tests/                   # pytest 用例（错误处理，见第十节）
│   ├── conftest.py          # 夹具：假 Embedding / 假模型 / 清库
│   └── test_error_handling.py
├── index_store/             # 向量索引落盘位置（vectors.npy + meta.json），由代码自动生成
├── logs/                    # 运行日志 app.log，由代码自动生成
└── document.db              # SQLite 数据文件，首次启动自动创建
```

---

## 三、接口一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/documents/upload` | 上传 `.txt` / `.md`，入库并**自动建立索引** |
| GET | `/documents` | 文档列表，带 `indexed` / `chunks`（注意路径没有尾斜杠） |
| GET | `/documents/{id}` | 文档详情，含完整正文 |
| GET | `/documents/name/{id}` | 只取文件名 |
| DELETE | `/documents/{id}` | 删文档，同时删分析记录和索引片段 |
| POST | `/analysis/document` | 结构化分析，结果写入 `analysis_records`（带 `?regenerate=true` 可强制重跑） |
| GET | `/analysis/document/{id}` | 读取这份文档**最新**的一条分析结果（`result` 已解析成对象） |
| POST | `/qa/` | 单文档（RAG）问答 |
| POST | `/qa/index/{id}` | 给某份文档建立或重建索引 |
| POST | `/agent` | Agent 模式，返回 `{answer, tool_calls}` |

路径写法上有两个刻意的区别：`@router.get("")` 得到 `/documents`，`@router.post("/")` 得到 `/qa/`。写成 `/` 会触发 307 跳转，前端 axios 跟随后端也会收到响应，但日志里会出现一次多余的重定向。

常见错误码：

| 状态码 | 触发条件 | detail |
|---|---|---|
| 400 | 扩展名不是 .txt / .md | `仅支持 .txt 或 .md 文件` |
| 400 | 不是 UTF-8 | `文件编码格式错误，请使用 UTF-8 编码` |
| 404 | 文档不存在 | `文档不存在` |
| 409 | 文档还没建索引就想提问 | `这份文档还没有建立索引，请先建立索引` |
| 500 | 模型调用失败 / JSON 不合法 / 结构校验失败 | 见 `llm_service.py` 的三条分支 |

---

## 四、RAG 是怎么跑的

### 写入侧（建索引）

```text
文档正文
  → split_text_line：按空行/换行切段，单段超过 500 字再用滑窗切（overlap = 80）
  → embed()：调 DashScope text-embedding-v3，每批最多 10 条
  → VectorStore.add()：L2 归一化后堆成 float32 矩阵，同时记下每个 chunk 的 source（= document_id）
  → save_index()：写 index_store/vectors.npy 和 meta.json
```

同一个 `source` 重新索引时是**先删后加**，所以「重新索引」不会产生重复片段。

### 读取侧（提问）

```text
问题 → embed() → VectorStore.search()
  → 向量已归一化，点积就是余弦相似度
  → 可选 source_filter：只在这份文档的片段里排序（不属于该 source 的分数置 -inf）
  → 取 Top-K（默认 3）→ 拼进 PROMPT_TEMPLATE → chat() 生成答案
```

Prompt 里明确要求「资料中没有相关信息就回答资料中没有提到」，用来抑制编造。

### 持久化与损坏防护

- `index_store/vectors.npy` + `index_store/meta.json` 必须成对存在；
- `store.load()` 会校验 `chunks` / `sources` / 向量行数三者一致，不一致就抛「索引文件损坏」；
- 删除文档时如果片段被删光，会连 `vectors.npy` 和 `meta.json` 一起清掉，避免下次启动数量对不上；
- `main.py` 里 `load_index()` 包了 try/except，索引坏了不会导致整个服务起不来。

---

## 五、Agent 是怎么跑的

`services/agent/agent.py` 是一个**最小循环**：调模型 → 看要不要用工具 → 执行 → 结果回填 → 再调，最多 `MAX_ROUNDS = 3` 轮。

四个工具（`services/agent/tools.py`）：

| 工具 | 参数 | 说明 |
|---|---|---|
| `list_documents` | 无 | 列出所有文档的「编号 + 文件名」。用户按文件名提问时，模型先用它把文件名翻译成编号 |
| `search_documents` | `query`、`top_k`（1~10，默认 3）、`document_id`（可选）、`filename`（可选，模糊匹配） | 只返回检索片段，不生成答案；`filename` 会自动翻译成编号 |
| `summarize_document` | `document_id` | 复用 `json_out()` 的摘要/关键点/关键词 |
| `compare_documents` | `document_id_a`、`document_id_b`、`aspect`（可选） | 两份文档各截 6000 字比较 |

约定：工具入参来自模型，**必须校验**；业务错误返回一句中文说明而不是抛异常；网络/模型异常由循环统一兜住转成文字回填。轮数用完还没收敛时，会再问一次但**不再给工具**，强制它给结论。

**为什么会有 `list_documents`**：向量检索只认 `document_id`，而用户习惯按文件名提问（「doc.md 的主要内容是什么」）。没有文档清单时，模型不知道 `doc.md` 对应几号，就会拿文件名当关键词反复乱搜；有了清单，它能先查编号再检索或总结。同理，系统提示词里明确要求「问某份文档的主要内容时用 `summarize_document` 取整篇」——「主要内容」这类整体性问题不适合只给 Top-3 片段，检索会答成片面结论。模型走哪个工具，几乎完全由 `registry.py` 的 description 和 `agent.py` 的 `SYSTEM_PROMPT` 这两处文字决定，调整行为优先改这两处。

---

## 六、日志（Day 22 任务 3）

配置集中在 `logging_config.py`，`main.py` 启动时调用一次 `setup_logging()`；其他模块只用 `logger = logging.getLogger(__name__)` 记录，不再用 `print`。

- 输出两处：**控制台**（和原来一样看得见）和 **`backend/logs/app.log`**；
- 文件按 1MB 轮转、留 3 份备份，不会无限增长；
- 格式：`时间 [级别] 模块名: 内容`。

记录点：

| 位置 | 级别 | 记什么 |
|---|---|---|
| `main.py` lifespan | INFO | RAG 就绪、索引加载成功/失败、数据库初始化、服务关闭 |
| `api/documents.py` 上传 | WARNING / ERROR | 扩展名不支持、非 UTF-8（用户操作问题）；自动索引失败（ERROR，提示可去文档管理页重建） |
| `api/qa.py` | WARNING | 未建索引就提问（409）、建索引时文档不存在（404） |
| `api/analysis.py` | WARNING | 文档不存在（404）、还没有分析记录（404） |
| `services/llm_service.py` | ERROR | 模型调用失败、返回的不是合法 JSON（带前 200 字）、Pydantic 结构校验失败（带具体字段） |
| `services/rag/rag.py` | INFO | 清理旧索引的片段数、索引保存的片段数 |
| `services/agent/agent.py` | WARNING / ERROR | 工具参数不是合法 JSON、调用了不存在的工具、工具执行抛异常（ERROR 带堆栈） |

两条约定：**不打印 API Key 和 `.env` 内容**（只记异常本身的文字）；用户操作类的问题用 WARNING，代码/外部服务的问题用 ERROR，这样翻日志时能一眼分开。

---

## 七、环境变量（`backend/.env`）

从 `.env.example` 复制，不要提交到 Git。

| 变量 | 谁在用 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | `llm_client.py` | DeepSeek 密钥，读不到会直接抛 `ValueError` |
| `DEEPSEEK_BASE_URL` | `llm_client.py` | OpenAI 兼容地址 |
| `DEEPSEEK_MODEL` | `llm_client.py` | 默认 `deepseek-chat` |
| `OPENAI_API_KEY` | `rag/llm.py` | 阿里云百炼密钥，**Embedding 用它**（也兼容 `DASHSCOPE_API_KEY`） |
| `OPENAI_BASE_URL` | `rag/llm.py` | 默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `EMBED_MODEL` | `rag/llm.py` | 默认 `text-embedding-v3` |
| `CHAT_MODEL` | `rag/llm.py` | RAG 生成回答用的对话模型 |
| `RERANK_MODEL` / `RERANK_URL` | 暂无 | 预留给重排，目前还没接进检索流程 |

所以项目同时用到两家服务：**分析/Agent 用 DeepSeek 的 OpenAI 兼容接口，Embedding 用阿里云百炼**。少任何一个 Key，对应功能会失败。

---

## 八、已知限制与可补的点

1. **重排没接**：`RERANK_MODEL` / `RERANK_URL` 有配置项，但检索流程里没有调用；
2. **向量库是内存矩阵**：数据量大时 `np.argsort` 全量排序会变慢，也没有多进程共享；规模上来应该换向量数据库；
3. **问答不落库**：`/qa/` 只返回答案，没有 `qa_records` 表；
4. **`analysis.py` 的请求体是双轨的**：优先用 Pydantic 的 `AnalysisRequest`（字段不对返回 422），没传 body 时再退回 `await req.json()` 手工取（兼容旧调用）。这层兼容逻辑属于「为了不破坏老前端」的过渡写法，稳定之后可以只留 Pydantic；
5. **日志是「记录点」级别，不是全链路追踪**：没有请求 ID，也没有把同一次请求的多条日志串起来；
6. 仅支持 TXT / Markdown，无 PDF / Word / OCR；
7. **测试用例还没有实际跑通**：`tests/` 下有 30 多个错误处理用例，但写它们的环境没法执行 Python，断言可能与真实行为有出入（见第十节）；也没有 CI；
8. 无登录、权限校验和速率限制，接口对本机完全开放。

---

## 九、改完后端后的验证清单

1. `python main.py` 能启动，日志出现 RAG 就绪 + 数据库初始化成功；
2. `/docs` 能打开，11 个接口都在（第三节的表 11 行）；
3. 上传一份 TXT，响应里 `indexed` 为 true；
4. `GET /documents` 能看到这份文档且 `indexed` 为 true、`chunks` 大于 0；
5. `POST /analysis/document` 返回五个字段；`GET /analysis/document/{id}` 能把同一份结果读回来（没分析过的 id 应当是 404 而不是 500）；
6. `POST /qa/` 能返回答案，未建索引的文档返回 409；
7. `POST /agent` 分别试「有哪些文档」（应调 `list_documents`）、「doc.md 的主要内容是什么」（应先 `list_documents` 再 `summarize_document`）、「比较文档 1 和文档 2」，`tool_calls` 应出现对应工具名；
8. `DELETE /documents/{id}` 后列表里消失，`index_store/meta.json` 里也不再有该 source 的片段；
9. 重启后端，索引能自动加载（日志「索引加载成功，共 N 个片段」）；
10. 打开 `backend/logs/app.log`：上传成功、提问、删除这些动作应当有对应记录；故意上传一个 `.pdf` 或故意问没索引的文档，应当能看到 WARNING 级别的那一行。

---

## 十、自动化测试（Day 22 加的错误处理用例）

`tests/` 下是一套错误处理用例，覆盖 Day 22 任务 1 要求的 7 类错误：文件错误、`document_id` 不存在、模型失败、JSON 解析失败、数据库失败、RAG 无结果、Agent 工具失败。

```bash
cd backend
uv run --with pytest --with httpx pytest tests -v     # 不额外装依赖，直接跑
# 或：uv add --dev pytest httpx && uv run pytest -v
```

| 文件 | 作用 |
|---|---|
| `tests/conftest.py` | 把假的外部调用装进夹具：`fake_embed` / `fake_chat` 替代网络请求，`clean_db` 每个用例前清空两张表，`fake_json_out` 让结构化分析返回指定内容 |
| `tests/test_error_handling.py` | 全部用例，命名前缀对应错误类别（`a` 文件、`b` 不存在、`c` 模型、`d` JSON、`e` 数据库、`f` RAG、`g` Agent、`h` 分析结果查看） |
| `pytest.ini` | `testpaths = tests`，所以必须在 `backend/` 下执行 |

两个要点：

1. **假的是外部调用，不是接口**。用例真的走 FastAPI 路由和 SQLite，只是把「调 Embedding」「调大模型」换掉了，所以不花钱、不联网、每次结果一致。
2. **patch 的位置要对**。`services/rag/rag.py` 写的是 `from .llm import chat, embed`，这两个函数在导入时就绑定了，所以要打 `services.rag.rag` 上的属性；`rag/llm.py` 里的 `client()` 是运行时才调的，直接换成假客户端才管用；`api/analysis.py` 同理，`json_out` 要在 `api.analysis` 自己的命名空间里再打一次（`conftest.py` 里有注释说明）。
3. **测试会写日志**。`main` 被导入时会执行 `setup_logging()`，所以跑用例会顺带往 `backend/logs/app.log` 写。

> ⚠️ 这套用例**尚未在本机跑通过**（写的时候没法在这个环境里执行 Python）。后来整理后端时又动过 `llm_service.py` / `analysis.py` / `qa.py`（加日志、加 Pydantic 请求体）。第一次跑如果有失败，先看断言里期望的文案跟代码里的是否一致，再改断言或代码。
