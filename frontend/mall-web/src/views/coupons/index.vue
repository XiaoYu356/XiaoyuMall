<template>
  <div class="coupon-page">
    <div class="container">
      <div class="page-header">
        <h2>🎟️ 优惠券秒杀</h2>
        <p>限时抢购，先到先得</p>
      </div>

      <div class="countdown-bar" v-if="nextStartTime">
        <span>距离 <b>{{ nextCouponName }}</b> 开抢：</span>
        <span class="countdown">{{ countdownText }}</span>
      </div>

      <div v-loading="loading" class="coupon-grid">
        <div v-for="coupon in couponList" :key="coupon.id" class="coupon-card">
          <div class="coupon-left" :class="getCouponColor(coupon.couponType)">
            <div class="coupon-value">
              <template v-if="coupon.couponType === 2">
                <span class="number">{{ coupon.couponValue }}</span>
                <span class="unit">折</span>
              </template>
              <template v-else>
                <span class="symbol">¥</span>
                <span class="number">{{ coupon.couponValue }}</span>
              </template>
            </div>
            <div class="coupon-condition">满{{ coupon.minAmount }}可用</div>
          </div>
          <div class="coupon-right">
            <div class="coupon-info">
              <h3>{{ coupon.templateName }}</h3>
              <div class="coupon-type">
                <el-tag :type="getTypeTagColor(coupon.couponType)" size="small">
                  {{ getTypeName(coupon.couponType) }}
                </el-tag>
              </div>
              <div class="coupon-time">
                {{ formatTime(coupon.startTime) }} - {{ formatTime(coupon.endTime) }}
              </div>
              <div class="coupon-stock">
                <el-progress
                  :percentage="getStockPercentage(coupon)"
                  :stroke-width="8"
                  :color="getStockPercentage(coupon) < 20 ? '#F56C6C' : '#409EFF'"
                />
                <span class="stock-text">剩余 {{ coupon.totalCount - coupon.usedCount }} / {{ coupon.totalCount }}</span>
              </div>
            </div>
            <el-button
              :type="canReceive(coupon) ? 'danger' : 'info'"
              :disabled="!canReceive(coupon)"
              :loading="receivingIds.has(coupon.id)"
              @click="handleReceive(coupon)"
              class="receive-btn"
            >
              {{ getReceiveBtnText(coupon) }}
            </el-button>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && couponList.length === 0" description="暂无可领取的优惠券" />

      <div class="pagination-wrap" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="pageNum"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchCoupons"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAvailableCoupons, receiveCoupon } from '@/api/coupon'

const loading = ref(false)
const couponList = ref([])
const pageNum = ref(1)
const pageSize = ref(20)
const total = ref(0)
const receivingIds = ref(new Set())

const nextStartTime = ref(null)
const nextCouponName = ref('')
const countdownText = ref('')
let timer = null

const TYPE_NAME_MAP = { 1: '满减券', 2: '折扣券', 3: '现金券' }
const TYPE_COLOR_MAP = { 1: 'success', 2: 'warning', 3: 'danger' }

const getTypeName = (type) => TYPE_NAME_MAP[type] || '优惠券'
const getTypeTagColor = (type) => TYPE_COLOR_MAP[type] || 'info'

const getCouponColor = (type) => {
  const map = { 1: 'blue', 2: 'orange', 3: 'red' }
  return map[type] || 'blue'
}

const getStockPercentage = (coupon) => {
  if (!coupon.totalCount) return 0
  return Math.round(((coupon.totalCount - coupon.usedCount) / coupon.totalCount) * 100)
}

const canReceive = (coupon) => {
  if (coupon.status !== 1) return false
  if (coupon.usedCount >= coupon.totalCount) return false
  if (coupon.userReceivedCount >= (coupon.perLimit || 1)) return false
  const now = new Date()
  const start = new Date(coupon.startTime)
  const end = new Date(coupon.endTime)
  if (now < start || now > end) return false
  return true
}

const getReceiveBtnText = (coupon) => {
  if (coupon.usedCount >= coupon.totalCount) return '已抢光'
  if (coupon.status !== 1) return '已结束'
  const now = new Date()
  const start = new Date(coupon.startTime)
  const end = new Date(coupon.endTime)
  if (now < start) return '未开始'
  if (now > end) return '已过期'
  if (coupon.userReceivedCount >= (coupon.perLimit || 1)) return '已领取'
  return '立即领取'
}

