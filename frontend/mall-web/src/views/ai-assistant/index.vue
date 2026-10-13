<template>
  <div class="ai-page">
    <div class="container">
      <div class="chat-container">
        <div class="chat-header">
          <div class="header-left">
            <span class="robot-icon">🤖</span>
            <div>
              <h2>AI 智能购物助手</h2>
              <p>找商品 · 查优惠 · 查订单 · 办售后，一句话搞定</p>
            </div>
          </div>
          <el-button text @click="clearChat">清空对话</el-button>
        </div>

        <div class="chat-messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="welcome-section">
            <div class="welcome-icon">🛒</div>
            <h3>你好！我是你的智能购物助手</h3>
            <p>可以帮你找商品、查优惠券、查订单、办售后，也能解答购物常见问题</p>
            <div class="quick-actions">
              <div class="quick-card" @click="quickAsk('帮我推荐一款性价比高的手机')">
                <span class="quick-icon">📱</span>
                <span>推荐手机</span>
              </div>
              <div class="quick-card" @click="quickAsk('有什么优惠券可以领？')">
                <span class="quick-icon">🎟️</span>
                <span>优惠券推荐</span>
              </div>
              <div class="quick-card" @click="quickAsk('帮我查一下最近的订单')">
                <span class="quick-icon">📦</span>
                <span>查我的订单</span>
              </div>
              <div class="quick-card" @click="quickAsk('你们的退货政策是什么？')">
                <span class="quick-icon">📋</span>
                <span>退货政策</span>
              </div>
            </div>
          </div>

          <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
            <div class="message-avatar">
              <span v-if="msg.role === 'user'">👤</span>
              <span v-else>🤖</span>
            </div>
            <div class="message-content">
              <div class="message-bubble" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.cards && msg.cards.length" class="product-cards">
                <div
                  v-for="card in msg.cards"
                  :key="card.id"
                  class="product-card"
                  @click="goProduct(card.id)"
                >
                  <img class="product-image" :src="card.image" :alt="card.name" />
                  <div class="product-meta">
                    <div class="product-name">{{ card.name }}</div>
                    <div class="product-price">¥{{ formatPrice(card.price) }}</div>
                    <div class="product-sales">已售 {{ card.sales }}</div>
                  </div>
                </div>
              </div>
              <div v-if="msg.citations && msg.citations.length" class="citation-list">
                <div v-for="cite in msg.citations" :key="cite.no" class="citation-item">
                  [{{ cite.no }}] {{ cite.question }}
                </div>
              </div>
              <div v-if="msg.traceUrl || msg.elapsedMs" class="message-footer">
                <a v-if="msg.traceUrl" class="trace-link" :href="msg.traceUrl" target="_blank" rel="noopener">查看链路</a>
                <span v-if="msg.elapsedMs" class="elapsed-text">耗时 {{ (msg.elapsedMs / 1000).toFixed(1) }}s</span>
              </div>
              <div v-if="msg.draft" class="aftersale-card">
                <div class="draft-title">📋 售后申请确认</div>
                <div v-if="msg.draft.order_no" class="draft-row"><span>订单号</span>{{ msg.draft.order_no }}</div>
                <div v-if="msg.draft.items" class="draft-row"><span>商品</span>{{ msg.draft.items }}</div>
                <div v-if="msg.draft.type_text" class="draft-row"><span>类型</span>{{ msg.draft.type_text }}</div>
                <div v-if="msg.draft.refund_amount !== undefined" class="draft-row"><span>退款金额</span>¥{{ msg.draft.refund_amount }}</div>
                <div v-if="msg.draft.reason" class="draft-row"><span>原因</span>{{ msg.draft.reason }}</div>
                <div class="draft-actions">
                  <el-button type="primary" size="small" :disabled="resolvingDraft" @click="confirmDraft">确认提交</el-button>
                  <el-button size="small" :disabled="resolvingDraft" @click="cancelDraft">取消申请</el-button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="loading" class="message assistant">
            <div class="message-avatar"><span>🤖</span></div>
            <div class="message-content">
              <div class="message-bubble streaming">
                <div v-if="streamingText" v-html="formatMessage(streamingText)"></div>
                <div v-else-if="statusHint" class="status-hint">{{ statusHint }}</div>
                <div v-else class="typing">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
                <!-- 商品卡片不在流式阶段展示：product_card 事件先于文字到达（工具返回即发），
                     缓冲到 complete 时随最终消息一起渲染，避免「卡片先出、文字后到」的割裂感 -->
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="inputText"
            placeholder="输入你的购物需求，如：推荐一款2000元以内的手机..."
            @keyup.enter="sendMessage"
            :disabled="loading"
            size="large"
          >
            <template #append>
              <el-button type="primary" @click="sendMessage" :loading="loading" :disabled="!inputText.trim()">
                发送
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  connectV3Chat,
  confirmAftersale,
  getConversationHistory,
  clearConversationSession
} from '@/api/ai'
import { useUserStore } from '@/stores/user'
import { marked } from 'marked'

