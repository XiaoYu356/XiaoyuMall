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

export const getBrandList = () => {
  return request({ url: '/v1/products/brands', method: 'get' })
}

export const searchSuggest = (prefix) => {
  return request({ url: '/v1/products/es/suggest', method: 'get', params: { prefix } })
}

export const getHotSearches = (size = 10) => {
  return request({ url: '/v1/products/es/hot', method: 'get', params: { size } })
}

export const getSearchHistory = () => {
  return request({ url: '/v1/products/es/history', method: 'get' })
}

export const clearSearchHistory = () => {
  return request({ url: '/v1/products/es/history', method: 'delete' })
}

export const getSearchFilters = (params) => {
  return request({ url: '/v1/products/es/filters', method: 'get', params })
}
