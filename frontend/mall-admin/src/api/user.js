import request from './request'

export const login = (data) => {
  return request({ url: '/v1/users/login', method: 'post', data })
}

export const register = (data) => {
  return request({ url: '/v1/users/register', method: 'post', data })
}

export const createUser = (data) => {
  return request({ url: '/v1/users/create', method: 'post', data })
}

export const getCurrentUserInfo = () => {
  return request({ url: '/v1/users/info', method: 'get' })
}

export const getUserInfo = (userId) => {
  return request({ url: `/v1/users/${userId}`, method: 'get' })
}

export const getUserList = (params) => {
  return request({ url: '/v1/users', method: 'get', params })
}

export const updateUser = (data) => {
  return request({ url: '/v1/users', method: 'put', data })
}

export const deleteUser = (userId) => {
  return request({ url: `/v1/users/${userId}`, method: 'delete' })
}
