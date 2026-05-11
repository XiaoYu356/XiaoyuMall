import request from './request'

export const getCouponList = (params) => {
  return request({ url: '/v1/coupons', method: 'get', params })
}

export const createCoupon = (data) => {
  return request({ url: '/v1/coupons', method: 'post', data })
}

export const updateCoupon = (data) => {
  return request({ url: '/v1/coupons', method: 'put', data })
}

export const deleteCoupon = (templateId) => {
  return request({ url: `/v1/coupons/${templateId}`, method: 'delete' })
}
