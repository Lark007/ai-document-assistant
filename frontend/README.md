# AI 文档分析与知识助手平台（前端）

这是项目的 Vue 3 前端，当前处于 **V1.0 阶段**：单文档闭环已经跑通，RAG 检索问答和最小 Agent 也已经接上。

四个页面：

| 路径 | 页面 | 作用 |
|---|---|---|
| `/` | 首页 | 介绍项目目标、当前功能和数据流 |
| `/documents` | 文档管理 | 列出全部文档、显示索引状态、建立索引、查看历史分析结果、删除、跳去提问 |
| `/analysis` | 文档分析（核心） | 选择 / 上传文档 → 预览正文 → 调用 AI 生成结构化分析 |
| `/analysis?documentId=3` | 分析结果查看 | 只看数据库里上一次保存的结果，可手动重新分析 |
| `/qa` | 知识问答 | 针对当前文档提问（RAG），或打开 Agent 模式让模型自己选工具 |

> 想先看整体架构、后端接口和数据库，请读仓库根目录的 [`README.md`](../README.md)。

---

## 一、技术栈

| 技术 | 版本 | 用途 |
|---|---|---|
| Vue 3 | ^3.5.13 | 组件与响应式，全部使用 `<script setup>` |
| Vue Router | ^4.5.0 | 四个页面的路由（History 模式） |
| Vite | ^6.0.5 | 开发服务器、构建、`/api` 代理 |
| Axios | ^1.7.9 | HTTP 请求，一个统一实例 + 响应拦截器 |
| 原生 CSS | — | 不使用 UI 框架：`base.css` 放全局变量和公共类，组件内用 `<style scoped>` |

没有 Pinia。跨页共享的「当前文档」用模块级 `ref` + `sessionStorage` 实现，见 `src/stores/currentDocument.js`。

---

## 二、运行项目

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 `http://localhost:5173`（5173 被占用时 Vite 会自动换端口，以终端输出为准）。

开发环境下 `/api` 请求由 Vite 代理到后端：

```text
http://127.0.0.1:8080        # vite.config.js 里的 proxy.target
```

后端端口改了，就改 `vite.config.js` 的 `proxy.target`。

**前端不需要创建 `.env`**：`src/api/http.js` 里 `baseURL` 写死为 `/api`，请求由代理转发，不受跨域限制。`.env.example` 里的 `VITE_API_BASE_URL` 目前是预留项，没有被读取。

其他命令：

```bash
npm run build      # 生产构建，产物在 dist/
npm run preview    # 本地预览构建产物
```

---

## 三、一次操作的数据流

不要从 CSS 开始看，先顺着一次真实操作理解数据怎么流动。

### 1. 上传 + 预览 + 分析（`/analysis`）

```text
选择文件
  → FileUploader 校验扩展名和大小，emit('selected')
  → AnalysisView.handleFileSelected：file.text() 本地读一遍，预览区立刻有内容
  → 点击「上传到后端」→ emit('upload')
  → AnalysisView.handleUpload
  → document.js: uploadDocument()          POST /api/documents/upload
  → document.js: getDocument()             GET  /api/documents/{id}
  → 把文档写入 stores/currentDocument.js   （问答页要读）
  → 点击「AI 分析文档」
  → analysis.js: analyzeDocument()         POST /api/analysis/document
  → AnalysisResult.vue 按字段分区渲染
```

### 2. 提问（`/qa`）

```text
QABox 收集问题 → QAView.handleQuestion
  ├─ 普通模式：qa.js: askDocumentQuestion()   POST /api/qa/
  │             后端只在这份文档的索引片段里检索（RAG）
  └─ Agent 模式：agent.js: runAgent()          POST /api/agent
                返回 tool_calls 数组，页面把「用了哪些工具」拼在回答前面
                （后端有 4 个工具：list_documents 列文档、search_documents 检索、
                  summarize_document 整篇总结、compare_documents 对比。按文件名提问时
                  模型会先 list_documents 把文件名换成编号，所以回答前的工具名里
                  常能看到它）
  → 结果追加到 messages，QABox 渲染并自动滚到底部
```

### 4. 查看已保存的分析结果（`/analysis?documentId=3`）

```text
在 /documents 点某一行的「查看分析结果」
  → DocumentsView.goAnalysis(doc)
  → 先把这份文档写进 stores/currentDocument.js（问答页要读）
  → router.push({ path: '/analysis', query: { documentId: doc.document_id } })
  → AnalysisView 检测到 route.query.documentId，进入「查看模式」（isViewMode）
  → document.js: getDocument(id)                GET /api/documents/{id}
  → analysis.js: getAnalysisRecord(id)          GET /api/analysis/document/{id}
        ├─ 200：AnalysisResult 渲染 result 字段
        └─ 404：不报错，显示空态，引导点「开始分析」
```

查看模式会**自动隐去上传区和正文预览**，左侧只留一张文档信息卡，避免和「首次分析」的流程混淆。想重新生成结果就点卡片里的按钮，它调用的仍然是 `POST /api/analysis/document`。

