// 作用：创建 Vue 应用，加载路由和全局样式。
// 这是浏览器执行前端代码时的第一个 JavaScript 文件。
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/base.css'

createApp(App).use(router).mount('#app')
