<template>
  <div class="ai-page">
    <div class="container">
      <div class="chat-container">
        <div class="chat-header">
          <div class="header-left">
            <span class="robot-icon">🤖</span>
            <div>
              <h2>AI 智能购物助手</h2>
              <p>为您推荐最优惠的购物方案</p>
            </div>
          </div>
          <el-button text @click="clearChat">清空对话</el-button>
        </div>

        <div class="chat-messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="welcome-section">
            <div class="welcome-icon">🛒</div>
            <h3>你好！我是你的智能购物助手</h3>
            <p>我可以帮你分析商品性价比、推荐最优优惠券、给出购买建议</p>
            <div class="quick-actions">
              <div class="quick-card" @click="quickAsk('帮我推荐一款性价比高的手机')">
                <span class="quick-icon">📱</span>
                <span>推荐手机</span>
              </div>
              <div class="quick-card" @click="quickAsk('有什么优惠券可以领？')">
                <span class="quick-icon">🎟️</span>
                <span>优惠券推荐</span>
              </div>
              <div class="quick-card" @click="quickAsk('帮我分析一下这个商品值得买吗？')">
                <span class="quick-icon">🔍</span>
                <span>商品分析</span>
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
            </div>
          </div>

          <div v-if="loading" class="message assistant">
            <div class="message-avatar"><span>🤖</span></div>
            <div class="message-content">
              <div class="message-bubble typing">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
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
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { analyzeProduct } from '@/api/ai'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

const quickAsk = (text) => {
  inputText.value = text
  sendMessage()
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const productId = extractProductId(text)
    const res = await analyzeProduct({
      productId: productId || undefined,
      userId: userStore.userInfo?.id,
      userQuery: text
    })

    const data = res.data || res
    let reply = ''

    if (data.recommendation) {
      const r = data.recommendation
      reply = `<h4>💡 购买建议</h4>`
      if (r.productName) reply += `<p><b>商品：</b>${r.productName}</p>`
      if (r.currentPrice) reply += `<p><b>当前价格：</b><span style="color:#F56C6C">¥${r.currentPrice}</span></p>`
      if (r.finalPrice) reply += `<p><b>优惠后价格：</b><span style="color:#67C23A">¥${r.finalPrice}</span></p>`
      if (r.totalSavings) reply += `<p><b>可节省：</b><span style="color:#E6A23C">¥${r.totalSavings}</span></p>`
      if (r.buyRecommendation) reply += `<p>${r.buyRecommendation}</p>`
    }

    if (data.productAnalysis?.analysis) {
      const a = data.productAnalysis.analysis
      reply += `<h4>📦 商品分析</h4>`
      if (a.features) reply += `<p><b>特点：</b>${a.features}</p>`
      if (a.quality) reply += `<p><b>品质：</b>${a.quality}</p>`
      if (a.targetAudience) reply += `<p><b>适用人群：</b>${a.targetAudience}</p>`
    }

    if (data.priceAnalysis?.priceAnalysis) {
      const p = data.priceAnalysis.priceAnalysis
      reply += `<h4>💰 价格分析</h4>`
      if (p.discountRate) reply += `<p><b>折扣率：</b>${p.discountRate}%</p>`
      if (p.priceTrend) reply += `<p><b>价格趋势：</b>${p.priceTrend}</p>`
      if (p.buyRecommendation) reply += `<p>${p.buyRecommendation}</p>`
    }

    if (data.couponStrategy?.bestCoupon) {
      const c = data.couponStrategy
      reply += `<h4>🎟️ 最优优惠券</h4>`
      if (c.bestCoupon?.templateName) reply += `<p><b>优惠券：</b>${c.bestCoupon.templateName}</p>`
      if (c.maxDiscount) reply += `<p><b>优惠金额：</b>¥${c.maxDiscount}</p>`
    }

    if (!reply) {
      reply = '抱歉，我暂时无法分析这个需求，请换个方式描述或提供具体的商品信息。'
    }

    if (data.executionTime) {
      reply += `<p style="color:#999;font-size:12px;margin-top:8px">⏱ 分析耗时 ${data.executionTime}s</p>`
    }

    messages.value.push({ role: 'assistant', content: reply })
  } catch (error) {
    console.error('AI分析失败:', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，分析服务暂时不可用，请稍后再试。'
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const extractProductId = (text) => {
  const match = text.match(/商品[编号ID]*[：:]?\s*(\d+)/i)
  return match ? match[1] : null
}

const formatMessage = (content) => {
  return content
}

const clearChat = () => {
  messages.value = []
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

.chat-input {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}
</style>