> ⚠️ 这里有一个容易踩的坑：后端 `GET /analysis/document/{id}` 返回的结构是
> `{ document_id, record_id, analysis_type, created_at, result: { 摘要 / 关键点 / … } }`，
> 真正要渲染的字段都**套在 `result` 里**，所以 `api/analysis.js` 负责把它拆平：
> `result: response.result`。如果直接把整条响应交给 `AnalysisResult.vue`，
> 页面会显示「后端暂未返回摘要 / 暂无关键点」——因为它在最外层找不到 `summary`。

> 地址上用的是 query（`?documentId=3`）而不是路由参数（`/analysis/3`），这样 `/analysis` 依然是同一条路由，不需要改 `router/index.js`。

### 5. 管理文档（`/documents`）

```text
进页面 → knowledge.js: listDocuments()   GET    /api/documents
建索引 → knowledge.js: indexDocument()   POST   /api/qa/index/{id}
查看结果 → 跳到 /analysis?documentId={id}
删除   → knowledge.js: deleteDocument()  DELETE /api/documents/{id}
```

---

## 四、接口封装（`src/api/`）

请求层故意保持简单：一个通用实例，加按业务拆分的文件。

| 文件 | 负责的接口 | 前端请求路径 |
|---|---|---|
| `http.js` | axios 实例、响应拦截器（把后端 `detail` 转成 `Error.message`，并附带 `status` / `isNotFound`） | — |
| `document.js` | 上传 / 文档详情 / 只看文件名 | `/api/documents/upload`、`/api/documents/{id}`、`/api/documents/name/{id}` |
| `analysis.js` | AI 结构化分析 / 读取已保存结果 | `/api/analysis/document`（POST）、`/api/analysis/document/{id}`（GET） |
| `qa.js` | 单文档（RAG）问答 | `/api/qa/`（注意尾斜杠） |
| `knowledge.js` | 文档列表 / 建立索引 / 删除 | `/api/documents`、`/api/qa/index/{id}`、`/api/documents/{id}` |
| `agent.js` | Agent 模式 | `/api/agent`（没有尾斜杠） |

> `/qa/` 带尾斜杠（后端装饰器是 `@router.post("/")`），`/agent` 和 `/documents` 不带（装饰器是 `@router.post("")`）。这两个写法不同是刻意的：写成 `/` 会触发 307 跳转。

---

## 五、核心文件与阅读顺序

### 第 1 步：应用如何启动

1. `src/main.js`
2. `src/App.vue`
3. `src/router/index.js`
4. `src/components/AppHeader.vue`

先理解：Vue 应用如何创建、路由如何挂载、页面如何显示到 `RouterView`。

### 第 2 步：核心业务页面

5. `src/views/AnalysisView.vue`（最核心）
6. `src/components/FileUploader.vue`
7. `src/components/DocumentPreview.vue`
8. `src/components/AnalysisResult.vue`

### 第 3 步：问答与 Agent

9. `src/views/QAView.vue`
10. `src/components/QABox.vue`
11. `src/stores/currentDocument.js`

重点理解：分析页上传成功后文档 ID 存在哪里，问答页怎么拿到它，Agent 模式为什么可以不需要当前文档。

### 第 4 步：文档管理

12. `src/views/DocumentsView.vue`
13. `src/api/knowledge.js`

### 第 5 步：请求层

14. `src/api/http.js`
15. 其余 `src/api/*.js`

### 第 6 步：最后看样式

16. `src/styles/base.css`
17. 各 `.vue` 文件底部的 `<style scoped>`

---

## 六、样式约定（想改外观时看这里）

### 设计变量都在 `src/styles/base.css` 的 `:root` 里

| 变量 | 用途 |
|---|---|
| `--primary-color` / `--primary-hover` / `--primary-soft` | 主色（按钮、导航高亮、步骤标签） |
| `--accent-color` / `--accent-soft` | 辅助色（文档类型标记、成功底色） |
| `--success-text` | 成功文字色（浅绿底上的深绿字） |
| `--warning-color` / `--warning-soft` | 警告（未索引、本地预览） |
| `--danger-color` / `--danger-soft` | 错误与删除 |
| `--text-strong` / `--text-secondary` / `--text-muted` | 三级文字颜色 |
| `--surface-color` / `--surface-muted` | 卡片底色 / 次级底色 |
| `--border-color` / `--shadow-card` / `--shadow-soft` | 边框与阴影 |

改主题色基本只需要动这几个变量，不用逐个组件改。

### 公共类也在 `base.css`

| 类名 | 用途 |
|---|---|
| `.card` | 白色卡片 |
| `.page-heading` / `.eyebrow` | 页面标题区 |
| `.primary-button` / `.secondary-button` / `.ghost-button`（可加 `.small`） | 三种按钮 |
| `.status-message.error` / `.success` | 提示条 |
| `.step-label` | 「步骤 1 / 2 / 3」小标题 |
| `.status-badge.ready` / `.local` | 文档预览右上角的状态胶囊 |
| `.loading-dot` | 加载小圆点 |

