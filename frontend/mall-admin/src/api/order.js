import request from './request'

export const getOrderStats = () => {
  return request({ url: '/v1/orders/stats', method: 'get' })
}

export const getOrderList = (params) => {
  return request({ url: '/v1/orders', method: 'get', params })
}

export const getOrderById = (orderId) => {
  return request({ url: `/v1/orders/${orderId}`, method: 'get' })
}

export const createOrder = (data) => {
  return request({ url: '/v1/orders', method: 'post', data })
}

export const cancelOrder = (orderId) => {
  return request({ url: `/v1/orders/${orderId}/cancel`, method: 'post' })
}

export const shipOrder = (orderId) => {
  return request({ url: `/v1/orders/${orderId}/ship`, method: 'post' })
}

export const payOrder = (orderId) => {
  return request({ url: `/v1/orders/${orderId}/pay`, method: 'post' })
}

export const confirmReceive = (orderId) => {
  return request({ url: `/v1/orders/${orderId}/receive`, method: 'post' })
}