const formatTime = (time) => {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const fetchCoupons = async () => {
  loading.value = true
  try {
    const res = await getAvailableCoupons({ pageNum: pageNum.value, pageSize: pageSize.value })
    couponList.value = res.data?.records || []
    total.value = res.data?.total || 0
    updateNextStart()
  } catch (error) {
    console.error('获取优惠券列表失败:', error)
  } finally {
    loading.value = false
  }
}

const updateNextStart = () => {
  const now = new Date()
  let nearest = null
  for (const coupon of couponList.value) {
    const start = new Date(coupon.startTime)
    if (start > now && coupon.usedCount < coupon.totalCount) {
      if (!nearest || start < new Date(nearest.startTime)) {
        nearest = coupon
      }
    }
  }
  if (nearest) {
    nextStartTime.value = nearest.startTime
    nextCouponName.value = nearest.templateName
  } else {
    nextStartTime.value = null
    nextCouponName.value = ''
  }
}

const handleReceive = async (coupon) => {
  if (receivingIds.value.has(coupon.id)) return
  receivingIds.value.add(coupon.id)
  try {
    await receiveCoupon(coupon.id)
    ElMessage.success('领取成功！')
    coupon.usedCount += 1
    coupon.userReceivedCount = (coupon.userReceivedCount || 0) + 1
  } catch (error) {
    console.error('领取失败:', error)
  } finally {
    receivingIds.value.delete(coupon.id)
  }
}

const updateCountdown = () => {
  if (!nextStartTime.value) return
  const diff = new Date(nextStartTime.value) - new Date()
  if (diff <= 0) {
    countdownText.value = '开抢中！'
    nextStartTime.value = null
    return
  }
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  const s = Math.floor((diff % 60000) / 1000)
  countdownText.value = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

onMounted(() => {
  fetchCoupons()
  updateCountdown()
  timer = setInterval(updateCountdown, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.coupon-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h2 {
  font-size: 28px;
  color: #F56C6C;
  margin-bottom: 8px;
}

.page-header p {
  color: #999;
  font-size: 16px;
}

.countdown-bar {
  text-align: center;
  padding: 12px;
  background: linear-gradient(135deg, #ff6b6b, #ee5a24);
  color: white;
  border-radius: 8px;
  margin-bottom: 30px;
  font-size: 16px;
}

.countdown {
  font-size: 24px;
  font-weight: bold;
  font-family: monospace;
  margin-left: 10px;
}

.coupon-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.coupon-card {
  display: flex;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
}

.coupon-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.coupon-left {
  width: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  padding: 20px;
  position: relative;
}

.coupon-left::after {
  content: '';
  position: absolute;
  right: -6px;
  top: 0;
  bottom: 0;
  width: 12px;
  background: white;
  border-radius: 6px;
}

.coupon-left.blue {
  background: linear-gradient(135deg, #409EFF, #337ecc);
}

.coupon-left.orange {
  background: linear-gradient(135deg, #E6A23C, #cf8e24);
}

.coupon-left.red {
  background: linear-gradient(135deg, #F56C6C, #dd4a4a);
}

.coupon-value {
  display: flex;
  align-items: baseline;
  margin-bottom: 8px;
}

.coupon-value .symbol {
  font-size: 18px;
  margin-right: 2px;
}

.coupon-value .number {
  font-size: 40px;
  font-weight: bold;
  line-height: 1;
}

.coupon-value .unit {
  font-size: 18px;
  margin-left: 2px;
}

.coupon-condition {
  font-size: 13px;
  opacity: 0.9;
}

.coupon-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px 20px;
}

.coupon-info h3 {
  font-size: 16px;
  color: #333;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.coupon-type {
  margin-bottom: 6px;
}

.coupon-time {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.coupon-stock {
  display: flex;
  align-items: center;
  gap: 10px;
}

.coupon-stock .el-progress {
  flex: 1;
}

.stock-text {
  font-size: 12px;
  color: #999;
  white-space: nowrap;
}

.receive-btn {
  align-self: flex-end;
  min-width: 90px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}

@media (max-width: 768px) {
  .coupon-grid {
    grid-template-columns: 1fr;
  }

  .coupon-left {
    width: 120px;
  }

  .coupon-value .number {
    font-size: 30px;
  }
}
</style>