### 其他约定

- 全局有 `:focus-visible` 焦点圈，键盘 Tab 能看清当前焦点；
- 有 `prefers-reduced-motion` 分支，系统开启「减少动态效果」时动画全部关闭；
- 表格在窄屏是**横向滚动**（`.table-wrap`），不是隐藏列；
- 分析结果卡片（`.analysis-result`）**自身限高 + 内部滚动**（`max-height: min(720px, 78vh)`）。AI 返回十几条关键点时不会把整张卡片拉得很长；点标题右侧的「展开全部」换成页面整体滚动（`.is-expanded` 去掉限高）。
  - 标题**故意不做 `position: sticky`**：卡片自己是滚动容器，吸顶会让标题在页面滚动时停在半空、和卡片边框脱开，看起来像浮在内容上面。让标题跟着内容一起滚更自然。
  - 卡片内边距写在 `.analysis-result` 自己身上，不要再叠一层 `.card` 的默认内边距，否则会被算两次。

### 想改某处样式时

| 想改什么 | 改哪里 |
|---|---|
| 颜色、字体、按钮、卡片 | `src/styles/base.css` |
| 首页布局 | `src/views/HomeView.vue` |
| 分析页布局 | `src/views/AnalysisView.vue` |
| 分析结果查看模式的样式 | `src/views/AnalysisView.vue` 的 `.view-grid`、`.document-summary` |
| 上传框、拖拽区 | `src/components/FileUploader.vue` |
| 预览区、复制按钮 | `src/components/DocumentPreview.vue` |
| 分析结果卡片 | `src/components/AnalysisResult.vue` |
| 问答框、快捷问题 | `src/components/QABox.vue` |
| 问答页文档卡片、Agent 开关 | `src/views/QAView.vue` |
| 文档列表表格 | `src/views/DocumentsView.vue` |
| 顶部导航 | `src/components/AppHeader.vue` |

---

## 七、以后要改功能时改哪里

### 后端地址或端口变了

开发环境代理：`vite.config.js` 的 `proxy.target`。

### 接口路径或请求字段变了

改 `src/api/` 下对应文件（见第四节表格）。如果基础地址、超时时间、错误处理要统一改，再动 `http.js`。

### 后端返回字段变了

先改页面接收数据的位置，再改展示组件：

| 数据 | 位置 |
|---|---|
| 上传 / 详情返回 | `AnalysisView.vue` 的 `handleUpload` |
| 分析结果字段 | `AnalysisResult.vue` |
| 分析历史记录字段 | `AnalysisView.vue` 的 `loadAnalysisRecord`（`record_id` / `created_at` 目前没展示，想显示就加在文档信息卡里） |
| 问答返回 | `QAView.vue` 的 `handleQuestion` |
| 列表 / 索引状态 | `DocumentsView.vue` 的 `loadDocuments`、`handleIndex` |

### 想增加一个新页面

1. 在 `src/views/` 新建页面组件；
2. 在 `src/router/index.js` 增加一条路由；
3. 在 `src/components/AppHeader.vue` 增加导航入口；
4. 需要请求后端就在 `src/api/` 新建对应文件。

不要一开始就抽象通用页面配置。先把一个页面完整写明白，出现重复后再考虑抽取组件。

---

## 八、当前已知限制

- 问答记录**不落库**，只存在 `QAView.vue` 的内存里，刷新即丢；
- 分析历史**只能看最新一条**（`GET /api/analysis/document/{id}` 取的是 `id` 最大的那条），没有列表页，也不能对比两次结果；
- 只支持 TXT / Markdown（前端限制 2MB），PDF、Word、OCR 未支持；
- 删除文档没有二次确认之外的软删除，删掉即无法恢复；
- 没有登录、权限和部署配置。

---

## 九、验证清单（改完前端后照着点一遍）

1. 打开首页，四个导航项都能跳转，当前页导航高亮；
2. 上传一个 `.txt` / `.md`：选错扩展名或超过 2MB 应被前端拦下并给提示；
3. 预览区显示后端返回的正文，点「复制全文」提示变成「已复制」；
4. 点「AI 分析文档」，右侧四个区块（摘要 / 关键点 / 行动项 / 关键词）正常渲染；
5. 去 `/documents`：列表有数据、显示索引状态，能「建立索引」「去提问」「查看分析结果」「删除」；
6. 点某一行的「查看分析结果」→ 跳到 `/analysis?documentId=x`，左侧显示文档信息、右侧显示上次的分析结果；换一份没分析过的文档应当显示空态 + 「开始分析」，控制台**不应**出现红色报错；
7. 在 `/qa` 提问，回答能显示；开启「Agent 模式」后提问，回答前会显示调用了哪些工具（问「doc.md 的主要内容是什么」时，工具名里应出现 `list_documents`）；
8. 把窗口缩到手机宽度：导航变横向滑动标签，表格可横向滚动，按钮不重叠。
