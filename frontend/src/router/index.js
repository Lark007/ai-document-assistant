// 作用：定义首页、文档管理页、文档分析页和知识问答页的访问地址。
// 新增页面时，先在这里增加一条路由记录。
import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import DocumentsView from '../views/DocumentsView.vue'
import AnalysisView from '../views/AnalysisView.vue'
import QAView from '../views/QAView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/documents', name: 'documents', component: DocumentsView },
  { path: '/analysis', name: 'analysis', component: AnalysisView },
  { path: '/qa', name: 'qa', component: QAView },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

export default router
