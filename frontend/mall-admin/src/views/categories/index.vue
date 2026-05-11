<template>
  <div class="categories-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>分类管理</span>
          <el-button type="primary" v-permission="'product:add'" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加分类
          </el-button>
        </div>
      </template>

      <el-table :data="categoryTreeData" border stripe v-loading="loading" row-key="id" default-expand-all>
        <el-table-column prop="categoryName" label="分类名称" min-width="200" />
        <el-table-column prop="categoryLevel" label="层级" width="80">
          <template #default="{ row }">
            <el-tag size="small">第{{ row.categoryLevel }}级</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="icon" label="图标" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.icon" size="20"><component :is="row.icon" /></el-icon>
            <span v-else style="color: #c0c4cc">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" fixed="right" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="handleMoveUp(row)" :disabled="isFirstInSiblings(row)">
              <el-icon><Top /></el-icon>
            </el-button>
            <el-button size="small" @click="handleMoveDown(row)" :disabled="isLastInSiblings(row)">
              <el-icon><Bottom /></el-icon>
            </el-button>
            <el-button
              type="primary"
              size="small"
              v-permission="'product:edit'"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              v-permission="'product:delete'"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="categoryForm" :rules="rules" ref="categoryFormRef" label-width="100px">
        <el-form-item label="分类名称" prop="categoryName">
          <el-input v-model="categoryForm.categoryName" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="父级分类">
          <el-tree-select
            v-model="categoryForm.parentId"
            :data="categoryTreeOptions"
            :props="{ label: 'categoryName', value: 'id', children: 'children' }"
            placeholder="不选则为一级分类"
            clearable
            check-strictly
            style="width: 100%"
            @change="handleParentChange"
          />
        </el-form-item>
        <el-form-item label="分类层级">
          <el-tag>{{ categoryForm.categoryLevel }}级分类</el-tag>
        </el-form-item>
        <el-form-item label="图标">
          <el-popover
            placement="bottom-start"
            :width="360"
            trigger="click"
            v-model:visible="iconPickerVisible"
          >
            <template #reference>
              <div class="icon-select-trigger">
                <el-icon v-if="categoryForm.icon" size="20"><component :is="categoryForm.icon" /></el-icon>
                <span v-else class="icon-placeholder">请选择图标</span>
                <el-button v-if="categoryForm.icon" type="danger" text size="small" @click.stop="clearIcon">
                  清除
                </el-button>
              </div>
            </template>
            <div class="icon-picker">
              <div
                v-for="icon in iconList"
                :key="icon"
                class="icon-item"
                :class="{ active: categoryForm.icon === icon }"
                @click="selectIcon(icon)"
              >
                <el-icon size="20"><component :is="icon" /></el-icon>
              </div>
            </div>
          </el-popover>
        </el-form-item>
        <el-form-item label="状态" v-if="categoryForm.id">
          <el-radio-group v-model="categoryForm.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Top, Bottom } from '@element-plus/icons-vue'
import { getCategoryList, createCategory, updateCategory, deleteCategory } from '@/api/product'

const iconList = [
  'Phone', 'Laptop', 'Monitor', 'Headset', 'Camera',
  'Watch', 'VideoCamera', 'Speaker', 'Mouse', 'Keyboard',
  'Printer', 'Cellphone', 'Van', 'Bicycle', 'ShoppingCart',
  'Goods', 'Box', 'Present', 'Cherry', 'Apple',
  'Grape', 'Coffee', 'IceCream', 'Bowl', 'KnifeFork',
  'Trophy', 'Medal', 'Star', 'Flag', 'Collection',
  'HomeFilled', 'House', 'School', 'OfficeBuilding', 'FirstAidKit',
  'Cpu', 'Connection', 'Opportunity', 'MagicStick', 'Setting'
]

const loading = ref(false)
const dialogVisible = ref(false)
const iconPickerVisible = ref(false)
const dialogTitle = ref('')
const categoryList = ref([])
const categoryFormRef = ref(null)

const categoryForm = reactive({
  id: null,
  parentId: 0,
  categoryName: '',
  categoryLevel: 1,
  icon: '',
  sort: 0,
  status: 1
})

