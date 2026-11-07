// 作用：创建统一的 Axios 实例，并把常见后端错误转换为可读提示。
// 接口地址优先读取 .env 中的 VITE_API_BASE_URL。
import axios from 'axios'

const http = axios.create({
  // baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  baseURL: "/api",
  timeout: 60_000,
})

// 响应拦截器：将后端返回的错误信息转换为可读提示。
http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error.response?.data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : error.message || '请求失败，请检查后端服务是否启动。'

    const result = new Error(message)
    // 把状态码带出去：页面需要区分「404 还没结果」和「真的出错」
    result.status = error.response?.status
    result.isNotFound = error.response?.status === 404
    return Promise.reject(result)
  },
)

export default http
