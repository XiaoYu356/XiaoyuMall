import { hasPermission } from '@/utils/permission'

export default {
  mounted(el, binding) {
    const permission = binding.value
    if (!hasPermission(permission)) {
      el.parentNode?.removeChild(el)
    }
  }
}

export function setupPermissionDirective(app) {
  app.directive('permission', {
    mounted(el, binding) {
      const permission = binding.value
      if (!hasPermission(permission)) {
        el.parentNode?.removeChild(el)
      }
    }
  })
}
