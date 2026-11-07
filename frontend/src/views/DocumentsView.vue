<!-- 作用：文档管理页。列出数据库里的全部文档，显示索引状态，并可建立索引、删除、跳去提问。 -->
<template>
  <div class="documents-page">
    <header class="page-heading">
      <p class="eyebrow">Document library</p>
      <h1>文档管理</h1>
      <p>
        这里列出数据库里保存的所有文档，以及它们有没有建立索引。
        没有索引的文档在被提问前，需要先点一下「建立索引」。
        点「查看分析结果」可以看到这份文档上一次保存的结构化分析。
      </p>
    </header>

    <section class="card list-card">
      <div class="section-title">
        <h2>共 {{ docList.length }} 份文档</h2>
        <button class="secondary-button" :disabled="loading" @click="loadDocuments">
          {{ loading ? '加载中…' : '刷新' }}
        </button>
      </div>

      <p v-if="errorMessage" class="status-message error">{{ errorMessage }}</p>

      <div v-if="loading && !docList.length" class="hint">正在读取文档列表…</div>

      <div v-else-if="!docList.length" class="hint">
        还没有任何文档。先去「文档分析」页上传一份 TXT 或 Markdown。
      </div>

      <!-- 文档列表 -->
      <div v-else class="table-wrap">
        <table class="doc-table">
          <!-- 表头 -->
          <thead>
            <tr>
              <th>ID</th>
              <th>文件名</th>
              <th>字数</th>
              <th>上传时间</th>
              <th>索引状态</th>
              <th>分析状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <!-- 文档列表 -->
          <tbody>
            <tr v-for="doc in docList" :key="doc.document_id">
              <td>{{ doc.document_id }}</td>
              <td class="name">{{ doc.filename }}</td>
              <td>{{ doc.length }}</td>
              <td class="time">{{ doc.created_at }}</td>
              <td>
                <span v-if="doc.indexed" class="badge ok">已索引 · {{ doc.chunks }} 段</span>
                <span v-else class="badge warn">未索引</span>
              </td>
              <td>
                <span v-if="doc.analyzed" class="badge ok">已分析</span>
                <span v-else class="badge warn">未分析</span>
              </td>
              <!-- 操作列 -->
              <td class="actions">
                <!-- 建立索引按钮 -->
                <button
                  class="primary-button small"
                  :disabled="indexingId === doc.document_id || deletingId === doc.document_id"
                  @click="handleIndex(doc)"
                >
                  {{ indexingId === doc.document_id ? '索引中…' : (doc.indexed ? '重新索引' : '建立索引') }}
                </button>
                <!-- 提问按钮 -->
                <button
                  class="ghost-button small"
                  :disabled="!doc.indexed"
                  @click="goAsk(doc)"
                >
                  去提问
                </button>
                <!-- 查看这份文档上一次保存的分析结果 -->
                <button
                  class="ghost-button small analyze-btn"
                  :disabled="deletingId === doc.document_id"
                  @click="goAnalysis(doc)"
                >
                  {{doc.analyzed ? '查看分析结果' : '开始分析'}}
                </button>
                <!-- 删除按钮 -->
                <button
                  class="ghost-button small danger"
                  :disabled="deletingId === doc.document_id || indexingId === doc.document_id"
                  @click="handleDelete(doc)"
                >
                  {{ deletingId === doc.document_id ? '删除中…' : '删除' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { deleteDocument, indexDocument, listDocuments } from '../api/knowledge'
import { useCurrentDocument } from '../stores/currentDocument'

const router = useRouter()
const { currentDocument, setCurrentDocument } = useCurrentDocument()

// 变量名故意不叫 documents，避免和浏览器全局的 document 混淆
const docList = ref([])
const loading = ref(false)
const indexingId = ref(null)      // 正在建索引的文档 id
const deletingId = ref(null)      // 正在删除的文档 id
const errorMessage = ref('')

// 拉取列表
async function loadDocuments() {
  loading.value = true
  errorMessage.value = ''
  try {
    docList.value = await listDocuments()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}

// 给一份文档建索引；成功后直接改这一行的数据，不用重新拉列表
async function handleIndex(doc) {
  indexingId.value = doc.document_id
  errorMessage.value = ''
  try {
    const result = await indexDocument(doc.document_id)
    doc.indexed = true
    doc.chunks = result.chunks
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    indexingId.value = null
  }
}

// 删除一份文档（后端会一起删掉分析记录和索引片段）
async function handleDelete(doc) {
  const ok = window.confirm(
    `确定删除「${doc.filename}」（ID ${doc.document_id}）吗？\n它的分析记录和索引片段会一起删掉，无法恢复。`,
  )
  if (!ok) return

  deletingId.value = doc.document_id
  errorMessage.value = ''
  try {
    await deleteDocument(doc.document_id)
    // 如果删的正好是问答页正在用的那份文档，顺手清掉，免得问答页还拿着一个已经不存在的 id
    if (currentDocument.value?.document_id === doc.document_id) {
      setCurrentDocument(null)
    }
    // 从列表里去掉这一行，不用重新拉全部
    docList.value = docList.value.filter((item) => item.document_id !== doc.document_id)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    deletingId.value = null
  }
}

// 把这份文档设为「当前文档」，然后跳到问答页
function goAsk(doc) {
  setCurrentDocument({
    document_id: doc.document_id,
    filename: doc.filename,
    file_type: doc.file_type,
    length: doc.length,
  })
  router.push("/qa")
}

// 跳到分析页的「查看模式」，只展示已经保存的结果，不会自动发起新分析
function goAnalysis(doc) {
  setCurrentDocument({
    document_id: doc.document_id,
    filename: doc.filename,
    file_type: doc.file_type,
    length: doc.length,
  })
  router.push({ path: '/analysis', query: { documentId: doc.document_id } })
}

onMounted(loadDocuments)
</script>

<style scoped>
.documents-page {
  display: grid;
  gap: 28px;
}

.list-card {
  padding: 24px;
}

.hint {
  padding: 40px 0;
  color: var(--text-muted);
  text-align: center;
}

.table-wrap {
  overflow-x: auto;
}

.doc-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
  font-size: 13px;
}

.doc-table th {
  padding: 10px 8px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border-color);
}

.doc-table td {
  padding: 12px 8px;
  color: var(--text-secondary);
  vertical-align: middle;
  border-bottom: 1px solid var(--border-color);
}

/* 鼠标停在哪一行，哪一行就有一点底色，方便一行一行看。 */
.doc-table tbody tr:hover td {
  background: var(--surface-muted);
}

/* 最后一行不再需要分隔线 */
.doc-table tbody tr:last-child td {
  border-bottom: 0;
}

.doc-table .name {
  color: var(--text-strong);
  font-weight: 600;
  overflow-wrap: anywhere;
}

.doc-table .time {
  color: var(--text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.badge {
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  border-radius: 999px;
}

.badge.ok {
  color: var(--success-text);
  background: var(--accent-soft);
}

.badge.warn {
  color: var(--warning-color);
  background: var(--warning-soft);
}

.actions {
  display: flex;
  gap: 6px;
}
/* 分析按钮 */
.analyze-btn {
  min-width: 8em;         /* 短文案也撑到同宽 */
  text-align: center;    /* 文字居中，不再左对齐随字宽伸缩 */
  white-space: nowrap;   /* 窄屏时文字不换行 */
}


/* 删除按钮：红色文字，平时不抢眼 */
.ghost-button.danger {
  color: var(--danger-color);
}

.ghost-button.danger:hover:not(:disabled) {
  background: var(--danger-soft);
}

@media (max-width: 640px) {
  .list-card {
    padding: 18px;
  }

  /* 窄屏下按钮换行排列，不要互相挤在一起 */
  .actions {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
