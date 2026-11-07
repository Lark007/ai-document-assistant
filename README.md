<!-- 作用：项目总说明。前端细节见 frontend/README.md，后端细节见 backend/README.md。 -->
# AI 文档分析与知识助手平台

一个从零搭起来的全栈学习项目：上传 TXT / Markdown 文档，在浏览器里预览正文，调用大模型生成**结构化**分析结果，再把文档切块、向量化、建立索引，围绕文档做 **RAG 检索问答**，最后让一个**最小 Agent** 自己决定调用哪个工具。

前端 Vue 3 + Vite，后端 FastAPI + SQLite，模型侧用 DeepSeek 的 OpenAI 兼容接口，Embedding 用阿里云百炼的 `text-embedding-v3`。

> 当前版本：**V1.0**。已跑通的两条闭环：
> **上传 → 预览 → 结构化分析 → 落库** 和 **建索引 → 检索 → 带来源回答 → Agent 选工具**。
> 阶段定义见 [每日任务计划.md](每日任务计划.md)，执行中的计划见 [每日任务计划_Day14-Day28_阶段修订版_2026-10-08.md](每日任务计划_Day14-Day28_阶段修订版_2026-10-08.md)。

---

## 一、项目要解决的问题

这个项目想做的是一件很具体的事：**把「读一份长文档」从一件模糊的事，变成一份结构固定、能存进数据库、能按字段渲染、还能继续追问的数据。**

它真正练的不是「调用一个大模型」，而是下面四件事：

| 要做的事 | 具体做法 |
|---|---|
| 模型输出不可控 | 要求返回 JSON + Pydantic 校验 + 字段固定，前端不需要「读懂一段话」 |
| 文档太长塞不进上下文 | 切块 → Embedding → 只把最相关的 Top-K 片段喂给模型（RAG） |
| 不知道模型在用什么依据 | 检索片段带回 `source` 和相似度分数，回答不靠全文瞎猜 |
| 模型该用哪个能力 | Tool Calling + 循环，让模型自己决定搜索、总结还是对比 |

### Structured Output 长什么样

```json
{
  "summary":      "文档整体摘要",
  "key_points":   ["关键点 1", "关键点 2"],
  "keywords":     ["FastAPI", "Vue 3"],
  "action_items": ["下一步要做什么"],
  "questions":    ["可以继续追问的问题"]
}
```

前端拿到这个对象后，直接按字段渲染到固定区域即可 —— 这就是 Structured Output 相对于「一段自然语言回答」的价值。

---

## 二、技术栈

### 前端

| 技术 | 版本 | 用途 |
|---|---|---|
| Vue 3 | ^3.5.13 | 组件与响应式（全部使用 `<script setup>` 组合式 API） |
| Vue Router | ^4.5.0 | 四个页面的路由（History 模式） |
| Vite | ^6.0.5 | 开发服务器、构建工具、`/api` 代理 |
| Axios | ^1.7.9 | HTTP 请求，统一实例 + 响应拦截器 |
| 原生 CSS | — | 无 UI 框架，`base.css` 放设计变量和公共类 + 组件内 `<style scoped>` |

### 后端

| 技术 | 版本 | 用途 |
|---|---|---|
| Python | `requires-python = ">=3.14"` | 运行环境（见 `backend/pyproject.toml`） |
| FastAPI | 0.142.2 | Web 框架、自动生成 Swagger |
| Uvicorn | 0.54.0 | ASGI 服务器 |
| Pydantic | 2.13.5 | 校验模型输出结构（`DocumentAnalysis`）、校验请求体 |
| openai | 3.24.0 | SDK，通过 OpenAI 兼容接口调用 DeepSeek 和 DashScope |
| numpy | >=2.5.4 | 向量矩阵：归一化、点积打分、`argsort` 排序、`np.save` 持久化 |
| python-dotenv | 1.2.4 | 从 `.env` 读取密钥 |
| python-multipart | 0.0.32 | 解析 `multipart/form-data`（`UploadFile` 必需） |
| sqlite3 | Python 内置 | 文档与分析记录持久化，无需额外安装 |

没有 Pinia，没有 Tailwind，没有向量数据库 —— 这些是刻意不引入的，见第九节。

---

## 三、系统架构

