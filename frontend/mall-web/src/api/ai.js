import axios from 'axios'

/**
 * AI 助手 v3 SSE 契约（Java 网关 /api/v1/ai/stream/v3/chat 原样转发 ai-service 帧）。
 * 每帧 event: <type> + data: <json>，须用 addEventListener(type) 监听：
 *   meta         {request_id, trace_url, served_by}                        首事件
 *   llm_chunk    {text}                                                    增量文本
 *   tool         {name, phase:'start'|'end', ok, elapsed_ms?}              工具调用
 *   product_card {items:[{id,name,price,image,sales}]}                     商品卡片
 *   citation     {refs:[{no, question}]}                                   引用对照
 *   interrupt    {action, payload, resume_token}                           写操作确认卡片
 *   complete     {usage:{input_tokens,output_tokens,total_ms,shortcut_hit}} 收尾
 *   error        {code, message, recoverable}
 */
export const connectV3Chat = ({ q, sessionId, productId, handlers = {} }) => {
  const params = new URLSearchParams()
  params.append('q', q || '')
  if (sessionId) params.append('session_id', sessionId)
  if (productId) params.append('product_id', productId)
  // EventSource 无法携带 header，网关 AuthFilter 兼容从 query 读取 satoken
  const token = localStorage.getItem('token')
  if (token) params.append('satoken', token)

  let closed = false
  let finished = false
  const eventSource = new EventSource(`/api/v1/ai/stream/v3/chat?${params.toString()}`)

  const safeClose = () => {
    if (closed) return
    closed = true
    eventSource.close()
  }

  const parse = (event) => {
    try {
      return JSON.parse(event.data)
    } catch (e) {
      return { raw: event.data }
    }
  }

  const emit = (type, payload) => {
    if (typeof handlers[type] === 'function') handlers[type](payload)
  }

  // 业务收尾（complete/error 帧到达）只通知调用方收尾落盘（幂等），
  // 不主动 close()：此时服务端尚未走完连接收尾，客户端先掐断会被 Chrome
  // 记为 net::ERR_ABORTED。实际关闭交给服务端关连接触发的原生 error 事件。
  const finish = () => {
    if (finished) return
    finished = true
    if (typeof handlers.onclose === 'function') handlers.onclose()
  }

  ;['meta', 'llm_chunk', 'tool', 'product_card', 'citation', 'interrupt'].forEach((type) => {
    eventSource.addEventListener(type, (event) => emit(type, parse(event)))
  })

  eventSource.addEventListener('complete', (event) => {
    emit('complete', parse(event))
    finish()
  })

  // 业务 error 帧与 EventSource 原生连接错误共用 'error' 事件名：
  // 帧携带 data（MessageEvent），原生错误无 data
  eventSource.addEventListener('error', (event) => {
    if (event && typeof event.data === 'string' && event.data) {
      emit('error', parse(event))
      finish()
      return
    }
    // 原生连接层事件：服务端正常收尾关闭，或网络中断。
    // 此刻请求已结束，close() 仅用于阻断自动重连（先于 ~3s retry），不会产生 abort
    safeClose()
    finish()
  })

  return eventSource
}

/**
 * ai-service 会话/确认/反馈接口。
 * 注意：ai-service 响应为 {success,message,data}（无 code 字段），
 * 与共享 request 拦截器的 R 结构不兼容，故使用独立 axios 实例。
 * 网关 AuthFilter 从 header 或 query 读取 satoken，两处都带上。
 */
const aiHttpClient = axios.create({ baseURL: '/api', timeout: 30000 })

export const getConversationHistory = async (userId, sessionId, limit = 20) => {
  const token = localStorage.getItem('token') || ''
  const res = await aiHttpClient.get(
    `/v1/ai/memory/conversation/${userId}`,
    {
      params: { session_id: sessionId, limit, satoken: token },
      headers: { satoken: token }
    }
  )
  return (res.data && res.data.data && res.data.data.history) || []
}

export const clearConversationSession = async (userId, sessionId) => {
  const token = localStorage.getItem('token') || ''
  const res = await aiHttpClient.delete(
    `/v1/ai/memory/session/${userId}/${encodeURIComponent(sessionId)}`,
    {
      params: { satoken: token },
      headers: { satoken: token }
    }
  )
  return res.data
}

/**
 * 售后写操作确认（v3 HITL interrupt 恢复）。
 * Java 网关透传到 ai-service POST /api/v1/ai/v3/resume；
 * 成功返回 {success, data:{approved, message}}，message 为执行结果文本，直接作为助手消息展示；
 * 重复提交返回 HTTP 409，body 为 {detail:{code:'ALREADY_PROCESSED'}}
 * （从 axios 错误对象 e.response.data.detail.code 读取）。
 */
export const confirmAftersale = async ({ sessionId, approved }) => {
  const token = localStorage.getItem('token') || ''
  const res = await aiHttpClient.post(
    '/v1/ai/v3/resume',
    { session_id: sessionId, approved },
    {
      params: { satoken: token },
      headers: { satoken: token }
    }
  )
  return res.data
}

/**
 * 回答反馈（v3 可选项）：rating 1=赞 0=踩，comment 可选。
 */
export const submitFeedback = async ({ requestId, sessionId, rating, comment }) => {
  const token = localStorage.getItem('token') || ''
  const res = await aiHttpClient.post(
    '/v1/ai/v3/feedback',
    { request_id: requestId, session_id: sessionId, rating, comment },
    {
      params: { satoken: token },
      headers: { satoken: token }
    }
  )
  return res.data
}
