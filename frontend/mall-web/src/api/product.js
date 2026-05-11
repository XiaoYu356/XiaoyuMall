import request from './request'

export const getProductList = (params) => {
  return request({ url: '/v1/products', method: 'get', params })
}

export const getProductById = (id) => {
  return request({ url: `/v1/products/${id}`, method: 'get' })
}

export const getProductSkus = (productId) => {
  return request({ url: `/v1/products/${productId}/skus`, method: 'get' })
}

export const getCategories = () => {
  return request({ url: '/v1/products/categories', method: 'get' })
}
