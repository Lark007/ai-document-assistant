<!-- 作用：读取当前文档信息，调用后端问答接口，并维护本次页面会话记录。 -->
<template>
  <div class="qa-page">
    <header class="page-heading qa-heading">
      <div>
        <p class="eyebrow">Contextual Q&A</p>
        <h1>知识问答</h1>
        <p>围绕一份已上传文档继续追问。</p>
      </div>
      <RouterLink class="secondary-button" to="/documents">查看文档列表</RouterLink>
    </header>

    <section v-if="hasDocument && !useAgentMode" class="current-document card">
      <div class="document-mark">{{ currentDocument.file_type?.toUpperCase() || 'DOC' }}</div>
      <div>
        <small>当前文档</small>
        <strong>{{ currentDocument.filename }}</strong>
        <p>
          文档 ID：{{ currentDocument.document_id }}
          <span v-if="currentDocument.length">· {{ currentDocument.length }} 个字符</span>
        </p>
      </div>
      <!-- 直接跳回分析页重新选文档，比在问答页手动输入 ID 更顺手 -->
      <RouterLink class="secondary-button small" to="/documents">更换文档</RouterLink>
    </section>

    <section v-else-if="!hasDocument" class="manual-document card">
      <div>
        <p class="manual-label">未检测到当前文档</p>
        <h2>先选择一份已上传的文档</h2>
        <p>推荐到「文档分析」页上传；如果后端已有数据，也可以直接填写 document_id 调试接口。</p>
      </div>
      <div class="manual-form">
        <label>
          <span>文档 ID</span>
          <input v-model="manualDocumentId" inputmode="numeric" placeholder="例如：1" />
        </label>
        <label>
          <span>显示名称（可选）</span>
          <input v-model="manualFilename" placeholder="例如：fastapi_notes.md" />
        </label>
        <button class="primary-button" @click="useManualDocument">使用这份文档</button>
      </div>
    </section>

    <!-- Agent 模式开关：放在提问框之前，用户先决定用哪种方式问 -->
    <label class="agent-toggle card">
      <input v-model="useAgentMode" type="checkbox" />
      <span>
        <strong>Agent 模式</strong>
        <small>
          模型自己决定要不要用工具：跨文档搜索、总结整篇、比较两份文档。开启后不再限制在当前文档内。
        </small>
      </span>
    </label>

    <p v-if="errorMessage" class="status-message error">{{ errorMessage }}</p>

    <!-- 问答框 -->
    <QABox
      :disabled="!hasDocument && !useAgentMode"
      :loading="loading"
      :messages="messages"
      :analysisQuestions="analysisQuestions"
      @submit="handleQuestion"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

import { runAgent } from '../api/agent'
import { getDocumentName } from '../api/document'
import { askDocumentQuestion } from '../api/qa'
import QABox from '../components/QABox.vue'
import { useCurrentDocument } from '../stores/currentDocument'

const { currentDocument, setCurrentDocument } = useCurrentDocument()

const manualDocumentId = ref('')
const manualFilename = ref('')
const messages = ref([])
const loading = ref(false)
const errorMessage = ref('')
const useAgentMode = ref(false)     // 是否使用 Agent 模式

const hasDocument = computed(() => Boolean(currentDocument.value?.document_id))
const analysisQuestions = computed(() => currentDocument.value?.analysisQuestions || [])


// 直接访问 /qa 时可手动输入文档 ID，便于单独调试问答接口。
async function useManualDocument() {
  const documentId = Number(manualDocumentId.value)
  let documentInfo = null
  if (!Number.isInteger(documentId) || documentId <= 0) {
    errorMessage.value = '请输入有效的正整数文档 ID。'
    return
  } 
  
  try {
    documentInfo = await getDocumentName(documentId)
  } catch (error) {
    errorMessage.value = "无法获取文档信息，请检查文档 ID 是否正确。"
    return
  }

  if (!documentInfo) {
    errorMessage.value = "文档信息为空，无法加载。"
    return
  }

  setCurrentDocument({
    document_id: documentInfo.document_id,
    filename: documentInfo.filename?.trim() || `文档 #${documentId}`,
  })
  messages.value = []
  errorMessage.value = ''
}

// 把用户问题先显示出来，再等待后端回答，失败时保留问题便于重新尝试。
async function handleQuestion(question) {
  // Agent 模式不需要先选文档（它可以跨文档搜索）
  if (loading.value) return
  if (!useAgentMode.value && !hasDocument.value) return

  messages.value.push({ role: 'user', content: question })
  loading.value = true
  errorMessage.value = ''

  try {
    if (useAgentMode.value) {
      const result = await runAgent(question)
      // 同名工具只显示一次：Agent 可能把同一个工具调用好几轮
      const tools = [...new Set(result.tool_calls || [])]
      // 把「用了什么工具」拼进正文
      const toolLine = tools.length ? `🔧 调用了 ${tools.join('、')}\n\n` : ''
      messages.value.push({
        role: 'assistant',
        content: toolLine + (result.answer || '后端没有返回 answer 字段。'),
      })
    } else {
      const response = await askDocumentQuestion(currentDocument.value.document_id, question)
      messages.value.push({
        role: 'assistant',
        content: response.answer || '后端没有返回 answer 字段。',
        references: response.references || [],
      })
    }
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.qa-page {
  display: grid;
  gap: 20px;
}

.qa-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
}

.qa-heading .secondary-button {
  flex: 0 0 auto;
  text-decoration: none;
}

.agent-toggle {
  padding: 15px 18px;
  display: flex;
  align-items: flex-start;
  gap: 11px;
  cursor: pointer;
  transition: 0.2s ease;
}

.agent-toggle:hover {
  border-color: #c8cefb;
}

.agent-toggle input {
  width: 16px;
  height: 16px;
  margin-top: 3px;
  flex: 0 0 auto;
  accent-color: var(--primary-color);
}

.agent-toggle span {
  min-width: 0;
}

.agent-toggle strong {
  display: block;
  margin-bottom: 3px;
  font-size: 14px;
}

.agent-toggle small {
  display: block;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.current-document {
  padding: 17px 19px;
  display: grid;
  /* 中间那一列可以收缩，文件名再长也不会把按钮挤出卡片 */
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
}

.document-mark {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  color: var(--accent-color);
  font-size: 10px;
  font-weight: 800;
  border-radius: 13px;
  background: var(--accent-soft);
}

.current-document small,
.current-document strong {
  display: block;
}

.current-document small {
  margin-bottom: 3px;
  color: var(--text-muted);
  font-size: 10px;
}

.current-document strong {
  font-size: 14px;
  overflow-wrap: anywhere;
}

.current-document p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.manual-document {
  padding: 24px;
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  align-items: center;
  gap: 30px;
}

.manual-label {
  margin-bottom: 5px;
  color: var(--warning-color);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.manual-document h2 {
  margin-bottom: 8px;
  font-size: 21px;
}

.manual-document > div > p:last-child {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.manual-form {
  display: grid;
  grid-template-columns: 0.55fr 1fr auto;
  align-items: end;
  gap: 10px;
}

.manual-form label span {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
}

.manual-form input {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  color: var(--text-strong);
  border: 1px solid var(--border-color);
  border-radius: 11px;
  outline: none;
}

.manual-form input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-soft);
}

@media (max-width: 850px) {
  .qa-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .manual-document,
  .manual-form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .current-document {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .current-document .secondary-button {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
