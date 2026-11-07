<!-- 作用：串联文件选择、上传、正文预览和 AI 结构化分析的完整流程。
     带 ?documentId=123 打开时进入「查看模式」：只展示已保存的分析结果，可手动点重新分析。 -->
<template>
  <div class="analysis-page">
    <header class="page-heading analysis-heading">
      <div>
        <p class="eyebrow">{{ isViewMode ? 'Saved analysis' : 'Document analysis' }}</p>
        <h1>{{ isViewMode ? '分析结果查看' : '文档分析工作台' }}</h1>
        <p v-if="isViewMode">下面展示的是上一次的分析结果。需要最新结果时，可以点「重新分析」。</p>
        <p v-else>先上传并确认解析内容，再调用 AI 生成结构化结果。当前只处理 TXT 和 Markdown。</p>
      </div>
      <div v-if="!isViewMode" class="scope-note">
        <span>当前阶段</span>
        <strong>上传 → 预览 → 分析</strong>
        <small>分析结果会落库；问答走 RAG 检索，PDF / Word 仍未支持</small>
      </div>
      <RouterLink v-else class="secondary-button small" to="/documents">← 返回文档管理</RouterLink>
    </header>

    <!-- ============ 查看模式：只显示文档信息 + 已保存的分析结果 ============ -->
    <div v-if="isViewMode" class="view-grid">
      <div class="left-column">
        <section class="card document-summary">
          <div class="section-title">
            <h2>文档信息</h2>
            <!-- <span class="status-badge ready">已保存</span> -->
          </div>
          <dl class="summary-list">
            <div class="summary-row">
              <dt>文件名</dt>
              <dd>{{ viewDocument?.filename || '加载中…' }}</dd>
            </div>
            <div class="summary-row">
              <dt>文档 ID</dt>
              <dd>{{ documentId }}</dd>
            </div>
            <div class="summary-row">
              <dt>字符数</dt>
              <dd>{{ viewDocument?.length ?? '—' }}</dd>
            </div>
            <div v-if="viewedAt" class="summary-row">
              <dt>分析保存于</dt>
              <dd>{{ viewedAt }}</dd>
            </div>
          </dl>
          <p class="summary-note">需要看正文，请到「文档分析」页重新上传同一份文件；本页只负责展示结果。</p>
        </section>

        <section class="card action-card">
          <div>
            <p class="action-label">重新分析</p>
            <h2>{{ analysisResult ? '结果已加载' : '还没有保存的结果' }}</h2>
            <p>
              {{
                analysisResult
                  ? '后端保存新一条记录,前端查看取最新记录'
                  : '这份文档目前没有保存过分析结果，点下面按钮发起第一次分析。'
              }}
            </p>
          </div>
          <button
            class="primary-button analyze-button"
            :disabled="!documentId || analyzing"
            @click="handleAnalyze"
          >
            <span v-if="analyzing" class="loading-dot" />
            {{ analyzing ? '正在分析文档' : (analysisResult ? '重新分析' : '开始分析') }}
          </button>
          <RouterLink class="qa-link" :to="{ path: '/qa' }">针对这份文档提问 →</RouterLink>
          <p v-if="analysisError" class="status-message error">{{ analysisError }}</p>
        </section>
      </div>

      <div class="right-column">
        <AnalysisResult :result="analysisResult" :loading="analyzing || loadingRecord" />
      </div>
    </div>

    <!-- ============ 正常模式：上传 → 预览 → 分析 ============ -->
    <div v-else class="workspace-grid">
      <div class="left-column">
        <!-- 文件上传区域 -->
        <FileUploader :uploading="uploading" 
          @selected="handleFileSelected" @upload="handleUpload" />
        <p v-if="uploadError" class="status-message error">{{ uploadError }}</p>

        <!-- 文档预览区域 -->
        <DocumentPreview
          :document="previewDocument"
          :content="localContent"
          :uploaded="Boolean(uploadedDocument?.document_id)"
        />
      </div>

      <div class="right-column">
        <!-- 下一步操作：上传成功后按钮才可用 -->
        <section class="action-card card">
          <div>
            <p class="action-label">步骤 3</p>
            <h2>{{ uploadedDocument ? '文档已准备好' : '等待上传文档' }}</h2>
            <p>
              {{
                uploadedDocument
                  ? '点击按钮后，后端会读取文档并调用 DeepSeek 返回结构化 JSON。'
                  : '只有上传成功并获得 document_id 后，才能发起 AI 分析。'
              }}
            </p>
          </div>
          <button
            class="primary-button analyze-button"
            :disabled="!uploadedDocument?.document_id || analyzing"
            @click="handleAnalyze"
          >
            <span v-if="analyzing" class="loading-dot" />
            {{ analyzing ? '正在分析文档' : 'AI 分析文档' }}
          </button>
          <RouterLink v-if="uploadedDocument?.document_id" class="qa-link" to="/qa">
            暂不分析，直接针对文档提问 →
          </RouterLink>
          <p v-if="analysisError" class="status-message error">{{ analysisError }}</p>
        </section>

        <!-- 分析结果区域 -->
        <AnalysisResult :result="analysisResult" :loading="analyzing" />
      </div>
    </div>
  </div>