const categoryTreeOptions = computed(() => {
  const list = categoryList.value.filter(c => c.status === 1)
  const map = {}
  const roots = []
  list.forEach(c => {
    map[c.id] = { ...c, children: [] }
  })
  list.forEach(c => {
    const node = map[c.id]
    if (c.parentId && map[c.parentId]) {
      map[c.parentId].children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
})

const categoryTreeData = computed(() => {
  const map = {}
  const roots = []
  categoryList.value.forEach(c => {
    map[c.id] = { ...c, children: [] }
  })
  categoryList.value.forEach(c => {
    const node = map[c.id]
    if (c.parentId && map[c.parentId]) {
      map[c.parentId].children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
})

const getSiblings = (row) => {
  if (row.parentId && row.parentId > 0) {
    return categoryList.value.filter(c => c.parentId === row.parentId).sort((a, b) => a.sort - b.sort)
  }
  return categoryList.value.filter(c => !c.parentId || c.parentId === 0).sort((a, b) => a.sort - b.sort)
}

const isFirstInSiblings = (row) => {
  const siblings = getSiblings(row)
  return siblings.length === 0 || siblings[0].id === row.id
}

const isLastInSiblings = (row) => {
  const siblings = getSiblings(row)
  return siblings.length === 0 || siblings[siblings.length - 1].id === row.id
}

const findCategoryById = (id) => {
  return categoryList.value.find(c => c.id === id)
}

const handleParentChange = (parentId) => {
  if (parentId) {
    const parent = findCategoryById(parentId)
    categoryForm.categoryLevel = parent ? parent.categoryLevel + 1 : 1
  } else {
    categoryForm.categoryLevel = 1
  }
}

const selectIcon = (icon) => {
  categoryForm.icon = icon
  iconPickerVisible.value = false
}

const clearIcon = () => {
  categoryForm.icon = ''
}

const rules = {
  categoryName: [{ required: true, message: '请输入分类名称', trigger: 'blur' }]
}

const fetchCategoryList = async () => {
  loading.value = true
  try {
    const res = await getCategoryList()
    categoryList.value = res.data || []
  } catch (error) {
    console.error('获取分类列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加分类'
  const sameLevelCategories = categoryList.value.filter(c => !categoryForm.parentId || c.parentId === 0)
  const maxSort = sameLevelCategories.length > 0
    ? Math.max(...sameLevelCategories.map(c => c.sort || 0))
    : 0
  Object.assign(categoryForm, {
    id: null,
    parentId: 0,
    categoryName: '',
    categoryLevel: 1,
    icon: '',
    sort: maxSort + 1,
    status: 1
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑分类'
  Object.assign(categoryForm, { ...row })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该分类吗？删除后不可恢复。', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteCategory(row.id)
      ElMessage.success('删除成功')
      fetchCategoryList()
    } catch (error) {
      console.error('删除分类失败:', error)
    }
  })
}

const handleMoveUp = async (row) => {
  const siblings = getSiblings(row)
  const idx = siblings.findIndex(c => c.id === row.id)
  if (idx <= 0) return
  const prev = siblings[idx - 1]
  const tempSort = row.sort
  try {
    await updateCategory({ id: row.id, sort: prev.sort, categoryName: row.categoryName, parentId: row.parentId, categoryLevel: row.categoryLevel, icon: row.icon })
    await updateCategory({ id: prev.id, sort: tempSort, categoryName: prev.categoryName, parentId: prev.parentId, categoryLevel: prev.categoryLevel, icon: prev.icon })
    ElMessage.success('上移成功')
    fetchCategoryList()
  } catch (error) {
    console.error('上移失败:', error)
  }
}

const handleMoveDown = async (row) => {
  const siblings = getSiblings(row)
  const idx = siblings.findIndex(c => c.id === row.id)
  if (idx === -1 || idx >= siblings.length - 1) return
  const next = siblings[idx + 1]
  const tempSort = row.sort
  try {
    await updateCategory({ id: row.id, sort: next.sort, categoryName: row.categoryName, parentId: row.parentId, categoryLevel: row.categoryLevel, icon: row.icon })
    await updateCategory({ id: next.id, sort: tempSort, categoryName: next.categoryName, parentId: next.parentId, categoryLevel: next.categoryLevel, icon: next.icon })
    ElMessage.success('下移成功')
    fetchCategoryList()
  } catch (error) {
    console.error('下移失败:', error)
  }
}

const handleSubmit = async () => {
  if (!categoryFormRef.value) return

  await categoryFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      if (categoryForm.id) {
        await updateCategory(categoryForm)
        ElMessage.success('更新成功')
      } else {
        const siblings = categoryForm.parentId && categoryForm.parentId > 0
          ? categoryList.value.filter(c => c.parentId === categoryForm.parentId)
          : categoryList.value.filter(c => !c.parentId || c.parentId === 0)
        const maxSort = siblings.length > 0
          ? Math.max(...siblings.map(c => c.sort || 0))
          : 0
        categoryForm.sort = maxSort + 1
        await createCategory(categoryForm)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchCategoryList()
    } catch (error) {
      console.error('操作失败:', error)
    }
  })
}

onMounted(() => {
  fetchCategoryList()
})
</script>

<style scoped>
.categories-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.icon-select-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
  min-height: 32px;
  min-width: 200px;
}

.icon-select-trigger:hover {
  border-color: var(--el-color-primary);
}

.icon-placeholder {
  color: #c0c4cc;
  font-size: 14px;
}

.icon-picker {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 4px;
}

.icon-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-item:hover {
  background-color: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.icon-item.active {
  background-color: var(--el-color-primary);
  color: #fff;
}
</style>
