<!-- 作用：收集用户问题、提供快捷问题，并展示本次会话的问答记录。 -->
<template>
  <section class="qa-box card">
    <div class="section-title">
      <div>
        <p class="section-kicker">Ask the document</p>
        <h2>对文档或全库进行提问</h2>
      </div>
      <span>文档问答</span>
    </div>

    <div class="suggestions">
      <button
        v-for="item in suggestions"
        :key="item"
        type="button"
        :disabled="disabled || loading"
        @click="useSuggestion(item)"
      >
        {{ item }}
      </button>
    </div>

    <div ref="conversationRef" class="conversation">
      <!-- 空的会话 -->
      <div v-if="!messages.length" class="empty-conversation">
        <span>?</span>
        <strong>从一个具体问题开始</strong>
        <p>先检索这份文档里最相关的片段，再让模型只根据这些片段回答。</p>
      </div>

      <!-- 问答记录 -->
      <template v-else>
        <article v-for="(message, index) in messages" :key="`${message.role}-${index}`" :class="message.role">
          <span class="avatar">{{ message.role === 'user' ? '你' : 'AI' }}</span>
          <div>
            <small>{{ message.role === 'user' ? '我的问题' : '文档助手' }}</small>
            <p>{{ message.content }}</p>
            <!-- 新增：AI 回答下面显示引用片段 -->
            <div v-if="message.references?.length" class="references">
              <small class="refs-title">引用了 {{ message.references.length }} 段，以下百分比为与问题的相关度</small>
              <div v-for="(ref, i) in message.references" :key="i" class="ref-item">
                <span class="ref-score">{{ (ref.score * 100).toFixed(0) }}%</span>
                <span class="ref-text">{{ ref.text }}</span>
              </div>
            </div>
          </div>
        </article>
      </template>

      <!-- 加载中 -->
      <article v-if="loading" class="assistant pending">
        <span class="avatar">AI</span>
        <div>
          <small>文档助手</small>
          <p><span class="loading-dot" /> 正在根据文档内容组织回答…</p>
        </div>
      </article>
    </div>

    <!-- 问题输入框 -->
    <form class="question-form" @submit.prevent="submitQuestion">
      <textarea
        v-model="question"
        rows="3"
        :disabled="disabled || loading"
        placeholder="例如：这份 JD 是否要求 FastAPI？"
        @keydown.ctrl.enter="submitQuestion"
      />
      <div class="form-footer">
        <span>Ctrl + Enter 发送</span>
        <button class="primary-button" type="submit" :disabled="disabled || loading || !question.trim()">
          {{ loading ? '回答中' : '发送问题' }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup>
import { computed, defineEmits, defineProps, nextTick, ref, watch } from 'vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  messages: {
    type: Array,
    default: () => [],
  },
  analysisQuestions: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['submit'])

const question = ref('')
const conversationRef = ref(null)
const defaultSuggestions = [
  '这份文档最重要的三个知识点是什么？',
  '请列出文档中的关键步骤。',
  '这份文档有哪些需要继续学习的内容？',
]

const suggestions = computed(() => {
  const questions = props.analysisQuestions

  // 情况 1：有分析结果
  if (questions && questions.length) {
    console.log('有分析结果：', questions)
    return questions
  }

  // 情况 2：没有分析结果，就用默认的建议问题
  return defaultSuggestions
  
})

// 新消息进来（或开始等待回答）时，把会话区滚到底部，不用用户手动往下拉。
watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    const box = conversationRef.value
    if (box) box.scrollTop = box.scrollHeight
  },
)

function submitQuestion() {
  const value = question.value.trim()
  if (!value) return

  emit('submit', value)
  question.value = ''
}

function useSuggestion(value) {
  question.value = value
}
</script>

<style scoped>
.qa-box {
  padding: 28px;
}

.section-kicker {
  margin-bottom: 5px;
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.suggestions {
  margin-bottom: 18px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestions button {
  padding: 8px 11px;
  color: var(--text-secondary);
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
}

.suggestions button:hover:not(:disabled) {
  color: var(--primary-color);
  border-color: #c8cefb;
  background: var(--primary-soft);
}

.suggestions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.conversation {
  min-height: 330px;
  max-height: 520px;
  padding: 22px;
  overflow-y: auto;
  border: 1px solid var(--border-color);
  border-radius: 18px;
  background: var(--surface-muted);
}

.empty-conversation {
  min-height: 285px;
  display: grid;
  place-content: center;
  justify-items: center;
  text-align: center;
}

.empty-conversation > span {
  width: 48px;
  height: 48px;
  margin-bottom: 12px;
  display: grid;
  place-items: center;
  color: var(--primary-color);
  font-weight: 800;
  border-radius: 15px;
  background: var(--primary-soft);
}

.empty-conversation strong {
  margin-bottom: 6px;
}

.empty-conversation p {
  max-width: 400px;
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.65;
}

.conversation article {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.conversation article + article {
  margin-top: 18px;
}

.conversation .avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  border-radius: 11px;
  background: var(--primary-soft);
}

.conversation .user .avatar {
  color: var(--success-text);
  background: var(--accent-soft);
}

.conversation article > div {
  max-width: 82%;
}

.conversation small {
  display: block;
  margin-bottom: 5px;
  color: var(--text-muted);
}

.conversation p {
  margin: 0;
  padding: 11px 13px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.75;
  border: 1px solid var(--border-color);
  border-radius: 4px 14px 14px;
  background: #fff;
  white-space: pre-wrap;
}


.conversation .references {
  margin-top: 8px;
  padding: 10px 12px;
  border-left: 3px solid var(--primary-color);
  border-radius: 6px;
  background: var(--primary-soft);
}

.refs-title {
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-color);
}

.ref-item {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  line-height: 1.6;
}

.ref-score {
  flex: 0 0 auto;
  padding: 0 6px;
  height: 20px;
  line-height: 20px;
  color: #fff;
  font-size: 11px;
  border-radius: 6px;
  background: var(--primary-color);
}

.ref-text {
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;          /* 最多显示 3 行 */
  -webkit-box-orient: vertical;
  overflow: hidden;
}



.conversation .user {
  flex-direction: row-reverse;
}

.conversation .user > div {
  text-align: right;
}

.conversation .user p {
  color: #fff;
  text-align: left;
  border: 0;
  border-radius: 14px 4px 14px 14px;
  background: var(--primary-color);
}

.question-form {
  margin-top: 14px;
  padding: 13px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: #fff;
}

.question-form textarea {
  width: 100%;
  padding: 4px;
  color: var(--text-strong);
  line-height: 1.7;
  border: 0;
  outline: none;
  resize: vertical;
}

.question-form textarea::placeholder {
  color: #a1a9b8;
}

.form-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.form-footer span {
  color: var(--text-muted);
  font-size: 11px;
}

@media (max-width: 600px) {
  .qa-box {
    padding: 18px;
  }

  .conversation {
    padding: 15px;
  }

  .conversation article > div {
    max-width: 88%;
  }
}
</style>