</template>


<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { analyzeDocument, getAnalysisRecord } from '../api/analysis'
import { getDocument, uploadDocument } from '../api/document'
import AnalysisResult from '../components/AnalysisResult.vue'
import DocumentPreview from '../components/DocumentPreview.vue'
import FileUploader from '../components/FileUploader.vue'
import { useCurrentDocument } from '../stores/currentDocument'

const route = useRoute()
const { setCurrentDocument } = useCurrentDocument()

const selectedFile = ref(null)
const localContent = ref('')
const uploadedDocument = ref(null)
const analysisResult = ref(null)
const uploading = ref(false)
const analyzing = ref(false)
const uploadError = ref('')
const analysisError = ref('')

// ===== 查看模式相关状态 =====
// 地址里带 documentId 就是查看模式，例如：/analysis?documentId=3
const viewDocument = ref(null)
const loadingRecord = ref(false)
const viewedAt = ref('')   // 这条分析结果的保存时间

onMounted(() => {
  if (isViewMode.value) loadAnalysisRecord()
})

const documentId = computed(() => {
  const id = route.query.documentId
  return id ? Number(id) : null
})

const isViewMode = computed(() => Boolean(documentId.value))

const previewDocument = computed(() => {
  if (uploadedDocument.value) return uploadedDocument.value
  if (!selectedFile.value) return null

  return {
    filename: selectedFile.value.name,
    file_type: selectedFile.value.name.split('.').pop(),
    length: localContent.value.length,
  }
})

// 在查看页里再点另一份文档时，地址变了但组件不会重建，所以手动再读一次
watch(documentId, (value) => {
  if (value) {
    loadAnalysisRecord()
  } else {
    analysisResult.value = null
    analysisError.value = ''
    viewDocument.value = null
    viewedAt.value = ''
  }
})

// 浏览器先读取一次文本，用户不必等后端完成就能检查选错文件的问题。
async function handleFileSelected(file) {
  selectedFile.value = file
  uploadedDocument.value = null
  analysisResult.value = null
  uploadError.value = ''
  analysisError.value = ''

  try {
    localContent.value = await file.text()
  } catch {
    localContent.value = ''
    uploadError.value = '浏览器读取文件失败，请重新选择文档。'
  }
}

// 上传成功后继续请求文档详情，保证预览展示的是后端实际保存的内容。
async function handleUpload(file) {
  uploading.value = true
  uploadError.value = ''
  analysisResult.value = null

  try {
    // 调用上传接口
    const uploadResponse = await uploadDocument(file)
    let detail = null

    try {
      detail = await getDocument(uploadResponse.document_id)
    } catch {
      // 如果详情接口还没完成，先使用上传接口返回的 preview，不阻塞 Day 10 联调。
      detail = null
    }

    // 上传接口返回的 preview 可能是空字符串，优先使用后端实际保存的内容。
    uploadedDocument.value = {
      ...uploadResponse,
      ...detail,
      content: detail?.content || detail?.text || uploadResponse.preview || localContent.value,
    }

    // 将上传成功的文档内容存入本地状态，方便预览和后续分析。
    localContent.value = uploadedDocument.value.content
    // 将上传成功的文档信息存入全局状态，方便后续在 QA 页面使用。
    setCurrentDocument({
      document_id: uploadedDocument.value.document_id,
      filename: uploadedDocument.value.filename,
      file_type: uploadedDocument.value.file_type,
      length: uploadedDocument.value.length,
    })
  } catch (error) {
    uploadError.value = error.message
  } finally {
    uploading.value = false
  }
}

// 分析接口只接收 document_id，避免前端重复拼接 Prompt 或暴露模型密钥。
async function handleAnalyze() {
  const targetId = documentId.value || uploadedDocument.value?.document_id
  if (!targetId) return

  analyzing.value = true
  analysisError.value = ''
  let result = null

  try {

    if(isViewMode.value && analysisResult.value){
      // 查看模式下，如果已经有分析结果了，就发起「重新分析」请求
      result = await analyzeDocument(targetId, true)
    }
    else{
    // 否则就是正常模式，第一次分析或重新分析都走同一个接口
      result = await analyzeDocument(targetId)
    }

    analysisResult.value = result

    // 把最新分析结果存入全局状态，方便 QA 页面使用。
    setCurrentDocument({
      document_id: targetId,
      filename: uploadedDocument.value?.filename || viewDocument?.filename || `文档 #${targetId}`,
      file_type: uploadedDocument.value?.file_type || viewDocument?.file_type || '',
      length: uploadedDocument.value?.length || viewDocument?.length || 0,
      analysisQuestions: result?.questions || [],
    })

  } catch (error) {
    analysisError.value = error.message
  } finally {
    analyzing.value = false
  }
}

