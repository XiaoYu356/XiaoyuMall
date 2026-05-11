import router from '@/router'
import { ElMessage } from 'element-plus'

const permissionList = []

export function setPermissionList(permissions) {
  permissionList.length = 0
  permissionList.push(...permissions)
}

export function getPermissionList() {
  return permissionList
}

export function hasPermission(permission) {
  if (!permission) return true
  const permissions = getPermissionList()
  if (permissions.includes('*')) return true
  return permissions.includes(permission)
}

export function checkPermission(permission) {
  if (!hasPermission(permission)) {
    ElMessage.error('没有操作权限')
    return false
  }
  return true
}

export function checkRoutePermission(to) {
  const permission = to.meta?.permission
  if (!permission) return true
  
  if (!hasPermission(permission)) {
    ElMessage.error('没有访问权限')
    router.push('/403')
    return false
  }
  return true
}
