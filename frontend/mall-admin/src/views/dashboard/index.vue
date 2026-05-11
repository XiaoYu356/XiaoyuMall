<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409EFF">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.userCount }}</div>
              <div class="stat-label">用户总数</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-detail">活跃 {{ stats.activeCount }}</span>
            <span class="stat-detail">禁用 {{ stats.disabledCount }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67C23A">
              <el-icon><Goods /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.productCount }}</div>
              <div class="stat-label">商品总数</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-detail">上架 {{ stats.onShelfCount }}</span>
            <span class="stat-detail">分类 {{ stats.categoryCount }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #E6A23C">
              <el-icon><Ticket /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.templateCount }}</div>
              <div class="stat-label">优惠券模板</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-detail">已领取 {{ stats.receivedCount }}</span>
            <span class="stat-detail">已使用 {{ stats.usedCount }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #F56C6C">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.orderCount }}</div>
              <div class="stat-label">订单总数</div>
            </div>
          </div>
          <div class="stat-footer">
            <span class="stat-detail">销售额 ¥{{ stats.totalAmount }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>订单状态分布</span>
          </template>
          <div class="order-status-grid">
            <div class="order-status-item">
              <div class="status-count pending">{{ stats.pendingCount }}</div>
              <div class="status-label">待付款</div>
            </div>
            <div class="order-status-item">
              <div class="status-count paid">{{ stats.paidCount }}</div>
              <div class="status-label">待发货</div>
            </div>
            <div class="order-status-item">
              <div class="status-count shipped">{{ stats.shippedCount }}</div>
              <div class="status-label">待收货</div>
            </div>
            <div class="order-status-item">
              <div class="status-count completed">{{ stats.completedCount }}</div>
              <div class="status-label">已完成</div>
            </div>
            <div class="order-status-item">
              <div class="status-count cancelled">{{ stats.cancelledCount }}</div>
              <div class="status-label">已取消</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/products')" style="width: 100%; margin-bottom: 12px">
              <el-icon><Goods /></el-icon>
              商品管理
            </el-button>
            <el-button type="success" @click="$router.push('/categories')" style="width: 100%; margin-bottom: 12px">
              <el-icon><Menu /></el-icon>
              分类管理
            </el-button>
            <el-button type="warning" @click="$router.push('/orders')" style="width: 100%; margin-bottom: 12px">
              <el-icon><Document /></el-icon>
              订单管理
            </el-button>
            <el-button type="info" @click="$router.push('/coupons')" style="width: 100%; margin-bottom: 12px">
              <el-icon><Ticket /></el-icon>
              优惠券管理
            </el-button>
            <el-button @click="$router.push('/users')" style="width: 100%">
              <el-icon><User /></el-icon>
              用户管理
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>最近订单</span>
      </template>
      <el-table :data="recentOrders" stripe v-loading="orderLoading" size="small">
        <el-table-column prop="orderNo" label="订单号" width="200" />
        <el-table-column prop="totalAmount" label="金额" width="120">
          <template #default="{ row }">
            <span style="color: #F56C6C">¥{{ row.totalAmount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="下单时间" width="180" />
        <el-table-column prop="consignee" label="收货人" width="100" />
        <el-table-column prop="phone" label="手机号" width="130" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { getUserStats } from '@/api/user'
import { getProductStats } from '@/api/product'
import { getCouponStats } from '@/api/coupon'
import { getOrderStats, getOrderList } from '@/api/order'

const stats = reactive({
  userCount: 0,
  activeCount: 0,
  disabledCount: 0,
  productCount: 0,
  onShelfCount: 0,
  categoryCount: 0,
  templateCount: 0,
  receivedCount: 0,
  usedCount: 0,
  orderCount: 0,
  pendingCount: 0,
  paidCount: 0,
  shippedCount: 0,
  completedCount: 0,
  cancelledCount: 0,
  totalAmount: '0.00'
})

const recentOrders = ref([])
const orderLoading = ref(false)

const statusText = (status) => {
  const map = { 0: '待付款', 1: '待发货', 2: '待收货', 3: '已完成', 4: '已取消' }
  return map[status] || '未知'
}

const statusTagType = (status) => {
  const map = { 0: 'warning', 1: 'primary', 2: 'info', 3: 'success', 4: 'danger' }
  return map[status] || 'info'
}

const fetchStats = async () => {
  try {
    const [userRes, productRes, couponRes, orderRes] = await Promise.allSettled([
      getUserStats(),
      getProductStats(),
      getCouponStats(),
      getOrderStats()
    ])

    if (userRes.status === 'fulfilled' && userRes.value.data) {
      const d = userRes.value.data
      stats.userCount = d.userCount || 0
      stats.activeCount = d.activeCount || 0
      stats.disabledCount = d.disabledCount || 0
    }
    if (productRes.status === 'fulfilled' && productRes.value.data) {
      const d = productRes.value.data
      stats.productCount = d.productCount || 0
      stats.onShelfCount = d.onShelfCount || 0
      stats.categoryCount = d.categoryCount || 0
    }
    if (couponRes.status === 'fulfilled' && couponRes.value.data) {
      const d = couponRes.value.data
      stats.templateCount = d.templateCount || 0
      stats.receivedCount = d.receivedCount || 0
      stats.usedCount = d.usedCount || 0
    }
    if (orderRes.status === 'fulfilled' && orderRes.value.data) {
      const d = orderRes.value.data
      stats.orderCount = d.orderCount || 0
      stats.pendingCount = d.pendingCount || 0
      stats.paidCount = d.paidCount || 0
      stats.shippedCount = d.shippedCount || 0
      stats.completedCount = d.completedCount || 0
      stats.cancelledCount = d.cancelledCount || 0
      stats.totalAmount = d.totalAmount || '0.00'
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const fetchRecentOrders = async () => {
  orderLoading.value = true
  try {
    const res = await getOrderList({ pageNum: 1, pageSize: 5 })
    recentOrders.value = res.data?.records || []
  } catch (error) {
    console.error('获取最近订单失败:', error)
  } finally {
    orderLoading.value = false
  }
}

onMounted(() => {
  fetchStats()
  fetchRecentOrders()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-content {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 30px;
  flex-shrink: 0;
}

.stat-info {
  margin-left: 20px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.stat-footer {
  display: flex;
  gap: 16px;
  padding: 8px 10px 4px;
  border-top: 1px solid #f0f0f0;
  margin-top: 8px;
}

.stat-detail {
  font-size: 12px;
  color: #909399;
}

.order-status-grid {
  display: flex;
  justify-content: space-around;
  padding: 20px 0;
}

.order-status-item {
  text-align: center;
}

.status-count {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.status-count.pending { color: #E6A23C; }
.status-count.paid { color: #409EFF; }
.status-count.shipped { color: #909399; }
.status-count.completed { color: #67C23A; }
.status-count.cancelled { color: #F56C6C; }

.status-label {
  font-size: 14px;
  color: #606266;
}

.quick-actions {
  padding: 4px 0;
}
</style>
