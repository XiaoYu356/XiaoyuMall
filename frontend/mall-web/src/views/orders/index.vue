<template>
  <div class="orders-page">
    <div class="container">
      <h2>我的订单</h2>
      
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="待付款" name="0" />
        <el-tab-pane label="待发货" name="1" />
        <el-tab-pane label="待收货" name="2" />
        <el-tab-pane label="已完成" name="3" />
      </el-tabs>
      
      <div class="order-list">
        <div v-for="order in orders" :key="order.id" class="order-item">
          <div class="order-header">
            <span>订单号：{{ order.orderNo }}</span>
            <span>{{ order.createTime }}</span>
            <el-tag :type="getStatusType(order.status)">{{ getStatusText(order.status) }}</el-tag>
          </div>
          
          <div class="order-products">
            <div v-for="item in order.items" :key="item.id" class="product-item">
              <el-image :src="item.productImage" fit="cover" class="product-image" />
              <div class="product-info">
                <h4>{{ item.productName }}</h4>
                <p>¥{{ item.price }} x {{ item.quantity }}</p>
              </div>
            </div>
          </div>
          
          <div class="order-footer">
            <span class="total-amount">实付：¥{{ order.payAmount }}</span>
            <div class="order-actions">
              <el-button v-if="order.status === 0" type="primary" @click="payOrder(order.id)">立即支付</el-button>
              <el-button v-if="order.status === 0" @click="cancelOrder(order.id)">取消订单</el-button>
              <el-button v-if="order.status === 2" type="success" @click="confirmReceive(order.id)">确认收货</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrderList, payOrder as payOrderApi, cancelOrder as cancelOrderApi, confirmReceive as confirmReceiveApi } from '@/api/order'

const activeTab = ref('all')
const orders = ref([])

onMounted(() => {
  fetchOrders()
})

const fetchOrders = async () => {
  try {
    const params = {}
    if (activeTab.value !== 'all') {
      params.status = parseInt(activeTab.value)
    }
    const res = await getOrderList(params)
    orders.value = res.data?.records || []
  } catch (error) {
    console.error('获取订单失败:', error)
  }
}

const handleTabChange = () => {
  fetchOrders()
}

const getStatusText = (status) => {
  const statusMap = { 0: '待付款', 1: '待发货', 2: '待收货', 3: '已完成', 4: '已取消' }
  return statusMap[status] || '未知'
}

const getStatusType = (status) => {
  const typeMap = { 0: 'warning', 1: 'primary', 2: 'info', 3: 'success', 4: 'danger' }
  return typeMap[status] || 'info'
}

const payOrder = async (id) => {
  try {
    await payOrderApi(id)
    ElMessage.success('支付成功')
    fetchOrders()
  } catch (error) {
    console.error('支付失败:', error)
    ElMessage.error('支付失败')
  }
}

const cancelOrder = async (id) => {
  try {
    await ElMessageBox.confirm('确定要取消该订单吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await cancelOrderApi(id)
    ElMessage.success('订单已取消')
    fetchOrders()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消订单失败:', error)
      ElMessage.error('取消订单失败')
    }
  }
}

const confirmReceive = async (id) => {
  try {
    await ElMessageBox.confirm('确认已收到货物吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    
    await confirmReceiveApi(id)
    ElMessage.success('已确认收货')
    fetchOrders()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('确认收货失败:', error)
      ElMessage.error('确认收货失败')
    }
  }
}
</script>

<style scoped>
.orders-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.order-list {
  margin-top: 20px;
}

.order-item {
  background: white;
  border-radius: 8px;
  margin-bottom: 20px;
  overflow: hidden;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f5f5f5;
  border-bottom: 1px solid #eee;
}

.order-products {
  padding: 20px;
}

.product-item {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.product-image {
  width: 80px;
  height: 80px;
  border-radius: 8px;
}

.product-info h4 {
  margin-bottom: 10px;
}

.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-top: 1px solid #eee;
}

.total-amount {
  font-size: 18px;
  color: #F56C6C;
  font-weight: bold;
}

.order-actions {
  display: flex;
  gap: 10px;
}
</style>