```text
┌──────────────────────────────────────────────────────┐
│  浏览器  Vue 3 SPA  (:5173)                           │
│    /            首页                                  │
│    /documents   文档管理（列表 / 建索引 / 删除）         │
│    /analysis    文档分析（上传 → 预览 → AI 分析）        │
│    /qa          知识问答（RAG 问答 / Agent 模式）        │
│    axios 统一实例：baseURL = "/api"                    │
└──────────────────────┬───────────────────────────────┘
                       │ /api/...
                       ▼
┌──────────────────────────────────────────────────────┐
│  Vite 开发服务器 (:5173)                              │
│    代理 /api → http://127.0.0.1:8080                  │
│    并 rewrite 去掉 /api 前缀                           │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│  FastAPI  (:8080)                                    │
│   api/documents.py  上传 / 详情 / 列表 / 删除           │
│   api/analysis.py   结构化分析 + 落库                   │
│   api/qa.py         建索引 + RAG 问答                  │
│   api/agent.py      Agent 循环                        │
│   services/         LLM、Prompt、RAG、Agent（见 backend/README.md）│
└───────┬──────────────────┬───────────────┬───────────┘
        │                  │               │
        ▼                  ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌──────────────────────┐
│ SQLite        │  │ 向量索引        │  │ 大模型                │
│ document.db   │  │ index_store/  │  │ DeepSeek：分析与 Agent │
│  documents    │  │ vectors.npy   │  │ DashScope：Embedding  │
│  analysis_    │  │ meta.json     │  │                      │
│   records     │  │               │  │                      │
└───────────────┘  └───────────────┘  └──────────────────────┘
```

---

## 四、四条数据流

### 1. 上传 → 预览 → 分析

```text
1. /analysis 选择 a.md，浏览器本地读一遍正文（file.text()）→ 预览区立刻显示
2. 点击「上传到后端」→ POST /api/documents/upload（multipart，字段名 file）
3. 后端校验扩展名 → UTF-8 解码 → INSERT INTO documents → 自动切块建索引 → 返回 document_id
4. 前端再请求详情接口拿到完整正文，并把文档写入 sessionStorage（供 /qa 页使用）
5. 点击「AI 分析文档」→ POST /api/analysis/document {"document_id": 1}
6. 后端取全文 → 拼 Prompt → 调 DeepSeek（response_format = json_object）
7. 清洗可能的 ```json 包裹 → json.loads → Pydantic 校验 → INSERT INTO analysis_records
8. AnalysisResult.vue 按五个字段分区渲染
```

### 2. 建索引 → 检索 → 回答（RAG）

```text
1. 上传时已自动建索引；也可以到 /documents 点「重新索引」→ POST /api/qa/index/{id}
2. 切块：按段切，单段超过 500 字用滑窗切，overlap = 80
3. Embedding：DashScope text-embedding-v3，每批最多 10 条
4. 入库：L2 归一化后堆成 float32 矩阵，记下每个 chunk 的 source（= document_id）
5. 落盘：index_store/vectors.npy + meta.json
6. 提问 → POST /api/qa/ → 问题向量化 → 与矩阵做点积（= 余弦相似度）→ 取 Top-3
7. 只把 Top-3 片段拼进 Prompt → 生成答案（资料里没有就回答「资料中没有提到」）
```

### 3. Agent 选工具

```text
1. /qa 打开「Agent 模式」→ POST /api/agent {"question": "..."}
2. 模型判断要不要调用工具（list_documents / search_documents / summarize_document / compare_documents）
   按文件名提问时先 list_documents 拿编号；问「主要内容是什么」时走 summarize_document 取整篇
