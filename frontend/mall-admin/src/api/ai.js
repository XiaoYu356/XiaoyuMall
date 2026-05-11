import request from './request'

export const analyzeProduct = (data) => {
  return request({ url: '/v1/ai/analyze', method: 'post', data })
}

export const quickAnalysis = (productId) => {
  return request({ url: '/v1/ai/analyze/product', method: 'post', data: { productId } })
}

export const priceAnalysis = (productId) => {
  return request({ url: '/v1/ai/analyze/price', method: 'post', data: { productId } })
}

export const couponAnalysis = (data) => {
  return request({ url: '/v1/ai/analyze/coupon', method: 'post', data })
}

export const streamAnalyze = async (data, onMessage, onError, onComplete) => {
  const baseURL = import.meta.env.VITE_API_URL || ''
  const token = localStorage.getItem('token')

  try {
    const response = await fetch(`${baseURL}/api/v1/ai/stream/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'satoken': token || ''
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const text = decoder.decode(value, { stream: true })
      const lines = text.split('\n')

      for (const line of lines) {
        if (line.startsWith('data:')) {
          const dataStr = line.substring(5).trim()
          if (dataStr === '[DONE]') {
            if (onComplete) onComplete()
            return
          }
          try {
            const parsed = JSON.parse(dataStr)
            if (onMessage) onMessage(parsed)
          } catch (e) {
            if (onMessage) onMessage({ content: dataStr })
          }
        }
      }
    }

    if (onComplete) onComplete()
  } catch (error) {
    if (onError) onError(error)
  }
}
