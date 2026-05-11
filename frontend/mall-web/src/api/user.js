import request from './request'

export const login = (data) => {
  return request({ url: '/v1/users/login', method: 'post', data })
}

export const register = (data) => {
  return request({ url: '/v1/users/register', method: 'post', data })
}

export const getUserInfo = () => {
  return request({ url: '/v1/users/info', method: 'get' })
}

export const updateUserInfo = (data) => {
  return request({ url: '/v1/users', method: 'put', data })
}

export const getAddressList = () => {
  return request({ url: '/v1/users/addresses', method: 'get' })
}

export const addAddress = (data) => {
  return request({ url: '/v1/users/addresses', method: 'post', data })
}

export const updateAddress = (data) => {
  return request({ url: '/v1/users/addresses', method: 'put', data })
}

export const deleteAddress = (addressId) => {
  return request({ url: `/v1/users/addresses/${addressId}`, method: 'delete' })
}

export const setDefaultAddress = (addressId) => {
  return request({ url: `/v1/users/addresses/${addressId}/default`, method: 'post' })
}
