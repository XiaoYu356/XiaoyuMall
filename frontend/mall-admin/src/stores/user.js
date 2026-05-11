import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as userApi from '@/api/user'
import { setPermissionList } from '@/utils/permission'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const permissions = ref([])
  const roles = ref([])

  const isLoggedIn = computed(() => !!token.value)

  const login = async (loginForm) => {
    const res = await userApi.login(loginForm)
    token.value = res.data
    localStorage.setItem('token', res.data)
    return res
  }

  const logout = () => {
    token.value = ''
    userInfo.value = null
    permissions.value = []
    roles.value = []
    setPermissionList([])
    localStorage.removeItem('token')
  }

  const getUserInfo = async () => {
    if (!token.value) return null

    try {
      const res = await userApi.getCurrentUserInfo()
      const data = res.data
      userInfo.value = data.user
      permissions.value = data.permissions || []
      roles.value = data.roles || []
      setPermissionList(data.permissions || [])
      return data.user
    } catch (error) {
      logout()
      throw error
    }
  }

  const setPermissions = (perms) => {
    permissions.value = perms
    setPermissionList(perms)
  }

  const setRoles = (rs) => {
    roles.value = rs
  }

  const init = async () => {
    if (token.value && !userInfo.value) {
      await getUserInfo()
    }
  }

  return {
    token,
    userInfo,
    permissions,
    roles,
    isLoggedIn,
    login,
    logout,
    getUserInfo,
    setPermissions,
    setRoles,
    init
  }
})