3. 参数校验 → 执行本地函数 → 结果回填 → 再调，最多 3 轮
4. 轮数用完仍没收敛时，再问一次但不再给工具，强制它给结论
5. 返回 {answer, tool_calls}，前端把「调用了哪些工具」显示在回答前面
```

### 4. 管理文档

```text
/documents → GET /api/documents（带 indexed / chunks）
点「建立索引」→ POST /api/qa/index/{id}（同一个 source 是先删后加，不会重复）
点「删除」→ DELETE /api/documents/{id}（同时删分析记录和索引片段，片段清空时连索引文件一起删）
```

**为什么要绕后端这一圈，而不让前端直接调大模型？** 因为 API Key 一旦出现在前端就等于公开（F12 就能看到），前端设的任何限制也都能被绕过。凡是「密钥」和「限制」，都必须放在后端。

---

## 五、快速开始

### 环境要求

| 项目 | 要求 | 本机开发环境 |
|---|---|---|
| 操作系统 | Windows / macOS / Linux | Windows |
| Python | 见 `backend/pyproject.toml`（`>=3.14`） | 3.14 |
| Node.js | 18 及以上（Vite 6 要求） | 24.21.0 |
| SQLite | **不需要单独安装** | Python 内置 `sqlite3` |
| DeepSeek API Key | 分析与 Agent 需要 | [platform.deepseek.com](https://platform.deepseek.com) |
| 阿里云百炼 API Key | Embedding（建索引、检索）需要 | [百炼控制台](https://bailian.console.aliyun.com) |

> 两个 Key 都没有时：上传、预览、文档列表和删除仍可用，只有「AI 分析」「建索引」「提问」会失败。

### 1. 启动后端

```bash
cd backend
uv sync                      # 没有 uv 时用 pip 装 pyproject.toml 里的依赖
copy .env.example .env       # Windows；macOS/Linux 用 cp
# 编辑 .env，至少填 DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、OPENAI_API_KEY、OPENAI_BASE_URL
python main.py
```

- 服务地址：`http://127.0.0.1:8080`
- 健康检查：`http://127.0.0.1:8080/health`
- 接口文档：`http://127.0.0.1:8080/docs`
- 首次启动会打印「数据库初始化成功」，并在 `backend/` 下创建 `document.db`

> ⚠️ 必须在 `backend/` 目录下启动 `python main.py`：代码用的是绝对导入，数据库路径也是相对路径（换目录会另外生成一个空库）。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`。前端不需要创建 `.env`（`baseURL` 写死为 `/api`，由 Vite 代理转发），后端端口改了要同步改 `vite.config.js` 的 `proxy.target`。

更详细的前端说明见 [frontend/README.md](frontend/README.md)，后端文件职责见 [backend/README.md](backend/README.md)。

---

## 六、项目目录

```text
ai-document-assistant/
├── backend/                              # FastAPI 后端
│   ├── api/
│   │   ├── documents.py                  # 上传、详情、文件名、列表、删除
│   │   ├── analysis.py                   # 结构化分析 + 落库
│   │   ├── qa.py                         # RAG 问答 + 建索引
│   │   └── agent.py                      # Agent 入口
│   ├── services/
│   │   ├── llm_client.py                 # DeepSeek 客户端（读 .env）
│   │   ├── llm_service.py                # json_out / llm_qa
│   │   ├── prompts.py                    # Prompt 模板
│   │   ├── document_schema.py            # DocumentAnalysis 数据模型
│   │   ├── rag/                          # config / llm / splitter / store / rag
│   │   └── agent/                        # registry / tools / agent
│   ├── database.py                       # SQLite 连接、建表、get_db 上下文管理器
│   ├── config.py                         # BASE_DIR / INDEX_DIR / DATA_DIR
│   ├── main.py                           # 入口：lifespan 初始化 RAG + 建表 + 挂载路由
│   ├── index_store/                      # vectors.npy + meta.json（自动生成）
│   ├── document.db                       # SQLite 数据文件（首次运行自动创建）
│   ├── pyproject.toml / uv.lock          # 依赖声明与锁定
│   ├── .env.example                      # 环境变量模板
│   └── README.md                         # 后端专项说明
├── frontend/                             # Vue 3 前端
│   ├── src/
│   │   ├── api/                          # http / document / analysis / qa / knowledge / agent
│   │   ├── components/                   # AppHeader / FileUploader / DocumentPreview / AnalysisResult / QABox
│   │   ├── views/                        # HomeView / DocumentsView / AnalysisView / QAView
│   │   ├── router/index.js               # 路由表
│   │   ├── stores/currentDocument.js     # 跨页共享「当前文档」（模块级 ref + sessionStorage）
│   │   ├── styles/base.css               # 设计变量 + 公共类
│   │   ├── App.vue / main.js
│   │   └── README.md                     # 前端专项说明
│   ├── vite.config.js                    # 开发服务器 + /api 代理
│   └── package.json
├── Day9_AI 文档分析与知识助手平台_项目设计.md
├── 每日任务计划.md
└── 每日任务计划_Day14-Day28_阶段修订版_2026-10-08.md
```

---

## 七、API 列表

开发环境下前端统一请求 `/api/...`，由 Vite 代理转发到 `http://127.0.0.1:8080` 并**去掉 `/api` 前缀**。下表「后端路径」是 FastAPI 里实际注册的路径。

