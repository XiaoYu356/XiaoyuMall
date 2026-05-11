<template>
  <div class="orders-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>订单管理</span>
        </div>
      </template>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="订单号">
          <el-input v-model="searchForm.orderNo" placeholder="请输入订单号" clearable />
        </el-form-item>
        <el-form-item label="订单状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="待支付" :value="0" />
            <el-option label="已支付" :value="1" />
            <el-option label="已发货" :value="2" />
            <el-option label="已完成" :value="3" />
            <el-option label="已取消" :value="4" />
            <el-option label="已退款" :value="5" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="orderList" border stripe v-loading="loading">
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="orderNo" label="订单号" width="200" />
        <el-table-column prop="receiverName" label="收货人" width="120" />
        <el-table-column prop="receiverPhone" label="联系电话" width="150" />
        <el-table-column prop="totalAmount" label="订单金额" width="120">
          <template #default="{ row }">
            <span style="color: #F56C6C">¥{{ row.totalAmount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payAmount" label="实付金额" width="120">
          <template #default="{ row }">
            <span style="color: #F56C6C; font-weight: bold">¥{{ row.payAmount }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusColor(row.status)">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" fixed="right" width="250">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="handleDetail(row)">详情</el-button>
            <el-button
              v-if="row.status === 1"
              v-permission="'order:ship'"
              type="success"
              size="small"
              @click="handleShip(row)"
            >
              发货
            </el-button>
            <el-button
              v-if="row.status === 0"
              v-permission="'order:cancel'"
              type="danger"
              size="small"
              @click="handleCancel(row)"
            >
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.pageNum"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <el-dialog v-model="detailVisible" title="订单详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="订单号">{{ orderDetail.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="订单状态">
          <el-tag :type="getStatusColor(orderDetail.status)">
            {{ getStatusName(orderDetail.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="收货人">{{ orderDetail.receiverName }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ orderDetail.receiverPhone }}</el-descriptions-item>
        <el-descriptions-item label="收货地址" :span="2">
          {{ orderDetail.receiverAddress }}
        </el-descriptions-item>
        <el-descriptions-item label="订单金额">¥{{ orderDetail.totalAmount }}</el-descriptions-item>
        <el-descriptions-item label="优惠金额">¥{{ orderDetail.discountAmount }}</el-descriptions-item>
        <el-descriptions-item label="实付金额">
          <span style="color: #F56C6C; font-weight: bold">¥{{ orderDetail.payAmount }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ orderDetail.createTime }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>订单商品</el-divider>

      <el-table :data="orderDetail.items" border>
        <el-table-column prop="productName" label="商品名称" />
        <el-table-column prop="skuName" label="规格" width="200" />
        <el-table-column prop="price" label="单价" width="120">
          <template #default="{ row }">¥{{ row.price }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="100" />
        <el-table-column prop="totalAmount" label="小计" width="120">
          <template #default="{ row }">¥{{ row.totalAmount }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrderList, getOrderById, cancelOrder, shipOrder } from '@/api/order'

const loading = ref(false)
const detailVisible = ref(false)
const orderList = ref([])
const orderDetail = ref({})

const searchForm = reactive({
  orderNo: '',
  status: null
})

const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const STATUS_MAP = {
  0: '待支付',
  1: '已支付',
  2: '已发货',
  3: '已完成',
  4: '已取消',
  5: '已退款'
}

const STATUS_COLOR_MAP = {
  0: 'warning',
  1: 'primary',
  2: 'info',
  3: 'success',
  4: 'danger',
  5: 'danger'
}

const getStatusName = (status) => STATUS_MAP[status] || '未知'
const getStatusColor = (status) => STATUS_COLOR_MAP[status] || 'info'

const fetchOrderList = async () => {
  loading.value = true
  try {
    const res = await getOrderList({
      ...searchForm,
      pageNum: pagination.pageNum,
      pageSize: pagination.pageSize
    })
    orderList.value = res.data.records || []
    pagination.total = res.data.total || 0
  } catch (error) {
    console.error('获取订单列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.pageNum = 1
  fetchOrderList()
}

const handleReset = () => {
  searchForm.orderNo = ''
  searchForm.status = null
  handleSearch()
}

const handleDetail = async (row) => {
  try {
    const res = await getOrderById(row.id)
    orderDetail.value = res.data
    detailVisible.value = true
  } catch (error) {
    console.error('获取订单详情失败:', error)
  }
}

const handleShip = (row) => {
  ElMessageBox.confirm('确定要发货吗?', '提示', {
    type: 'warning'
  }).then(async () => {
    await shipOrder(row.id)
    ElMessage.success('发货成功')
    fetchOrderList()
  })
}

const handleCancel = (row) => {
  ElMessageBox.confirm('确定要取消该订单吗?', '提示', {
    type: 'warning'
  }).then(async () => {
    await cancelOrder(row.id)
    ElMessage.success('订单已取消')
    fetchOrderList()
  })
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  fetchOrderList()
}

const handleCurrentChange = (val) => {
  pagination.pageNum = val
  fetchOrderList()
}

onMounted(() => {
  fetchOrderList()
})
</script>

<style scoped>
.orders-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}
</style>
