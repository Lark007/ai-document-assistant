// 作用：配置 Vite 开发服务器，并把 /api 请求代理到本地 FastAPI。
// 后端端口变化时，只需要修改 proxy.target。
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    // port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        // 作用：去掉 /api 前缀，便于后端路由直接匹配。
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