| 方法 | 后端路径 | 前端请求路径 | 说明 |
|---|---|---|---|
| GET | `/health` | `/api/health` | 健康检查 |
| POST | `/documents/upload` | `/api/documents/upload` | 上传 TXT / MD，自动建索引 |
| GET | `/documents` | `/api/documents` | 文档列表（带索引状态） |
| GET | `/documents/{id}` | `/api/documents/{id}` | 文档详情，含完整正文 |
| GET | `/documents/name/{id}` | `/api/documents/name/{id}` | 只取文件名 |
| DELETE | `/documents/{id}` | `/api/documents/{id}` | 删文档 + 分析记录 + 索引片段 |
| POST | `/analysis/document` | `/api/analysis/document` | AI 结构化分析 |
| POST | `/qa/` | `/api/qa/` | 单文档 RAG 问答 |
| POST | `/qa/index/{id}` | `/api/qa/index/{id}` | 建立 / 重建索引 |
| POST | `/agent` | `/api/agent` | Agent 模式 |

> ⚠️ 路径写法有两个刻意的区别：`/documents` 与 `/agent` **没有**尾斜杠（装饰器写 `""`），`/qa/` **有**尾斜杠（装饰器写 `"/"`）。写成 `/` 会触发 307 跳转。

### 1. 上传文档

```http
POST /documents/upload
Content-Type: multipart/form-data
```

表单字段名必须是 `file`：

```json
{
  "document_id": 1,
  "filename": "fastapi_notes.md",
  "file_type": "md",
  "length": 5230,
  "preview": "FastAPI 是一个……",
  "indexed": true
}
```

| 状态码 | 触发条件 | `detail` |
|---|---|---|
| 400 | 扩展名不是 `.txt` / `.md` | `仅支持 .txt 或 .md 文件` |
| 400 | 不是 UTF-8 编码 | `文件编码格式错误，请使用 UTF-8 编码` |
| 500 | 读取文件出现意外错误 | `读取文件失败: ...` |

> 索引失败**不影响上传成功**：这时 `indexed` 为 `false`，可以到「文档管理」页手动建索引。

### 2. 文档列表

```http
GET /documents
```

```json
[
  {
    "document_id": 1,
    "filename": "fastapi_notes.md",
    "file_type": "md",
    "length": 5230,
    "created_at": "2026-01-01 12:00:00",
    "indexed": true,
    "chunks": 12
  }
]
```

### 3. 文档详情

```http
GET /documents/1
```

```json
{
  "document_id": 1,
  "filename": "fastapi_notes.md",
  "file_type": "md",
  "length": 5230,
  "content": "FastAPI 是一个……（完整内容）"
}
```

| 状态码 | 触发条件 | `detail` |
|---|---|---|
| 404 | `document_id` 不存在 | `文档不存在` |

### 4. 删除文档

```http
DELETE /documents/1
```

```json
{ "message": "已删除", "document_id": 1, "filename": "fastapi_notes.md", "removed_chunks": 12 }
```

删除时先删子表分析记录，再删文档，最后把索引片段按 `source` 移除；如果片段被删光，连 `index_store/` 下的两个索引文件一起清掉，避免下次启动数量对不上。

### 5. AI 结构化分析

```http
POST /analysis/document
```

请求 `{ "document_id": 1 }`，成功返回：

```json
{
  "summary": "本文介绍了 FastAPI 的核心特性与使用方法。",
  "key_points": ["FastAPI 基于 Starlette 和 Pydantic", "支持异步请求处理"],
  "keywords": ["FastAPI", "Python", "Web 框架"],
  "action_items": ["完成一个文件上传接口"],
  "questions": ["如何实现依赖注入？"]
}
```

| 状态码 | 触发条件 | `detail` |
|---|---|---|
| 404 | `document_id` 不存在 | `文档不存在` |
| 500 | 调用模型失败 | `大模型调用失败: ...` |
| 500 | 模型返回的不是合法 JSON | `大模型返回的不是合法 JSON，请检查 Prompt 或降低 temperature` |
| 500 | JSON 合法但字段不符 | `模型输出结构校验失败: 字段 [xxx]: ...` |

结果会以 JSON 字符串写入 `analysis_records`（`analysis_type` 固定为 `structured_output`）。

