import request from './request'

// ---- 知识库缺口 ----
export const getGapList = (params) => {
  return request({ url: '/v1/ai/knowledge/gaps', method: 'get', params })
}

export const updateGapStatus = (gapId, data) => {
  return request({ url: `/v1/ai/knowledge/gaps/${gapId}/status`, method: 'put', data })
}

// ---- FAQ 管理 ----
export const getFaqList = (params) => {
  return request({ url: '/v1/ai/knowledge/faqs', method: 'get', params })
}

export const createFaq = (data) => {
  return request({ url: '/v1/ai/knowledge/faqs', method: 'post', data })
}

export const updateFaq = (faqId, data) => {
  return request({ url: `/v1/ai/knowledge/faqs/${faqId}`, method: 'put', data })
}

export const deleteFaq = (faqId) => {
  return request({ url: `/v1/ai/knowledge/faqs/${faqId}`, method: 'delete' })
}

export const getCategories = () => {
  return request({ url: '/v1/ai/knowledge/categories', method: 'get' })
}

export const rebuildIndex = () => {
  return request({ url: '/v1/ai/knowledge/rebuild', method: 'post', timeout: 120000 })
}
