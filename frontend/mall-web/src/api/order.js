import request from './request'

export const getOrderList = (params) => {
  return request({ url: '/v1/orders', method: 'get', params })
}

export const getOrderById = (id) => {
  return request({ url: `/v1/orders/${id}`, method: 'get' })
}

export const createOrder = (data) => {
  return request({ url: '/v1/orders', method: 'post', data })
}

export const payOrder = (id) => {
  return request({ url: `/v1/orders/${id}/pay`, method: 'post' })
}

export const cancelOrder = (id) => {
  return request({ url: `/v1/orders/${id}/cancel`, method: 'post' })
}

export const confirmReceive = (id) => {
  return request({ url: `/v1/orders/${id}/receive`, method: 'post' })
}
