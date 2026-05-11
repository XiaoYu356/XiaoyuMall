import request from './request'

export const uploadFile = (formData) => {
  return request({ url: '/v1/upload', method: 'post', data: formData, headers: { 'Content-Type': 'multipart/form-data' } })
}

export const getCategoryList = () => {
  return request({ url: '/v1/products/categories', method: 'get' })
}

export const createCategory = (data) => {
  return request({ url: '/v1/products/categories', method: 'post', data })
}

export const updateCategory = (data) => {
  return request({ url: '/v1/products/categories', method: 'put', data })
}

export const deleteCategory = (categoryId) => {
  return request({ url: `/v1/products/categories/${categoryId}`, method: 'delete' })
}

export const getProductStats = () => {
  return request({ url: '/v1/products/stats', method: 'get' })
}

export const getProductList = (params) => {
  return request({ url: '/v1/products', method: 'get', params })
}

export const getProductById = (productId) => {
  return request({ url: `/v1/products/${productId}`, method: 'get' })
}

export const createProduct = (data) => {
  return request({ url: '/v1/products', method: 'post', data })
}

export const updateProduct = (data) => {
  return request({ url: '/v1/products', method: 'put', data })
}

export const deleteProduct = (productId) => {
  return request({ url: `/v1/products/${productId}`, method: 'delete' })
}

export const getProductSkus = (productId) => {
  return request({ url: `/v1/products/${productId}/skus`, method: 'get' })
}