// 组件名供 Layout keep-alive include 匹配：跳商品详情再返回时保留
// 商品卡片/引用/interrupt 卡片等仅存在于前端内存的会话状态
defineOptions({ name: 'AIAssistant' })

marked.setOptions({
  breaks: true,
  gfm: true
})

const router = useRouter()
const userStore = useUserStore()
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)
const streamingText = ref('')
const statusHint = ref('')
const streamingCards = ref([])
const streamingCitations = ref([])
// meta 事件记录：request_id 用于反馈关联，trace_url 非空时展示「查看链路」小链接
const currentRequestId = ref('')
const currentTraceUrl = ref('')
// 本轮写操作确认卡片（interrupt 事件 payload，complete 时挂到助手消息上）
const pendingDraft = ref(null)

const generateSessionId = () => {
  return (window.crypto && crypto.randomUUID)
    ? crypto.randomUUID()
    : `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

// 会话ID按用户持久化到 localStorage：重开/刷新页面后沿用同一会话，
// 配合后端 Redis 历史记录实现对话恢复；未登录时仅使用临时会话
const SESSION_STORAGE_PREFIX = 'ai_session_id_'

const resolveStoredSessionId = (userId) => {
  const storageKey = SESSION_STORAGE_PREFIX + userId
  let sid = localStorage.getItem(storageKey)
  if (!sid) {
    sid = generateSessionId()
    localStorage.setItem(storageKey, sid)
  }
  return sid
}

// 初始为临时值，onMounted 解析登录态后替换为持久化会话
const sessionId = ref(generateSessionId())

// 已恢复会话归属的用户ID：undefined=尚未恢复过，null=游客。
// keep-alive 重入时用于判断身份是否变化，同一用户直接复用内存状态
let restoredUserId = undefined

const restoreConversation = async () => {
  let userId = userStore.userInfo?.id
  // localStorage 只持久化 token，userInfo 需异步拉取
  if (!userId && userStore.token) {
    try {
      await userStore.fetchUserInfo()
      userId = userStore.userInfo?.id
    } catch (e) {
      userId = null
    }
  }
  const currentUserId = userId ?? null
  if (currentUserId === restoredUserId) return // 同一身份：保留内存对话（含卡片/引用），不重拉
  restoredUserId = currentUserId
  messages.value = [] // 身份变化（登出/切换账号）时清空旧对话
  if (!currentUserId) return // 未登录：不持久化、不回显

  sessionId.value = resolveStoredSessionId(userId)
  try {
    const history = await getConversationHistory(userId, sessionId.value)
    if (history.length) {
      // 服务端历史已随助手消息持久化结构化附件（cards/citations/draft），
      // 刷新后可直接恢复商品卡片/引用/确认卡片，不再只剩纯文本
      messages.value = history
        .filter(m => m.role === 'user' || (m.role === 'assistant' && (m.content || m.cards?.length || m.draft)))
        .map(m => ({
          role: m.role,
          content: m.content,
          cards: m.cards || [],
          citations: m.citations || [],
          draft: m.draft || null
        }))
      scrollToBottom()
      // 刷新恢复历史时内容较多，首帧渲染与实际布局可能有时间差，
      // 延迟再补滚一次确保打开页面直接停在最底部（最新消息）
      setTimeout(scrollMessagesToBottom, 500)
    }
  } catch (e) {
    // 历史回显失败不阻塞新会话（如网络问题、token 过期）
    console.warn('历史对话恢复失败:', e)
  }
}

onMounted(restoreConversation)

// keep-alive 重入（如从商品详情返回）：仅当登录身份与上次恢复时不一致才重建，
// 同一用户直接复用内存状态，避免覆盖商品卡片等仅前端可见的数据。
// 但重挂 DOM 后浏览器会丢失容器滚动位置，同身份也要补滚到底部
onActivated(() => {
  if (restoredUserId === undefined) return // 首次挂载由 onMounted 处理
  const currentUserId = userStore.userInfo?.id ?? null
  if (currentUserId !== restoredUserId) {
    restoreConversation()
  } else {
    scrollToBottom()
  }
})

const scrollMessagesToBottom = () => {
  const el = messagesRef.value || document.querySelector('.chat-messages')
  if (el) el.scrollTop = el.scrollHeight
}

const scrollToBottom = async () => {
  await nextTick()
  scrollMessagesToBottom()
  // 首帧后浏览器可能因字体/图片回填再次布局，下一帧补滚一次
  requestAnimationFrame(scrollMessagesToBottom)
}

const quickAsk = (text) => {
  inputText.value = text
  sendMessage()
}

// 售后确认卡片按钮：调 /resume 恢复挂起的写工具（LangGraph interrupt 硬中断），
// 不再以固定句式触发模型确认分支，确认动作由系统强制执行
const resolvingDraft = ref(false)
const confirmDraft = () => resolveDraft(true)
const cancelDraft = () => resolveDraft(false)
const resolveDraft = async (approved) => {
  if (resolvingDraft.value) return
  resolvingDraft.value = true
  // 用户决策落为一条消息（与会话历史保持一致），并清除卡片防重复点击
  messages.value.push({ role: 'user', content: approved ? '确认了售后申请' : '取消了售后申请' })
  messages.value.forEach(m => { if (m.draft) m.draft = null })
  scrollToBottom()
  try {
    const res = await confirmAftersale({ sessionId: sessionId.value, approved })
    // data.message 为执行结果文本，直接作为新的助手消息展示
    const text = (res && res.data && res.data.message) || (approved ? '操作已完成。' : '已取消。')
    messages.value.push({ role: 'assistant', content: text })
  } catch (e) {
    const code = e && e.response && e.response.data && e.response.data.detail && e.response.data.detail.code
    if (code === 'ALREADY_PROCESSED') {
      ElMessage.warning('该确认已处理过')
    } else {
      console.warn('售后确认失败:', e)
      messages.value.push({ role: 'assistant', content: '确认操作失败，请稍后重试或联系人工客服。' })
    }
  } finally {
    resolvingDraft.value = false
    scrollToBottom()
  }
}

// v3 工具调用轻提示（tool 事件 phase=start 展示，end 清除，复用 statusHint）
const TOOL_LABEL = {
  search_faq: '正在查询知识库',
  search_products: '正在查询商品',
  get_product_detail: '正在查询商品详情',
  get_product_categories: '正在查询商品分类',
  get_product_skus: '正在查询商品规格',
  get_user_coupons: '正在查询我的优惠券',
  get_available_coupons: '正在查询可领优惠券',
  calculate_coupon_discount: '正在计算优惠',
  get_my_orders: '正在查询我的订单',
  get_order_detail: '正在查询订单详情',
  get_my_coupons: '正在查询我的优惠券',
}

// 流结束（complete/error/断连）统一落盘当前助手消息并复位状态
const resetStreamState = () => {
  streamingText.value = ''
  statusHint.value = ''
  streamingCards.value = []
  streamingCitations.value = []
  pendingDraft.value = null
  currentRequestId.value = ''
  currentTraceUrl.value = ''
  loading.value = false
  scrollToBottom()
}

const commitStreamMessage = (usage) => {
  if (
    streamingText.value ||
    streamingCards.value.length ||
    pendingDraft.value ||
    streamingCitations.value.length
  ) {
    messages.value.push({
      role: 'assistant',
      content: streamingText.value,
      cards: streamingCards.value.slice(),
      draft: pendingDraft.value,
      citations: streamingCitations.value.slice(),
      traceUrl: currentTraceUrl.value || null,
      elapsedMs: usage && usage.total_ms ? usage.total_ms : null
    })
  }
  resetStreamState()
}

// 是否收到过 meta 首事件：用于区分「连接失败」与「中途断开」
let receivedMeta = false

const sendMessage = () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  streamingText.value = ''
  statusHint.value = ''
  streamingCards.value = []
  streamingCitations.value = []
  pendingDraft.value = null
  currentRequestId.value = ''
  currentTraceUrl.value = ''
  receivedMeta = false
  scrollToBottom()

  connectV3Chat({
    q: text,
    sessionId: sessionId.value,
    productId: extractProductId(text) || undefined,
    handlers: {
      meta: (data) => {
        receivedMeta = true
        currentRequestId.value = data.request_id || ''
        currentTraceUrl.value = data.trace_url || ''
      },
      llm_chunk: (data) => {
        streamingText.value += data.text || ''
        scrollToBottom()
      },
      tool: (data) => {
        statusHint.value = data.phase === 'start'
          ? `${TOOL_LABEL[data.name] || data.name}...`
          : ''
        scrollToBottom()
      },
      product_card: (data) => {
        streamingCards.value = data.items || []
        scrollToBottom()
      },
      citation: (data) => {
        streamingCitations.value = data.refs || []
      },
      interrupt: (data) => {
        // 写操作确认卡片（HITL 硬中断），complete 时随消息落盘
        pendingDraft.value = data.payload || {}
        scrollToBottom()
      },
      error: (data) => {
        let msg = `❌ ${data.message || '服务出错，请稍后重试'}`
        if (data.recoverable) msg += '\n\n💡 您可以重新发送消息重试。'
        streamingText.value += (streamingText.value ? '\n\n' : '') + msg
        scrollToBottom()
      },
      complete: (data) => {
        commitStreamMessage(data && data.usage)
      },
      // complete/error 帧之外的结束（网络中断、连接失败等）：兜底落盘
      onclose: () => {
        if (!receivedMeta && !streamingText.value) {
          messages.value.push({ role: 'assistant', content: '抱歉，AI 服务连接失败，请稍后再试。' })
          resetStreamState()
          return
        }
        commitStreamMessage(null)
      }
    }
  })
}

const extractProductId = (text) => {
  const match = text.match(/商品[编号ID]*[：:]?\s*(\d+)/i)
  return match ? match[1] : null
}

const formatMessage = (content) => {
  if (!content) return ''
  return marked.parse(content)
}

const formatPrice = (price) => {
  if (price === null || price === undefined) return '-'
  return Number(price).toFixed(2)
}

const goProduct = (id) => {
  if (!id) return
  router.push(`/product/${id}`)
}

const clearChat = async () => {
  const userId = userStore.userInfo?.id
  const oldSessionId = sessionId.value

  messages.value = []
  streamingCards.value = []
  // 清空对话即开启新会话，避免上一轮上下文残留
  const newSessionId = generateSessionId()
  sessionId.value = newSessionId

  if (userId) {
    localStorage.setItem(SESSION_STORAGE_PREFIX + userId, newSessionId)
    // 最佳努力清除服务端旧会话展示历史（checkpoint 线程因 thread_id 变更自然不再使用）
    try {
      await clearConversationSession(userId, oldSessionId)
    } catch (e) {
      console.warn('清除服务端会话失败(忽略):', e)
    }
  }
}
</script>

<style scoped>
.ai-page {
  padding: 20px 0;
  min-height: calc(100vh - 80px);
}

.container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

.chat-container {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.robot-icon {
  font-size: 36px;
}

.chat-header h2 {
  font-size: 18px;
  margin-bottom: 2px;
}

.chat-header p {
  font-size: 13px;
  opacity: 0.85;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.welcome-section {
  text-align: center;
  padding: 40px 20px;
}

.welcome-icon {
  font-size: 60px;
  margin-bottom: 16px;
}

.welcome-section h3 {
  font-size: 20px;
  color: #333;
  margin-bottom: 8px;
}

.welcome-section > p {
  color: #999;
  margin-bottom: 30px;
}

.quick-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #f5f7fa;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
  color: #606266;
}

.quick-card:hover {
  background: #ecf5ff;
  color: #409EFF;
  transform: translateY(-2px);
}

.quick-icon {
  font-size: 20px;
}

.message {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  background: #f0f0f0;
}

.message.user .message-avatar {
  background: #ecf5ff;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
}

.message.user .message-bubble {
  background: #409EFF;
  color: white;
  border-top-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: #f5f7fa;
  color: #333;
  border-top-left-radius: 4px;
}

.message-bubble :deep(h4) {
  margin: 12px 0 6px;
  font-size: 15px;
}

.message-bubble :deep(h4:first-child) {
  margin-top: 0;
}

.message-bubble :deep(p) {
  margin: 4px 0;
}

.message-bubble :deep(h1), .message-bubble :deep(h2), .message-bubble :deep(h3) {
  margin: 12px 0 6px;
  font-weight: 600;
}

.message-bubble :deep(h3) {
  font-size: 15px;
}

.message-bubble :deep(ul), .message-bubble :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.message-bubble :deep(li) {
  margin: 2px 0;
}

.message-bubble :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}

.message-bubble :deep(th), .message-bubble :deep(td) {
  border: 1px solid #e0e0e0;
  padding: 6px 10px;
  text-align: left;
}

.message-bubble :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}

.message-bubble :deep(blockquote) {
  border-left: 3px solid #409EFF;
  padding: 4px 12px;
  margin: 8px 0;
  background: #f5f7fa;
  border-radius: 0 4px 4px 0;
}

.message-bubble :deep(strong) {
  color: #303133;
}

.message-bubble :deep(hr) {
  border: none;
  border-top: 1px solid #e8e8e8;
  margin: 12px 0;
}

.message-bubble :deep(code) {
  background: #f0f0f0;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 13px;
}

.streaming {
  min-height: 40px;
}

.status-hint {
  color: #909399;
  font-size: 13px;
  padding: 4px 0;
}

.typing {
  display: flex;
  gap: 4px;
  padding: 16px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: typing 1.4s infinite;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

.citation-list {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e8e8e8;
}

.citation-item {
  font-size: 12px;
  color: #909399;
  line-height: 1.8;
}

.message-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 12px;
}

.trace-link {
  color: #409EFF;
  text-decoration: none;
}

.trace-link:hover {
  text-decoration: underline;
}

.elapsed-text {
  color: #c0c4cc;
}

.product-cards {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  margin-top: 10px;
  padding-bottom: 4px;
}
.aftersale-card {
  margin-top: 10px;
  padding: 12px 14px;
  background: #fffdf5;
  border: 1px solid #f0d99a;
  border-radius: 10px;
  font-size: 13px;
}

.aftersale-card .draft-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #8a5a00;
}

.aftersale-card .draft-row {
  display: flex;
  gap: 8px;
  line-height: 1.9;
  color: #333;
}

.aftersale-card .draft-row span {
  flex: 0 0 56px;
  color: #909399;
}

.aftersale-card .draft-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.product-card {
  flex: 0 0 auto;
  width: 132px;
  background: white;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.product-card:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.18);
  transform: translateY(-2px);
}

.product-image {
  width: 100%;
  height: 100px;
  object-fit: cover;
  display: block;
  background: #f5f7fa;
}

.product-meta {
  padding: 8px 10px;
}

.product-name {
  font-size: 13px;
  color: #303133;
  line-height: 1.35;
  height: 36px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.product-price {
  font-size: 14px;
  font-weight: 600;
  color: #f56c6c;
  margin-top: 4px;
}

.product-sales {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.chat-input {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}
</style>
