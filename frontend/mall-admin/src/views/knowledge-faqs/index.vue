<template>
  <div class="knowledge-faqs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>FAQ 知识库</span>
          <div class="actions">
            <el-input v-model="filters.q" placeholder="搜索问题" clearable style="width:200px" @keyup.enter="loadData" />
            <el-button @click="loadData">搜索</el-button>
            <el-button type="primary" @click="openDialog()">新增</el-button>
            <el-button type="warning" @click="handleRebuild" :loading="rebuilding">重建索引</el-button>
          </div>
        </div>
      </template>

      <el-table :data="faqs" v-loading="loading" stripe>
        <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="answer" label="答案" min-width="250" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column label="同义问法" width="120">
          <template #default="{ row }">
            {{ row.similar_questions?.length || 0 }} 条
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑FAQ' : '新增FAQ'" width="700px">
      <el-form :model="dialog.form" label-width="100px">
        <el-form-item label="问题" required>
          <el-input v-model="dialog.form.question" placeholder="标准问题表述" />
        </el-form-item>
        <el-form-item label="答案" required>
          <el-input v-model="dialog.form.answer" type="textarea" :rows="4" placeholder="回答内容" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="dialog.form.category" placeholder="如：售后/退款/发货" />
        </el-form-item>
        <el-form-item label="同义问法">
          <div v-for="(_, i) in dialog.form.similar_questions" :key="i" class="similar-row">
            <el-input v-model="dialog.form.similar_questions[i]" placeholder="用户可能的问法" />
            <el-button @click="dialog.form.similar_questions.splice(i, 1)" text type="danger">删</el-button>
          </div>
          <el-button @click="dialog.form.similar_questions.push('')" text type="primary">+ 添加问法</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="dialog.saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getFaqList, createFaq, updateFaq, deleteFaq, rebuildIndex } from '@/api/knowledge'
import { updateGapStatus } from '@/api/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const rebuilding = ref(false)
const faqs = ref([])
const page = reactive({ current: 1, size: 50, total: 0 })
const filters = reactive({ q: '' })

const dialog = reactive({
  visible: false,
  isEdit: false,
  editId: null,
  saving: false,
  form: { question: '', answer: '', category: '', similar_questions: [] }
})

const loadData = async () => {
  loading.value = true
  try {
    const res = await getFaqList({
      q: filters.q,
      limit: page.size,
      offset: (page.current - 1) * page.size
    })
    faqs.value = res.data || []
    page.total = res.total || 0
  } catch (e) { /* */ } finally {
    loading.value = false
  }
}

const openDialog = (row) => {
  if (row) {
    dialog.isEdit = true
    dialog.editId = row.id
    dialog.form = {
      question: row.question,
      answer: row.answer,
      category: row.category || '',
      similar_questions: [...(row.similar_questions || [])]
    }
  } else {
    // 从缺口页跳转过来时预填 query
    const gapQuery = route.query.gapQuery
    dialog.isEdit = false
    dialog.editId = null
    dialog.form = {
      question: gapQuery || '',
      answer: '',
      category: '',
      similar_questions: []
    }
  }
  dialog.visible = true
}

const handleSave = async () => {
  if (!dialog.form.question || !dialog.form.answer) {
    ElMessage.warning('问题和答案不能为空')
    return
  }
  dialog.saving = true
  try {
    const data = { ...dialog.form, tags: [] }
    if (dialog.isEdit) {
      await updateFaq(dialog.editId, data)
    } else {
      await createFaq(data)
    }
    // 如果从缺口跳转来，标记缺口为已补
    if (route.query.gapId) {
      await updateGapStatus(route.query.gapId, { status: 1 })
    }
    ElMessage.success('保存成功')
    dialog.visible = false
    loadData()
  } catch (e) { /* */ } finally {
    dialog.saving = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除"${row.question}"？`, '提示', { type: 'warning' })
    await deleteFaq(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* */ }
}

const handleRebuild = async () => {
  try {
    await ElMessageBox.confirm('将从种子数据全量重建索引，当前ES中的手动新增/修改将被覆盖。确认？', '重建索引', { type: 'warning' })
    rebuilding.value = true
    const res = await rebuildIndex()
    ElMessage.success(`重建完成，共 ${res.data?.count || 0} 条`)
  } catch (e) { /* */ } finally {
    rebuilding.value = false
  }
}

onMounted(() => {
  loadData()
  // 从缺口页跳转来自动打开新增弹窗
  if (route.query.gapQuery) {
    openDialog()
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.actions {
  display: flex;
  gap: 8px;
}
.similar-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
</style>
