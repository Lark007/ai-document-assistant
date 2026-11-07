<!-- 作用：提供全站外壳，放置顶部导航，并显示当前路由页面。 -->
<script setup>
import AppHeader from './components/AppHeader.vue';
</script>

<template>
  <div class="app-shell">
    <!-- 顶部导航 -->
    <AppHeader />
    <!-- 页面内容容器 -->
    <main class="page-container">
      <RouterView />
    </main>
    <!-- 页脚 -->
    <footer class="app-footer">
      <span>AI Document Assistant</span>
      <span>Vue 3 · FastAPI · DeepSeek</span>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-container {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 44px 0 72px;
  flex: 1;
}

.app-footer {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding: 24px 0 36px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: var(--text-muted);
  font-size: 13px;
  letter-spacing: 0.01em;
  border-top: 1px solid var(--border-color);
}

@media (max-width: 640px) {
  .page-container {
    width: min(100% - 24px, 1180px);
    padding-top: 28px;
  }

  .app-footer {
    width: min(100% - 24px, 1180px);
    flex-direction: column;
  }
}
</style>