### 6. RAG 问答

```http
POST /qa/
```

请求 `{ "document_id": 1, "question": "最重要的三个知识点是什么？" }`，成功返回：

```json
{ "answer": "根据检索到的片段，文档中提到的三个重点是……" }
```

| 状态码 | 触发条件 | `detail` |
|---|---|---|
| 404 | `document_id` 不存在 | `文档不存在` |
| 409 | 该文档还没建过索引 | `这份文档还没有建立索引，请先建立索引` |
| 503 | RAG 服务未就绪 | `RAG 服务未就绪` |

### 7. 建立索引

```http
POST /qa/index/1
```

```json
{ "message": "索引完成", "doc_id": 1, "chunks": 12, "filename": "fastapi_notes.md" }
```

同一个 `document_id` 再次调用是**先删后加**，不会产生重复片段。

### 8. Agent

```http
POST /agent
```

请求 `{ "question": "比较文档 1 和文档 2 的技术要求" }`，成功返回：

```json
{
  "answer": "两份文档的相同点是……",
  "tool_calls": ["compare_documents"]
}
```

| 状态码 | 触发条件 | `detail` |
|---|---|---|
| 400 | 问题为空 | `问题不能为空` |
| 503 | RAG 服务未就绪 | `RAG 服务未就绪` |

---

## 八、数据库与索引

### documents

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键，对外就是 `document_id` |
| `filename` | TEXT | 原始文件名 |
| `file_type` | TEXT | `txt` / `md`（不带点号） |
| `content` | TEXT | 完整正文 |
| `created_at` | TIMESTAMP | 默认 `CURRENT_TIMESTAMP` |

### analysis_records

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER | 主键 |
| `document_id` | INTEGER | 外键 → `documents.id` |
| `analysis_type` | TEXT | 当前固定 `structured_output` |
| `result` | TEXT | 结构化结果的 JSON 字符串 |
| `created_at` | TIMESTAMP | 默认 `CURRENT_TIMESTAMP` |

一份文档可以有多条分析记录（重新分析、将来更多分析类型），所以拆成两张表。`get_connection()` 里执行了 `PRAGMA foreign_keys = ON`，外键约束是**生效**的（外键是连接级设置，所以每建一条连接都要开一次）。

### 向量索引（`backend/index_store/`）

| 文件 | 内容 |
|---|---|
| `vectors.npy` | float32 矩阵，每行一个 L2 归一化后的 chunk 向量 |
| `meta.json` | `{"chunks": [...], "sources": [...]}`，`sources` 存的是 `document_id` 字符串 |

加载时会校验 `chunks` / `sources` / 向量行数三者一致，不一致就判定索引损坏；`main.py` 兜住了这个异常，服务仍能启动，去「文档管理」页重建索引即可。

---

## 九、为什么不引入更多东西

这是学习项目，取舍是刻意的：

| 没引入 | 原因 |
|---|---|
| Pinia | 跨页只需要共享「当前文档」一个对象，模块级 `ref` + `sessionStorage` 更直观 |
| UI 框架 / Tailwind | 目的是练原生 CSS 变量和响应式布局，样式职责也更好解释 |
| 向量数据库 | 先用 numpy 矩阵把「归一化 + 点积 = 余弦相似度 + Top-K」写明白，规模不够时再换 |
| 重排模型 | `RERANK_MODEL` / `RERANK_URL` 配置项已留，但还没接进检索流程 |
| 测试框架 / CI | 属于后续工程化阶段（Day 22）的内容 |

---

## 十、当前功能与限制

### 已完成

| 模块 | 说明 |
|---|---|
| 文件选择与校验 | 点击或拖放选择 `.txt` / `.md`，前端校验扩展名与 2MB 上限 |
| 本地预览 | 浏览器先读一遍正文立即显示，另有「复制全文」按钮 |
| 文档上传 | multipart 上传，后端校验扩展名与 UTF-8，**上传即自动建索引** |
| 数据持久化 | 文档写入 SQLite，重启后端数据不丢 |
| 文档管理页 | 列表 + 索引状态 + 建立/重建索引 + 去提问 + 删除 |
| AI 结构化分析 | JSON 模式 + Markdown 包裹清洗 + Pydantic 校验 + 落库 |
| 结果展示 | 摘要 / 关键点 / 行动项 / 关键词 / 可追问的问题分区渲染 |
| RAG 检索问答 | 切块 → Embedding → 余弦相似度 Top-3 → 带来源约束的 Prompt |
| 索引持久化 | `vectors.npy` + `meta.json`，启动自动加载，损坏可降级 |
| 最小 Agent | 4 个工具（列文档 / 搜索 / 总结 / 对比），最多 3 轮，无 `tool_calls` 即收敛 |
| 前端体验 | 步骤编号统一、键盘焦点圈、`prefers-reduced-motion`、窄屏导航与表格滚动、问答自动滚到底部 |

