<!-- 作用：展示项目名称和三个核心页面的导航入口。 -->
<template>
  <header class="app-header">
    <div class="nav-wrap">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">AI</span>
        <span>
          <strong>文档知识助手</strong>
          <small>Document Workspace</small>
        </span>
      </RouterLink>

      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/analysis">文档分析</RouterLink>
        <RouterLink to="/documents">文档管理</RouterLink>
        <RouterLink to="/qa">知识问答</RouterLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color) 84%, transparent);
  background: color-mix(in srgb, var(--surface-color) 88%, transparent);
  backdrop-filter: blur(18px);
  box-shadow: 0 1px 0 rgba(24, 34, 53, 0.02);
}

.nav-wrap {
  width: min(1180px, calc(100% - 40px));
  height: 72px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: var(--text-strong);
  text-decoration: none;
}

.brand-mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 800;
  border-radius: 12px;
  background: linear-gradient(145deg, var(--primary-color), #6c7cff);
  box-shadow: 0 8px 24px rgba(57, 79, 210, 0.24);
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 15px;
}

.brand small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-links a {
  padding: 9px 14px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
  border-radius: 10px;
  transition: 0.2s ease;
}

/* 用 router-link-active 而不是 router-link-exact-active：
   这样进入 /documents/xxx 之类的子路径时，父级导航项仍然保持高亮。 */
.nav-links a:hover,
.nav-links a.router-link-active {
  color: var(--primary-color);
  background: var(--primary-soft);
}

@media (max-width: 640px) {
  .nav-wrap {
    width: min(100% - 24px, 1180px);
    height: auto;
    padding: 12px 0;
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  /* 窄屏把导航做成一条可以横向滑动的标签栏，不换行、不挤压。 */
  .nav-links {
    width: 100%;
    padding-bottom: 2px;
    justify-content: flex-start;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .nav-links::-webkit-scrollbar {
    display: none;
  }

  .nav-links a {
    flex: 0 0 auto;
    padding: 9px 13px;
    text-align: center;
  }
}
</style>
