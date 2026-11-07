<!-- 作用：首页负责说明项目价值、当前边界，并引导用户进入文档分析流程。 -->
<template>
  <div class="home-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">AI Document Workspace</p>
        <h1>把长文档变成<br /><span>清晰、可追问的知识</span></h1>
        <p class="hero-description">
          面向学习、求职和开发场景的文档分析工具。上传文本后完成内容预览、结构化总结，
          再围绕同一份文档继续提问。
        </p>
        <div class="hero-actions">
          <RouterLink class="primary-button" to="/analysis">开始分析文档 <span>→</span></RouterLink>
          <RouterLink class="secondary-button" to="/qa">进入知识问答</RouterLink>
        </div>

        <div v-if="currentDocument" class="recent-document">
          <span class="recent-dot" />
          <div>
            <small>当前文档</small>
            <strong>{{ currentDocument.filename }}</strong>
          </div>
          <RouterLink to="/qa">继续提问</RouterLink>
        </div>
      </div>

      <div class="hero-visual" aria-label="产品流程示意">
        <div class="visual-topbar">
          <div class="window-dots"><i /><i /><i /></div>
          <span>document-workspace</span>
          <span class="online-mark">Online</span>
        </div>
        <div class="visual-body">
          <aside>
            <div class="aside-logo">AI</div>
            <span class="aside-item active" />
            <span class="aside-item" />
            <span class="aside-item short" />
          </aside>
          <div class="visual-content">
            <div class="visual-heading">
              <div>
                <span />
                <span />
              </div>
              <b>MD</b>
            </div>
            <div class="document-lines">
              <i /><i /><i /><i /><i />
            </div>
            <div class="analysis-panel">
              <div class="spark">✦</div>
              <div>
                <strong>AI Summary</strong>
                <span /><span /><span />
              </div>
            </div>
            <div class="keyword-row"><span>FastAPI</span><span>Vue 3</span><span>RAG</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="feature-section">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Current version · V1.0</p>
          <h2>从一个小闭环长到 RAG + Agent</h2>
        </div>
        <p>仍然不做登录、复杂文档格式和部署，先把「检索到来源、Agent 会选工具」这两件事讲清楚。</p>
      </div>

      <div class="feature-grid">
        <article v-for="feature in features" :key="feature.number" class="feature-card card">
          <span>{{ feature.number }}</span>
          <h3>{{ feature.title }}</h3>
          <p>{{ feature.description }}</p>
        </article>
      </div>
    </section>

    <section class="flow-section card">
      <div>
        <p class="eyebrow">How it works</p>
        <h2>四步完成一次文档分析</h2>
      </div>
      <ol>
        <li v-for="(step, index) in steps" :key="step">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <strong>{{ step }}</strong>
        </li>
      </ol>
    </section>
  </div>
</template>


<script setup>
import { useCurrentDocument } from '../stores/currentDocument';

const { currentDocument } = useCurrentDocument()

const features = [
  {
    number: '01',
    title: '文档上传与预览',
    description: '支持 TXT 与 Markdown，上传后先在浏览器里确认解析到的文本是否正确。',
  },
  {
    number: '02',
    title: '结构化内容分析',
    description: '把模型返回的摘要、关键点、关键词和行动项分区展示，字段固定、格式稳定。',
  },
  {
    number: '03',
    title: 'RAG 检索问答',
    description: '文档切块并建立索引后，只把最相关的片段交给模型，回答有来源、不全靠全文。',
  },
  {
    number: '04',
    title: '最小 Agent',
    description: 'Agent 自己决定调用搜索、总结还是对比工具，页面上会显示它用了哪些工具。',
  },
]

const steps = ['选择 TXT / Markdown', 'FastAPI 解析并入库', 'DeepSeek 结构化分析', '建立索引后检索提问']
</script>


<style scoped>
.home-page {
  display: grid;
  gap: clamp(52px, 7vw, 76px);
}

.hero {
  min-height: 570px;
  display: grid;
  grid-template-columns: 0.93fr 1.07fr;
  align-items: center;
  gap: clamp(36px, 7vw, 90px);
}

.hero h1 {
  margin-bottom: 22px;
  font-size: clamp(44px, 6vw, 70px);
  line-height: 1.06;
  letter-spacing: -0.052em;
}

.hero h1 span {
  color: var(--primary-color);
}

.hero-description {
  max-width: 590px;
  margin-bottom: 28px;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.9;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-actions a {
  min-height: 48px;
  text-decoration: none;
}

.recent-document {
  width: fit-content;
  max-width: 100%;
  margin-top: 24px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
}

.recent-dot {
  width: 9px;
  height: 9px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--accent-color);
  box-shadow: 0 0 0 5px var(--accent-soft);
}

.recent-document small,
.recent-document strong {
  display: block;
}

.recent-document small {
  color: var(--text-muted);
  font-size: 10px;
}

