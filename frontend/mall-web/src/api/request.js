import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
})

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['satoken'] = token
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

const handleUnauthorized = () => {
  localStorage.removeItem('token')
  const currentPath = router.currentRoute.value.path
  if (currentPath !== '/login') {
    ElMessage.warning('登录已过期，请重新登录')
    router.push('/login')
  }
}

const getErrorMessage = (data) => {
  if (!data) return '请求失败'
  if (typeof data === 'string') return data
  return data.message || data.msg || '请求失败'
}

request.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code !== 200) {
      if (res.code === 401) {
        handleUnauthorized()
      } else {
        ElMessage.error(getErrorMessage(res))
      }
      return Promise.reject(new Error(getErrorMessage(res)))
    }
    return res
  },
  error => {
    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      if (status === 401) {
        handleUnauthorized()
      } else if (status === 403) {
        ElMessage.error('没有权限访问')
      } else {
        ElMessage.error(getErrorMessage(data))
      }
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  }
)

export default request
