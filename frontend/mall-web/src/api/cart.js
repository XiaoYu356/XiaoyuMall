import request from './request'

export const getCartList = () => {
  return request({ url: '/v1/cart', method: 'get' })
}

export const addCart = (data) => {
  return request({ url: '/v1/cart', method: 'post', data })
}

export const updateCart = (data) => {
  return request({ url: '/v1/cart', method: 'put', data })
}

export const deleteCart = (cartId) => {
  return request({ url: `/v1/cart/${cartId}`, method: 'delete' })
}

export const deleteCartBatch = (cartIds) => {
  return request({ url: '/v1/cart/batch', method: 'delete', data: cartIds })
}

export const clearCart = () => {
  return request({ url: '/v1/cart/clear', method: 'delete' })
}

export const selectAll = (selected) => {
  return request({ url: '/v1/cart/select-all', method: 'put', params: { selected } })
}
