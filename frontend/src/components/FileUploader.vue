<!-- 作用：提供文件上传功能，允许用户选择并上传 TXT 或 Markdown 文件。 -->
<template>
  <section class="uploader card">
    <div class="section-title">
      <div>
        <p class="step-label">步骤 1</p>
        <h2>选择文档</h2>
      </div>
      <span>TXT / Markdown · 最大 2MB</span>
    </div>

    <!-- 拖拽上传区域 -->
    <div
      class="drop-zone"
      :class="{ dragging: isDragging }"
      role="button"
      :aria-label="selectedFile ? '重新选择文档' : '选择文档'"
      tabindex="0"
      @click="openFilePicker"
      @keydown.enter="openFilePicker"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        ref="inputRef"
        class="file-input"
        type="file"
        accept=".txt,.md,text/plain,text/markdown"
        @change="handleInput"
      />
      <span class="upload-icon">↥</span>
      <strong>{{ selectedFile ? '已选择文档' : '拖拽文件到这里，或点击选择' }}</strong>
      <small>选择后会先在浏览器中读取，方便检查文档内容</small>
    </div>

    <!-- 如果选中了文件，则显示文件信息 -->
    <div v-if="selectedFile" class="selected-file">
      <!-- 文件类型 -->
      <div class="file-type">{{ selectedFile.name.split('.').pop()?.toUpperCase() }}</div>
      <div class="file-info">
        <strong>{{ selectedFile.name }}</strong>
        <span>{{ formatFileSize(selectedFile.size) }}</span>
      </div>
      <button class="reselect-button" type="button" @click="openFilePicker">重新选择</button>
      <button class="primary-button" :disabled="uploading" @click="submitFile">
        <span v-if="uploading" class="loading-dot" />
        {{ uploading ? '正在上传' : '上传到后端' }}
      </button>
    </div>

    <p v-if="errorMessage" class="status-message error">{{ errorMessage }}</p>
  </section>
</template>


<!-- 作用：选择并校验 TXT/Markdown 文件，再把文件交给分析页上传。 -->
<script setup>
import { defineEmits, defineProps, ref } from 'vue'

defineProps({
  uploading: {
    type: Boolean,
    default: false,
  },
})

// 定义事件发射,传给父组件的
const emit = defineEmits(['selected', 'upload'])

const inputRef = ref(null)
const selectedFile = ref(null)
const errorMessage = ref('')
const isDragging = ref(false)

const allowedExtensions = ['txt', 'md']
const maxFileSize = 2 * 1024 * 1024

// 打开文件选择器
function openFilePicker() {
  inputRef.value?.click()
}

// 校验文件类型和大小
function validateFile(file) {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (!allowedExtensions.includes(extension)) {
    return '当前只支持 .txt 和 .md 文件，请重新选择。'
  }

  if (file.size > maxFileSize) {
    return '第一版限制文件不超过 2MB，请先选择较小的文本文件。'
  }

  return ''
}

// 处理选中的文件，并触发 selected 事件（即向父组件提交文件）
function setFile(file) {
  if (!file) return

  // 校验文件类型和大小
  const validationError = validateFile(file)
  if (validationError) {
    selectedFile.value = null
    errorMessage.value = validationError
    return
  }

  selectedFile.value = file
  errorMessage.value = ''
  emit('selected', file)
}

// 处理文件选择事件
function handleInput(event) {
  setFile(event.target.files?.[0])
}

// 处理拖拽事件
function handleDrop(event) {
  isDragging.value = false
  setFile(event.dataTransfer.files?.[0])
}

// 提交文件给父组件处理上传
function submitFile() {
  if (!selectedFile.value) {
    errorMessage.value = '请先选择一个文档。'
    return
  }

  // 调用上传接口在父组件处理
  emit('upload', selectedFile.value)
}

// 格式化文件大小为可读字符串
function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}
</script>

<style scoped>
.uploader {
  padding: 24px;
}

.drop-zone {
  min-height: 190px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--text-secondary);
  text-align: center;
  border: 1.5px dashed #c8cfdf;
  border-radius: 18px;
  background: var(--surface-muted);
  cursor: pointer;
  transition: 0.2s ease;
}

.drop-zone:hover,
.drop-zone:focus-visible,
.drop-zone.dragging {
  border-color: var(--primary-color);
  background: var(--primary-soft);
}

.file-input {
  display: none;
}

.upload-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: var(--primary-color);
  font-size: 28px;
  font-weight: 300;
  border-radius: 13px;
  background: #fff;
  box-shadow: 0 6px 18px rgba(70, 89, 217, 0.13);
}

.drop-zone strong {
  color: var(--text-strong);
  font-size: 15px;
}

.drop-zone small {
  color: var(--text-muted);
  line-height: 1.6;
}

.selected-file {
  margin-top: 14px;
  padding: 13px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
}

.file-type {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  border-radius: 12px;
  background: var(--primary-soft);
}

.file-info {
  min-width: 0;
}

.selected-file strong,
.selected-file span {
  display: block;
}

.selected-file strong {
  margin-bottom: 4px;
  font-size: 14px;
  overflow-wrap: anywhere;
}

.selected-file span {
  color: var(--text-muted);
  font-size: 12px;
}

/* 「重新选择」是一个轻量文字按钮，不跟右侧的主按钮抢注意力。 */
.reselect-button {
  padding: 6px 4px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  background: none;
  cursor: pointer;
}

.reselect-button:hover {
  color: var(--primary-color);
}

@media (max-width: 600px) {
  .uploader {
    padding: 18px;
  }

  .selected-file {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .selected-file .primary-button,
  .selected-file .reselect-button {
    grid-column: 1 / -1;
  }

  .selected-file .reselect-button {
    justify-self: start;
  }
}
</style>
