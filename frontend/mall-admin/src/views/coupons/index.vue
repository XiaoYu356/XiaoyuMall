<template>
  <div class="coupons-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>优惠券管理</span>
          <el-button type="primary" v-permission="'coupon:add'" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加优惠券
          </el-button>
        </div>
      </template>

      <el-table :data="couponList" border stripe v-loading="loading">
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="templateName" label="优惠券名称" width="200" />
        <el-table-column prop="couponType" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.couponType)">
              {{ getTypeName(row.couponType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="couponValue" label="优惠值" width="120">
          <template #default="{ row }">
            {{ row.couponType === 2 ? row.couponValue + '折' : '¥' + row.couponValue }}
          </template>
        </el-table-column>
        <el-table-column prop="minAmount" label="最低消费" width="120">
          <template #default="{ row }">
            ¥{{ row.minAmount }}
          </template>
        </el-table-column>
        <el-table-column prop="totalCount" label="发行总量" width="120" />
        <el-table-column prop="usedCount" label="已使用" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" fixed="right" width="250">
          <template #default="{ row }">
            <el-button
              type="info"
              size="small"
              @click="handleDetail(row)"
            >
              详情
            </el-button>
            <el-tooltip :content="canEdit(row) ? '' : '已发放的优惠券不可编辑'" placement="top" :disabled="canEdit(row)">
              <el-button
                type="primary"
                size="small"
                v-permission="'coupon:edit'"
                :disabled="!canEdit(row)"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
            </el-tooltip>
            <el-button
              type="danger"
              size="small"
              v-permission="'coupon:delete'"
              @click="handleDelete(row)"
            >
              删除
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="couponForm" :rules="rules" ref="couponFormRef" label-width="100px">
        <el-form-item label="优惠券名称" prop="templateName">
          <el-input v-model="couponForm.templateName" placeholder="请输入优惠券名称" />
        </el-form-item>
        <el-form-item label="类型" prop="couponType">
          <el-select v-model="couponForm.couponType" placeholder="请选择类型">
            <el-option label="满减券" :value="1" />
            <el-option label="折扣券" :value="2" />
            <el-option label="现金券" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="优惠值" prop="couponValue">
          <el-input-number
            v-model="couponForm.couponValue"
            :min="couponForm.couponType === 2 ? 1 : 0"
            :max="couponForm.couponType === 2 ? 9.9 : 99999"
            :precision="couponForm.couponType === 2 ? 1 : 2"
          />
        </el-form-item>
        <el-form-item label="最低消费">
          <el-input-number v-model="couponForm.minAmount" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="发行总量" prop="totalCount">
          <el-input-number v-model="couponForm.totalCount" :min="1" />
        </el-form-item>
        <el-form-item label="每人限领">
          <el-input-number v-model="couponForm.perLimit" :min="1" />
        </el-form-item>
        <el-form-item label="有效期" prop="dateRange">
          <el-date-picker
            v-model="couponForm.dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="优惠券详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="优惠券名称" :span="2">{{ detailData.templateName }}</el-descriptions-item>
        <el-descriptions-item label="类型">
          <el-tag :type="getTypeColor(detailData.couponType)">{{ getTypeName(detailData.couponType) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailData.status === 1 ? 'success' : 'danger'">
            {{ detailData.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="优惠值">
          {{ detailData.couponType === 2 ? detailData.couponValue + '折' : '¥' + detailData.couponValue }}
        </el-descriptions-item>
        <el-descriptions-item label="最低消费">¥{{ detailData.minAmount }}</el-descriptions-item>
        <el-descriptions-item label="发行总量">{{ detailData.totalCount }}</el-descriptions-item>
        <el-descriptions-item label="已领取">{{ detailData.totalCount - (detailData.remainCount ?? detailData.totalCount) }}</el-descriptions-item>
        <el-descriptions-item label="已使用">{{ detailData.usedCount }}</el-descriptions-item>
        <el-descriptions-item label="每人限领">{{ detailData.perLimit }}张</el-descriptions-item>
        <el-descriptions-item label="生效时间" :span="2">{{ detailData.startTime }}</el-descriptions-item>
        <el-descriptions-item label="过期时间" :span="2">{{ detailData.endTime }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ detailData.createTime }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCouponList, createCoupon, updateCoupon, deleteCoupon } from '@/api/coupon'
import { formatDateTime as formatDateTimeUtil } from '@/utils/time'

const loading = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const detailData = ref({})
const dialogTitle = ref('')
const couponList = ref([])
const couponFormRef = ref(null)

const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const couponForm = reactive({
  id: null,
  templateName: '',
  couponType: 1,
  couponValue: 0,
  minAmount: 0,
  totalCount: 100,
  perLimit: 1,
  dateRange: []
})

const rules = {
  templateName: [{ required: true, message: '请输入优惠券名称', trigger: 'blur' }],
  couponType: [{ required: true, message: '请选择类型', trigger: 'change' }],
  couponValue: [{ required: true, message: '请输入优惠值', trigger: 'blur' }],
  totalCount: [{ required: true, message: '请输入发行总量', trigger: 'blur' }],
  dateRange: [{ required: true, message: '请选择有效期', trigger: 'change' }]
}

const TYPE_NAME_MAP = { 1: '满减券', 2: '折扣券', 3: '现金券' }
const TYPE_COLOR_MAP = { 1: 'success', 2: 'warning', 3: 'danger' }

const getTypeName = (type) => TYPE_NAME_MAP[type] || '未知'
const getTypeColor = (type) => TYPE_COLOR_MAP[type] || 'info'

const canEdit = (row) => {
  return row.usedCount === 0
}

const fetchCouponList = async () => {
  loading.value = true
  try {
    const res = await getCouponList({
      pageNum: pagination.pageNum,
      pageSize: pagination.pageSize
    })
    couponList.value = res.data.records || []
    pagination.total = res.data.total || 0
  } catch (error) {
    console.error('获取优惠券列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleDetail = (row) => {
  detailData.value = { ...row }
  detailVisible.value = true
}

const handleAdd = () => {
  dialogTitle.value = '添加优惠券'
  Object.assign(couponForm, {
    id: null,
    templateName: '',
    couponType: 1,
    couponValue: 0,
    minAmount: 0,
    totalCount: 100,
    perLimit: 1,
    dateRange: []
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑优惠券'
  Object.assign(couponForm, {
    ...row,
    dateRange: row.startTime && row.endTime ? [row.startTime, row.endTime] : []
  })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该优惠券吗?', '提示', {
    type: 'warning'
  }).then(async () => {
    await deleteCoupon(row.id)
    ElMessage.success('删除成功')
    fetchCouponList()
  })
}

const formatDateTime = (date) => {
  return formatDateTimeUtil(date)
}

const handleSubmit = async () => {
  if (!couponFormRef.value) return

  await couponFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      const data = {
        ...couponForm,
        startTime: formatDateTime(couponForm.dateRange?.[0]),
        endTime: formatDateTime(couponForm.dateRange?.[1])
      }
      delete data.dateRange

      if (couponForm.id) {
        await updateCoupon(data)
        ElMessage.success('更新成功')
      } else {
        await createCoupon(data)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchCouponList()
    } catch (error) {
      console.error('操作失败:', error)
    }
  })
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  fetchCouponList()
}

const handleCurrentChange = (val) => {
  pagination.pageNum = val
  fetchCouponList()
}

onMounted(() => {
  fetchCouponList()
})
</script>

<style scoped>
.coupons-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
