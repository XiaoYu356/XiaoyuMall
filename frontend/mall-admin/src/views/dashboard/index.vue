<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409EFF">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.userCount }}</div>
              <div class="stat-label">用户总数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67C23A">
              <el-icon><Goods /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.productCount }}</div>
              <div class="stat-label">商品总数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #E6A23C">
              <el-icon><Ticket /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.couponCount }}</div>
              <div class="stat-label">优惠券总数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #F56C6C">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.orderCount }}</div>
              <div class="stat-label">订单总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>欢迎使用智能百货平台管理后台</span>
      </template>
      <div class="welcome-content">
        <p>这是一个基于 Spring Cloud Alibaba 微服务架构的智能百货平台</p>
        <p>技术栈: Spring Boot 3.2 + Vue 3 + Element Plus + Sa-Token</p>
        <p>功能模块: 用户管理、商品管理、优惠券管理、订单管理、AI智能助手</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { getUserList } from '@/api/user'
import { getProductList } from '@/api/product'
import { getCouponList } from '@/api/coupon'
import { getOrderList } from '@/api/order'

const stats = reactive({
  userCount: 0,
  productCount: 0,
  couponCount: 0,
  orderCount: 0
})

const fetchStats = async () => {
  try {
    const [userRes, productRes, couponRes, orderRes] = await Promise.allSettled([
      getUserList({ pageNum: 1, pageSize: 1 }),
      getProductList({ pageNum: 1, pageSize: 1 }),
      getCouponList({ pageNum: 1, pageSize: 1 }),
      getOrderList({ pageNum: 1, pageSize: 1 })
    ])

    if (userRes.status === 'fulfilled') stats.userCount = userRes.value.data?.total || 0
    if (productRes.status === 'fulfilled') stats.productCount = productRes.value.data?.total || 0
    if (couponRes.status === 'fulfilled') stats.couponCount = couponRes.value.data?.total || 0
    if (orderRes.status === 'fulfilled') stats.orderCount = orderRes.value.data?.total || 0
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

onMounted(() => {
  fetchStats()
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

.welcome-content {
  line-height: 2;
  color: #606266;
}
</style>