// 查看模式：读文档基本信息 + 上一次保存的分析结果
async function loadAnalysisRecord() {
  if (!documentId.value) return

  loadingRecord.value = true
  analysisError.value = ''
  analysisResult.value = null
  viewDocument.value = null
  viewedAt.value = ''

  // 两个请求互不依赖，一起发出去更快；用 allSettled 是为了一个失败不影响另一个
  const [documentRes, recordRes] = await Promise.allSettled([
    getDocument(documentId.value),
    getAnalysisRecord(documentId.value),
  ])

  if (documentRes.status === 'fulfilled') {
    const detail = documentRes.value
    viewDocument.value = detail

    // 让问答页也知道「当前文档」是哪一份
    setCurrentDocument({
      document_id: detail.document_id ?? documentId.value,
      filename: detail.filename,
      file_type: detail.file_type,
      length: detail.length,
    })
  } else {
    analysisError.value = documentRes.reason?.message || '读取文档信息失败'
  }

  if (recordRes.status === 'fulfilled') {
    // 注意：这里取的是 result（后端那层包装已在 api/analysis.js 里拆掉了），
    // 直接把整条响应丢给结果卡片会渲染成空，因为字段在外层套着的 result 里。
    analysisResult.value = recordRes.value.result
    viewedAt.value = recordRes.value.createdAt || ''

    if(viewDocument.value){
      // 让问答页也知道「当前文档」的分析结果
      setCurrentDocument({
        document_id: viewDocument.value.document_id ?? documentId.value,
        filename: viewDocument.value.filename,
        file_type: viewDocument.value.file_type,
        length: viewDocument.value.length,
        analysisQuestions: recordRes.value.result?.questions || [],
      })
    }
  } else if (!recordRes.reason?.isNotFound) {
    // 404 表示「还没分析过」，属于正常情况，不当成错误提示
    analysisError.value = recordRes.reason?.message || '读取分析结果失败'
  }

  loadingRecord.value = false
}


</script>


<style scoped>
.analysis-page {
  display: grid;
  gap: 28px;
}

.analysis-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 30px;
}

.scope-note {
  min-width: 260px;
  padding: 16px 18px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.scope-note span,
.scope-note strong,
.scope-note small {
  display: block;
}

.scope-note span {
  margin-bottom: 6px;
  color: var(--primary-color);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.1em;
}

.scope-note strong {
  margin-bottom: 5px;
  font-size: 14px;
}

.scope-note small {
  color: var(--text-muted);
  line-height: 1.55;
}

.workspace-grid,
.view-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(340px, 0.95fr);
  align-items: start;
  gap: 18px;
}

/* 查看模式左边只是信息卡，不需要那么宽 */
.view-grid {
  grid-template-columns: minmax(0, 0.8fr) minmax(360px, 1.2fr);
}

.left-column,
.right-column {
  min-width: 0;
  display: grid;
  gap: 18px;
}

/* ===== 查看模式的文档信息卡 ===== */
.document-summary {
  padding: 22px 24px;
}

.summary-list {
  display: grid;
  gap: 10px;
  margin: 0;
}

.summary-row {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 10px;
  align-items: baseline;
}

.summary-row dt {
  color: var(--text-muted);
  font-size: 12px;
}

.summary-row dd {
  min-width: 0;
  margin: 0;
  color: var(--text-strong);
  font-size: 13px;
  word-break: break-all;
}

.summary-note {
  margin: 16px 0 0;
  padding-top: 14px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
  border-top: 1px dashed var(--border-color);
}

.action-card {
  padding: 24px;
  display: grid;
  gap: 15px;
  background:
    linear-gradient(145deg, rgba(70, 89, 217, 0.06), rgba(255, 255, 255, 0.9)),
    #fff;
}

.action-label {
  margin-bottom: 5px;
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.action-card h2 {
  margin-bottom: 8px;
  font-size: 21px;
}

.action-card > div > p:last-child {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.analyze-button {
  width: 100%;
  min-height: 48px;
}

.qa-link {
  justify-self: center;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

@media (max-width: 920px) {
  .analysis-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .scope-note {
    min-width: 0;
    width: 100%;
  }

  .workspace-grid,
  .view-grid {
    grid-template-columns: 1fr;
  }
}
</style>
