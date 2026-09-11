import axios from 'axios'
import { ElMessage } from 'element-plus'

// 根据环境自动判断API地址
const getApiBaseURL = () => {
  // 开发环境和生产环境都使用相对路径，通过代理转发
  // 开发环境：Vite 代理到 http://localhost:6001
  // 生产环境：Nginx 代理到 http://localhost:6001
  return '/api'
}

const service = axios.create({
  baseURL: getApiBaseURL(),
  timeout: 60000, // 文件上传需要更长时间
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 如果是 FormData，不设置 Content-Type，让浏览器自动设置（包括 boundary）
    if (config.data instanceof FormData) {
      // 不设置 Content-Type，让 axios/browser 自动处理
    } else if (!config.headers['Content-Type']) {
      // 其他请求默认使用 JSON
      config.headers['Content-Type'] = 'application/json'
    }
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 如果是blob类型（文件下载），直接返回response
    if (response.config.responseType === 'blob' || response.data instanceof Blob) {
      return response
    }
    return response.data
  },
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default service

