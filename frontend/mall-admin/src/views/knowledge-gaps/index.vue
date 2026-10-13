<template>
  <div class="knowledge-gaps">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>知识库缺口</span>
          <div class="filters">
            <el-select v-model="filters.status" placeholder="状态" clearable @change="loadData" style="width:120px">
              <el-option label="待处理" :value="0" />
              <el-option label="已补知识" :value="1" />
              <el-option label="已忽略" :value="2" />
            </el-select>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="gaps" v-loading="loading" stripe>
        <el-table-column prop="query" label="用户问题" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.gap_type === 1 ? 'danger' : 'warning'" size="small">
              {{ row.gap_type === 1 ? '全缺口' : '弱覆盖' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hit_count" label="触发次数" width="90" sortable />
        <el-table-column label="附加信息" min-width="200">
          <template #default="{ row }">
            <span v-if="row.detail">
              {{ row.detail.score ? 'score=' + row.detail.score : 'rrf=' + (row.detail.rrf_top1 || '-') }}
              {{ row.detail.candidate ? ' | ' + row.detail.candidate : '' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最近触发" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="goAddFaq(row)" :disabled="row.status === 1">
              补知识
            </el-button>
            <el-button size="small" @click="ignoreGap(row)" :disabled="row.status === 2">忽略</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page.current"
        v-model:page-size="page.size"
        :total="page.total"
        @current-change="loadData"
        layout="total, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getGapList, updateGapStatus } from '@/api/knowledge'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const gaps = ref([])
const page = reactive({ current: 1, size: 50, total: 0 })
const filters = reactive({ status: undefined })

const loadData = async () => {
  loading.value = true
  try {
    const res = await getGapList({
      status: filters.status,
      limit: page.size,
      offset: (page.current - 1) * page.size
    })
    gaps.value = res.data || []
    page.total = res.total || 0
  } catch (e) {
    // 错误已由 request 拦截器提示
  } finally {
    loading.value = false
  }
}

const statusText = (s) => ({ 0: '待处理', 1: '已补', 2: '已忽略' }[s] || '未知')
const statusType = (s) => ({ 0: 'warning', 1: 'success', 2: 'info' }[s] || 'info')

const goAddFaq = (row) => {
  router.push({ path: '/knowledge/faqs', query: { gapQuery: row.query, gapId: row.id } })
}

const ignoreGap = async (row) => {
  try {
    await updateGapStatus(row.id, { status: 2 })
    ElMessage.success('已忽略')
    loadData()
  } catch (e) { /* */ }
}

onMounted(loadData)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filters {
  display: flex;
  gap: 12px;
}
</style>
