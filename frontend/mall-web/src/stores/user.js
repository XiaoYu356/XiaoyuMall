import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as userApi from '@/api/user'
import { ElMessage } from 'element-plus'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const permissions = ref([])
  const roles = ref([])

  const isLoggedIn = computed(() => !!token.value)

  async function login(loginData) {
    const res = await userApi.login(loginData)
    token.value = res.data
    localStorage.setItem('token', res.data)
    await fetchUserInfo()
    ElMessage.success('登录成功')
    return res
  }

  async function register(registerData) {
    const res = await userApi.register(registerData)
    ElMessage.success('注册成功')
    return res
  }

  async function fetchUserInfo() {
    if (!token.value) return
    try {
      const res = await userApi.getUserInfo()
      const data = res.data
      userInfo.value = data.user
      permissions.value = data.permissions || []
      roles.value = data.roles || []
    } catch (e) {
      logout()
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    permissions.value = []
    roles.value = []
    localStorage.removeItem('token')
  }

  function init() {
    if (token.value && !userInfo.value) {
      fetchUserInfo()
    }
  }

  return {
    token,
    userInfo,
    permissions,
    roles,
    isLoggedIn,
    login,
    register,
    fetchUserInfo,
    logout,
    init
  }
})
