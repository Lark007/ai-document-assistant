<!-- 作用：结构化展示，把后端返回的结构化分析拆分为摘要、关键点、关键词和行动项。 -->

<template>
  <section class="analysis-result card" :class="{ 'is-expanded': expanded }">
    <div class="section-title">
      <div>
        <p class="step-label">步骤 4</p>
        <h2>AI 结构化分析</h2>
      </div>
      <div class="title-actions">
        <button
          v-if="result"
          class="ghost-button small"
          type="button"
          @click="expanded = !expanded"
        >
          {{ expanded ? '收起' : '展开全部' }}
        </button>
        <span>Structured Output</span>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="thinking-mark">AI</span>
      <div>
        <strong>正在阅读文档</strong>
        <p>后端正在调用模型并整理结构化结果，请稍候。</p>
      </div>
    </div>

    <div v-else-if="result" class="result-content">
      <article class="summary-block">
        <span class="block-index">01</span>
        <div>
          <h3>文档摘要</h3>
          <p>{{ result.summary || '后端暂未返回摘要。' }}</p>
        </div>
      </article>

      <div class="result-grid">
        <article class="result-block">
          <span class="block-index">02</span>
          <h3>关键点</h3>
          <ul v-if="safeList(result.key_points).length">
            <li v-for="item in safeList(result.key_points)" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-copy">暂无关键点</p>
        </article>

        <article class="result-block">
          <span class="block-index">03</span>
          <h3>行动项</h3>
          <ul v-if="safeList(result.action_items).length">
            <li v-for="item in safeList(result.action_items)" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-copy">暂无行动项</p>
        </article>
      </div>

      <article class="keyword-block">
        <div class="keyword-heading">
          <span class="block-index">04</span>
          <h3>关键词</h3>
        </div>
        <div v-if="safeList(result.keywords).length" class="keyword-list">
          <span v-for="keyword in safeList(result.keywords)" :key="keyword">{{ keyword }}</span>
        </div>
        <p v-else class="empty-copy">暂无关键词</p>
      </article>

      <article v-if="safeList(result.questions).length" class="question-block">
        <h3>可以继续追问</h3>
        <p v-for="question in safeList(result.questions)" :key="question">{{ question }}</p>
      </article>
    </div>

    <div v-else class="empty-state">
      <span>✦</span>
      <strong>分析结果将在这里展开</strong>
      <p>上传文档后点击“AI 分析文档”，前端会按字段展示后端返回的 JSON。</p>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  result: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

// AI 的结果可能很长（摘要好几段、关键点十几条），默认让卡片内部滚动，
// 免得整张卡片被拉得比旁边的文档信息卡长出一大截；点「展开全部」看完整内容。
const expanded = ref(false)

function safeList(value) {
  return Array.isArray(value) ? value : []
}
</script>

<style scoped>
.analysis-result {
  /* 卡片自己管内边距，和 .card 的默认内边距保持一致即可，
     注意别再把内边距叠到 .card 上，否则会被算两次。 */
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: min(720px, 78vh);
  padding: 24px;
  overflow-y: auto;
  overscroll-behavior: contain;
}

/* 点「展开全部」后不再限制高度，页面整体滚动 */
.analysis-result.is-expanded {
  max-height: none;
  overflow-y: visible;
}

/* 标题不吸顶：卡片本身是滚动容器，吸顶会让它在页面滚动时留在半空中，
   和卡片边框脱开，看起来像浮在内容上面。让标题跟着内容一起滚最自然。 */
.section-title {
  margin-bottom: 0;
  padding-bottom: 14px;
}

.title-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}

.loading-state,
.empty-state {
  min-height: 230px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: var(--text-secondary);
}

.thinking-mark,
.empty-state > span {
  width: 50px;
  height: 50px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #fff;
  font-size: 14px;
  font-weight: 800;
  border-radius: 16px;
  background: linear-gradient(145deg, #8c55cb, var(--primary-color));
  box-shadow: 0 10px 26px rgba(100, 74, 190, 0.2);
  animation: breathe 1.4s ease-in-out infinite;
}

.loading-state strong,
.empty-state strong {
  display: block;
  margin-bottom: 5px;
  color: var(--text-strong);
}

.loading-state p,
.empty-state p {
  max-width: 390px;
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.65;
}

.empty-state {
  flex-direction: column;
  text-align: center;
}

.empty-state > span {
  animation: none;
}

.result-content {
  display: grid;
  gap: 14px;
}

.summary-block,
.result-block,
.keyword-block,
.question-block {
  position: relative;
  padding: 18px;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  background: #fbfcff;
}

.summary-block {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
}

.block-index {
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.result-content h3 {
  margin: 0 0 9px;
  font-size: 15px;
}

.result-content p,
.result-content li {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.75;
}

.summary-block p,
.question-block p {
  margin-bottom: 0;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.result-block ul {
  margin: 0;
  padding-left: 18px;
}

.result-block li + li {
  margin-top: 6px;
}

.keyword-heading {
  display: flex;
  gap: 12px;
}

.keyword-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-list span {
  padding: 6px 10px;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
  background: var(--primary-soft);
}

.question-block {
  background: var(--accent-soft);
  border-color: #cce9e4;
}

.question-block p + p {
  margin-top: 6px;
}

.empty-copy {
  margin: 0;
  color: var(--text-muted) !important;
}

@keyframes breathe {
  0%,
  100% {
    transform: scale(0.96);
  }
  50% {
    transform: scale(1.04);
  }
}

@media (max-width: 600px) {
  .analysis-result {
    /* 手机屏幕矮，限制再收一点 */
    max-height: 66vh;
    padding: 18px;
  }

  /* 空态也跟着变矮，否则矮屏上会平白多出一根滚动条 */
  .loading-state,
  .empty-state {
    min-height: 170px;
  }

  .title-actions span {
    display: none;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
