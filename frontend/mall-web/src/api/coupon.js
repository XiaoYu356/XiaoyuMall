import request from './request'

export const getAvailableCoupons = (params) => {
  return request({ url: '/v1/coupons/available', method: 'get', params })
}

export const receiveCoupon = (templateId) => {
  return request({ url: `/v1/coupons/receive/${templateId}`, method: 'post' })
}

export const getMyCoupons = (params) => {
  return request({ url: '/v1/coupons/mine', method: 'get', params })
}

export const calculateDiscount = (couponId, orderAmount) => {
  return request({ url: '/v1/coupons/calculate', method: 'post', params: { couponId, orderAmount } })
}