### 尚未完成 / 已知限制

| 项 | 现状 |
|---|---|
| 问答记录持久化 | `/qa/` 只返回答案，没有 `qa_records` 表，刷新即丢 |
| 分析历史回看 | 只能看最新一条（`GET /analysis/document/{id}`），没有历史列表 |
| 检索没有重排 | Top-K 直接用余弦相似度排序 |
| 向量库是全量矩阵 | 数据量大时全量 `argsort` 会变慢，且不能多进程共享 |
| `analysis.py` 请求体 | Pydantic 与手工 `await req.json()` 双轨并存，稳定后可只留 Pydantic |
| 其他文档格式 | 仅 TXT / Markdown，PDF / Word / OCR 未支持 |
| 测试与 CI | `tests/` 下有 30+ 错误处理用例，但尚未实跑通过，也没有 CI |
| 日志没有请求 ID | 有分级日志和 `logs/app.log`，但一次请求的多行日志串不起来 |
| 无登录、权限、部署 | 接口对本机完全开放 |

---

## 十一、常见问题

**Q：页面提示「请求失败，请检查后端服务是否启动」？**
后端没启动或端口不一致。先确认 `http://127.0.0.1:8080/health` 能打开，再检查 `main.py` 的端口和 `vite.config.js` 的 `proxy.target` 是否一致。

**Q：上传报 400「仅支持 .txt 或 .md 文件」/「文件编码格式错误」？**
后端按扩展名判断，只接受 `.txt` 和 `.md`；编码必须是 UTF-8（记事本另存为选 UTF-8 即可），后端不做编码猜测。

**Q：上传成功但 `indexed` 是 false？**
索引那一步调 Embedding 失败了（Key、额度或网络问题）。文档本身已经入库，到「文档管理」页点「建立索引」重试。

**Q：提问返回 409「这份文档还没有建立索引」？**
这份文档从没建过索引，或者索引建过但后来被删了。先去「文档管理」页建索引。

**Q：分析报 500「大模型调用失败」？**
依次检查 `backend/.env` 里的 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、余额和本机网络。

**Q：建索引或问答报 Embedding 相关错误？**
Embedding 用的是阿里云百炼，检查 `.env` 里的 `OPENAI_API_KEY`（或 `DASHSCOPE_API_KEY`）和 `OPENAI_BASE_URL`。

**Q：问答报 404 或 405？**
确认路径：后端注册的是 `/qa/`（带尾斜杠），`/agent` 和 `/documents`（不带）。前端 `qa.js`、`agent.js` 也是按这个写的。

**Q：改了代码后文档不见了？**
文档存在 SQLite 里，重启不会丢。请确认启动时的工作目录是 `backend/`，否则会在别的目录新建一个空库。

**Q：刷新浏览器后预览和分析结果空了？**
正常现象。`uploadedDocument`、`analysisResult` 是组件内 `ref`，刷新即重置；只有「当前文档」的 `document_id` 存在 `sessionStorage` 里。

**Q：怎么看数据库里的数据？**

```bash
sqlite3 backend/document.db "SELECT id, filename, file_type, created_at FROM documents;"
```

或直接用 DB Browser for SQLite 打开 `backend/document.db`。

---

## 十二、界面预览

> 首页

![1792049816509](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792049816509.png)

![1792049833959](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792049833959.png)

![1792049841925](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792049841925.png)

> 文档分析页

![1792050051631](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050051631.png)

![1792050064105](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050064105.png)



![1792050070572](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050070572.png)

![1792050077504](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050077504.png)

> 文档管理页

![1792050137740](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050137740.png)

> 知识问答页

![1792050836668](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050836668.png)

![1792050854946](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792050854946.png)

![1792051837518](C:\Users\HS\AppData\Roaming\Typora\typora-user-images\1792051837518.png)