.recent-document strong {
  max-width: 250px;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-document a {
  margin-left: 8px;
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}

.hero-visual {
  overflow: hidden;
  border: 1px solid #dfe3ee;
  border-radius: 24px;
  background: #fff;
  box-shadow: var(--shadow-soft);
  transform: rotate(1.2deg);
}

.visual-topbar {
  height: 52px;
  padding: 0 18px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  color: var(--text-muted);
  font-size: 11px;
  border-bottom: 1px solid var(--border-color);
}

.window-dots {
  display: flex;
  gap: 5px;
}

.window-dots i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d2d7e1;
}

.online-mark {
  justify-self: end;
  color: var(--accent-color);
  font-weight: 700;
}

.visual-body {
  min-height: 450px;
  display: grid;
  grid-template-columns: 76px 1fr;
}

.visual-body aside {
  padding: 22px 17px;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 17px;
  border-right: 1px solid var(--border-color);
  background: #fafbfe;
}

.aside-logo {
  width: 38px;
  height: 38px;
  margin-bottom: 12px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  border-radius: 12px;
  background: var(--primary-color);
}

.aside-item {
  width: 30px;
  height: 7px;
  border-radius: 99px;
  background: #dfe3ed;
}

.aside-item.active {
  background: var(--primary-color);
}

.aside-item.short {
  width: 20px;
}

.visual-content {
  padding: 32px;
  background: linear-gradient(155deg, #fff, #f8f9fd);
}

.visual-heading {
  padding-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
}

.visual-heading > div {
  width: 54%;
  display: grid;
  gap: 8px;
}

.visual-heading span,
.document-lines i,
.analysis-panel span {
  height: 8px;
  display: block;
  border-radius: 99px;
  background: #dfe3ed;
}

.visual-heading span:last-child {
  width: 62%;
}

.visual-heading b {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: var(--primary-color);
  font-size: 11px;
  border-radius: 12px;
  background: var(--primary-soft);
}

.document-lines {
  margin: 24px 0;
  display: grid;
  gap: 11px;
}

.document-lines i:nth-child(2) { width: 91%; }
.document-lines i:nth-child(3) { width: 74%; }
.document-lines i:nth-child(4) { width: 86%; }
.document-lines i:nth-child(5) { width: 58%; }

.analysis-panel {
  padding: 18px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  border: 1px solid #dcdffc;
  border-radius: 17px;
  background: var(--primary-soft);
}

.spark {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  color: #fff;
  border-radius: 11px;
  background: var(--primary-color);
}

.analysis-panel strong {
  display: block;
  margin-bottom: 12px;
  font-size: 12px;
}

.analysis-panel span {
  height: 6px;
  margin-top: 7px;
  background: #cbd0fa;
}

.analysis-panel span:nth-child(3) { width: 82%; }
.analysis-panel span:nth-child(4) { width: 64%; }

.keyword-row {
  margin-top: 16px;
  display: flex;
  gap: 7px;
}

.keyword-row span {
  padding: 6px 9px;
  color: var(--text-secondary);
  font-size: 10px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: #fff;
}

.feature-section {
  display: grid;
  gap: 26px;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 30px;
}

.section-heading h2,
.flow-section h2 {
  margin-bottom: 0;
  font-size: clamp(27px, 4vw, 38px);
  letter-spacing: -0.035em;
}

.section-heading > p {
  max-width: 450px;
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.75;
}

.feature-grid {
  display: grid;
  /* 四张卡片排成 2 × 2，比一行挤四张更好读。 */
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.feature-card {
  min-height: 190px;
  padding: 25px;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-soft);
}

.feature-card > span {
  color: var(--primary-color);
  font-size: 12px;
  font-weight: 800;
}

.feature-card h3 {
  margin: 40px 0 12px;
  font-size: 20px;
}

.feature-card p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.75;
}

.flow-section {
  padding: 32px;
  display: grid;
  grid-template-columns: 0.75fr 1.25fr;
  align-items: center;
  gap: 44px;
}

.flow-section ol {
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  list-style: none;
}

.flow-section li {
  min-height: 88px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  border-radius: 15px;
  background: var(--surface-muted);
}

.flow-section li span {
  color: var(--primary-color);
  font-size: 11px;
  font-weight: 800;
}

.flow-section li strong {
  font-size: 13px;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .hero-copy {
    max-width: 700px;
  }

  .hero-visual {
    max-width: 680px;
  }

  .section-heading,
  .flow-section {
    align-items: start;
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .home-page {
    gap: 54px;
  }

  .hero {
    min-height: auto;
  }

  .hero h1 {
    font-size: clamp(38px, 12vw, 52px);
  }

  .visual-body {
    grid-template-columns: 54px 1fr;
  }

  .visual-body aside {
    padding: 18px 8px;
  }

  .visual-content {
    padding: 20px;
  }

  .feature-grid,
  .flow-section ol {
    grid-template-columns: 1fr;
  }

  .feature-card {
    min-height: 0;
  }

  .feature-card h3 {
    margin-top: 26px;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
