<!-- 作用：展示已选或已上传文档的名称、长度和可滚动正文预览。 -->
<script setup>
import { ref } from 'vue'

const props = defineProps({
  document: {
    type: Object,
    default: null,
  },
  content: {
    type: String,
    default: '',
  },
  uploaded: {
    type: Boolean,
    default: false,
  },
})

function fileLabel(document) {
  const type = document?.file_type || document?.filename?.split('.').pop() || 'TEXT'
  return String(type).toUpperCase()
}

// 复制按钮的两秒反馈：copied 为 true 时按钮文字变成「已复制」。
const copied = ref(false)
let copiedTimer = null

async function copyContent() {
  if (!props.content) return

  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    clearTimeout(copiedTimer)
    copiedTimer = setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    // 浏览器不允许写剪贴板（例如不是 https 或用户拒绝授权）时，安静地不做反馈
  }
}
</script>

<template>
  <section class="preview card">
    <div class="section-title">
      <div>
        <p class="step-label">步骤 2</p>
        <h2>文档预览</h2>
      </div>
      <div class="preview-actions">
        <button v-if="content" class="ghost-button small" type="button" @click="copyContent">
          {{ copied ? '已复制' : '复制全文' }}
        </button>
        <span :class="['status-badge', uploaded ? 'ready' : 'local']">
          {{ uploaded ? '后端解析成功' : '本地预览' }}
        </span>
      </div>
    </div>

    <div v-if="document" class="document-meta">
      <div class="file-type">{{ fileLabel(document) }}</div>
      <div class="meta-info">
        <strong>{{ document.filename }}</strong>
        <p>
          {{ document.length ?? content.length }} 个字符
          <span v-if="document.document_id">· ID {{ document.document_id }}</span>
        </p>
      </div>
    </div>

    <div class="content-box" :class="{ empty: !content }">
      <pre v-if="content">{{ content }}</pre>
      <div v-else class="empty-state">
        <span>文</span>
        <strong>还没有可预览的内容</strong>
        <p>选择 TXT 或 Markdown 文件后，内容会显示在这里。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.preview {
  padding: 24px;
}

/* 标题右侧放「复制全文」和状态胶囊，窄屏时自动换行。 */
.preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.document-meta {
  margin-bottom: 14px;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--surface-muted);
}

.file-type {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--accent-color);
  font-size: 10px;
  font-weight: 800;
  border-radius: 12px;
  background: var(--accent-soft);
}

.meta-info {
  min-width: 0;
}

.document-meta strong {
  display: block;
  margin-bottom: 4px;
  overflow-wrap: anywhere;
}

.document-meta p {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
}

.content-box {
  /* 正文区高度跟着窗口走：大屏看得多，小屏不占满整屏 */
  height: clamp(280px, 42vh, 460px);
  padding: 18px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: #fbfcfe;
}

.content-box pre {
  margin: 0;
  color: #344055;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.content-box.empty {
  display: grid;
  place-items: center;
}

.empty-state {
  max-width: 300px;
  text-align: center;
}

.empty-state > span {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  display: grid;
  place-items: center;
  color: var(--text-muted);
  font-weight: 800;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: #fff;
}

.empty-state strong {
  display: block;
  margin-bottom: 6px;
}

.empty-state p {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 600px) {
  .preview {
    padding: 18px;
  }
}
</style>
