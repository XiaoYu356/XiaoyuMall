<template>
  <div class="products-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>商品管理</span>
          <el-button type="primary" v-permission="'product:add'" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加商品
          </el-button>
        </div>
      </template>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="商品名称">
          <el-input v-model="searchForm.keyword" placeholder="请输入商品名称" clearable />
        </el-form-item>
        <el-form-item label="分类">
          <el-tree-select
            v-model="searchForm.categoryId"
            :data="categoryTreeOptions"
            :props="{ label: 'categoryName', value: 'id', children: 'children' }"
            placeholder="请选择分类"
            clearable
            check-strictly
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="productList" border stripe v-loading="loading">
        <el-table-column type="index" label="#" width="60" />
        <el-table-column label="商品" min-width="260">
          <template #default="{ row }">
            <div class="product-info">
              <el-image v-if="row.mainImage" :src="row.mainImage" class="product-thumb" fit="cover" />
              <div class="product-text">
                <div class="product-name">{{ row.productName }}</div>
                <div class="product-code">{{ row.productCode }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="120">
          <template #default="{ row }">
            <span style="color: #F56C6C">¥{{ row.price }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="brandName" label="品牌" width="120">
          <template #default="{ row }">
            <span>{{ row.brandName || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sales" label="销量" width="100" />
        <el-table-column prop="totalStock" label="库存" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.totalStock <= 10 ? '#F56C6C' : '#67C23A' }">
              {{ row.totalStock || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? '上架' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180" />
        <el-table-column label="操作" fixed="right" width="300">
          <template #default="{ row }">
            <el-button
              type="info"
              size="small"
              @click="handleDetail(row)"
            >
              详情
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
              :type="row.status === 1 ? 'warning' : 'success'"
              size="small"
              v-permission="'product:edit'"
              @click="handleStatusChange(row)"
            >
              {{ row.status === 1 ? '下架' : '上架' }}
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="960px" top="5vh">
      <el-form :model="productForm" :rules="rules" ref="productFormRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="商品名称" prop="productName">
              <el-input v-model="productForm.productName" placeholder="请输入商品名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="商品编码" prop="productCode">
              <el-input v-model="productForm.productCode" placeholder="请输入商品编码" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分类" prop="categoryId">
              <el-tree-select
                v-model="productForm.categoryId"
                :data="categoryTreeOptions"
                :props="{ label: 'categoryName', value: 'id', children: 'children' }"
                placeholder="请选择分类"
                clearable
                check-strictly
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-select v-model="productForm.brandId" placeholder="请选择品牌" clearable style="width: 100%">
                <el-option v-for="brand in brandList" :key="brand.id" :label="brand.brandName" :value="brand.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="销售价" prop="price">
              <el-input-number
                v-model="productForm.price"
                :min="0"
                :precision="2"
                :disabled="generatedSkuList.length > 0"
                style="width: 100%"
              />
              <div v-if="generatedSkuList.length > 0" class="price-tip">有SKU时自动取最低SKU价格</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="商品主图">
          <div class="upload-area">
            <el-upload
              class="main-image-uploader"
              :show-file-list="false"
              :http-request="handleMainImageUpload"
              accept="image/*"
            >
              <el-image v-if="productForm.mainImage" :src="productForm.mainImage" fit="cover" class="uploaded-image" />
              <el-icon v-else class="upload-icon"><Plus /></el-icon>
            </el-upload>
            <el-button v-if="productForm.mainImage" type="danger" text size="small" @click="productForm.mainImage = ''" style="margin-left: 8px">删除</el-button>
          </div>
        </el-form-item>
        <el-form-item label="商品描述">
          <el-input v-model="productForm.description" type="textarea" :rows="2" placeholder="请输入商品描述" />
        </el-form-item>

        <el-divider content-position="left">商品规格</el-divider>

        <div v-if="!productForm.id" class="spec-section">
          <div class="spec-header">
            <el-button type="primary" size="small" @click="addSpec">添加规格</el-button>
            <span class="spec-tip">如：颜色(黑/白)、内存(128G/256G)，系统自动生成SKU组合</span>
          </div>

          <div v-for="(spec, sIdx) in specList" :key="sIdx" class="spec-row">
            <el-input v-model="spec.name" placeholder="规格名(如:颜色)" style="width: 140px" />
            <span class="spec-colon">:</span>
            <div class="spec-values">
              <el-tag
                v-for="(val, vIdx) in spec.values"
                :key="vIdx"
                closable
                @close="removeSpecValue(sIdx, vIdx)"
                class="spec-tag"
              >
                {{ val }}
              </el-tag>
              <el-input
                v-if="spec.inputVisible"
                v-model="spec.inputValue"
                size="small"
                style="width: 100px"
                @keyup.enter="confirmSpecValue(sIdx)"
                @blur="confirmSpecValue(sIdx)"
              />
              <el-button v-else size="small" @click="showSpecInput(sIdx)">+ 添加</el-button>
            </div>
            <el-button type="danger" text @click="removeSpec(sIdx)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>

          <div v-if="editableSkuList.length > 0" class="sku-table-section">
            <div class="sku-table-header">
              <h4>SKU 列表（共 {{ editableSkuList.length }} 项）</h4>
              <div class="batch-set">
                <span class="batch-label">批量设置：</span>
                <el-input-number v-model="batchPrice" :min="0" :precision="2" size="small" placeholder="价格" style="width: 120px" />
                <el-input-number v-model="batchStock" :min="0" size="small" placeholder="库存" style="width: 100px" />
                <el-button type="primary" size="small" @click="applyBatchSet">应用</el-button>
              </div>
            </div>
            <el-table :data="editableSkuList" border size="small" max-height="400">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column
                v-for="spec in specList"
                :key="spec.name"
                :label="spec.name"
                width="120"
              >
                <template #default="{ row }">
                  {{ row.specs[spec.name] }}
                </template>
              </el-table-column>
              <el-table-column label="SKU名称" min-width="160">
                <template #default="{ row }">
                  <el-input v-model="row.skuName" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="图片" width="90">
                <template #default="{ row }">
                  <el-upload
                    :show-file-list="false"
                    :http-request="(opts) => handleSkuImageUpload(row, opts)"
                    accept="image/*"
                  >
                    <el-image v-if="row.image" :src="row.image" fit="cover" class="sku-thumb" />
                    <el-icon v-else class="sku-upload-icon"><Plus /></el-icon>
                  </el-upload>
                </template>
              </el-table-column>
              <el-table-column label="价格" width="130">
                <template #default="{ row }">
                  <el-input-number v-model="row.price" :min="0" :precision="2" size="small" style="width: 100%" @change="updateProductPrice" />
                </template>
              </el-table-column>
              <el-table-column label="库存" width="120">
                <template #default="{ row }">
                  <el-input-number v-model="row.stock" :min="0" size="small" style="width: 100%" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-else class="spec-section">
          <el-empty v-if="editSkuList.length === 0" description="暂无SKU数据" :image-size="60" />
          <el-table v-else :data="editSkuList" border size="small">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="skuName" label="SKU名称" min-width="160" />
            <el-table-column label="图片" width="90">
              <template #default="{ row }">
                <el-image v-if="row.image" :src="row.image" fit="cover" class="sku-thumb" />
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="120">
              <template #default="{ row }">
                ¥{{ row.price }}
              </template>
            </el-table-column>
            <el-table-column prop="stock" label="库存" width="120">
              <template #default="{ row }">
                <span :style="{ color: row.stock <= 10 ? '#F56C6C' : '#67C23A' }">{{ row.stock }}</span>
              </template>
            </el-table-column>
            <el-table-column label="规格" min-width="150">
              <template #default="{ row }">
                <template v-if="row.specsObj">
                  <el-tag v-for="(val, key) in row.specsObj" :key="key" size="small" class="spec-tag">
                    {{ key }}: {{ val }}
                  </el-tag>
                </template>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="商品详情" width="800px" top="5vh">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="商品名称" :span="2">{{ detailData.productName }}</el-descriptions-item>
        <el-descriptions-item label="商品编码">{{ detailData.productCode }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ detailData.categoryName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="品牌">{{ detailData.brandName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="销售价">
          <span style="color: #F56C6C; font-weight: bold">¥{{ detailData.price }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailData.status === 1 ? 'success' : 'danger'">
            {{ detailData.status === 1 ? '上架' : '下架' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="销量">{{ detailData.sales || 0 }}</el-descriptions-item>
        <el-descriptions-item label="库存">
          <span :style="{ color: (detailData.totalStock || 0) <= 10 ? '#F56C6C' : '#67C23A' }">
            {{ detailData.totalStock || 0 }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detailData.createTime }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ detailData.updateTime || '-' }}</el-descriptions-item>
        <el-descriptions-item label="商品主图" :span="2">
          <el-image
            v-if="detailData.mainImage"
            :src="detailData.mainImage"
            fit="cover"
            style="width: 200px; height: 200px; border-radius: 6px"
            :preview-src-list="[detailData.mainImage]"
          />
          <span v-else>暂无图片</span>
        </el-descriptions-item>
        <el-descriptions-item label="商品描述" :span="2">{{ detailData.description || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">SKU 信息</el-divider>
      <el-empty v-if="detailSkuList.length === 0" description="暂无SKU数据" :image-size="60" />
      <el-table v-else :data="detailSkuList" border size="small">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="skuName" label="SKU名称" min-width="160" />
        <el-table-column label="图片" width="90">
          <template #default="{ row }">
            <el-image
              v-if="row.image"
              :src="row.image"
              fit="cover"
              style="width: 50px; height: 50px; border-radius: 4px"
              :preview-src-list="[row.image]"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="120">
          <template #default="{ row }">
            <span style="color: #F56C6C">¥{{ row.price }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.stock <= 10 ? '#F56C6C' : '#67C23A' }">{{ row.stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="规格" min-width="150">
          <template #default="{ row }">
            <template v-if="row.specsObj">
              <el-tag v-for="(val, key) in row.specsObj" :key="key" size="small" style="margin-right: 4px">
                {{ key }}: {{ val }}
              </el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'
import { getCategoryList, getBrandList, getProductList, getProductById, createProduct, updateProduct, deleteProduct, getProductSkus, uploadFile } from '@/api/product'

const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const detailVisible = ref(false)
const detailData = ref({})
const detailSkuList = ref([])
const productList = ref([])
const categoryList = ref([])
const brandList = ref([])
const productFormRef = ref(null)
const editSkuList = ref([])
const uploading = ref(false)

const searchForm = reactive({
  keyword: '',
  categoryId: null
})

const pagination = reactive({
  pageNum: 1,
  pageSize: 10,
  total: 0
})

const productForm = reactive({
  id: null,
  productName: '',
  productCode: '',
  categoryId: null,
  brandId: null,
  price: 0,
  mainImage: '',
  description: '',
  sort: 0,
  status: 1
})

const specList = ref([])
const batchPrice = ref(null)
const batchStock = ref(null)
const editableSkuList = ref([])

const doUpload = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await uploadFile(formData)
  return res.data
}

const handleMainImageUpload = async (options) => {
  try {
    uploading.value = true
    const url = await doUpload(options.file)
    productForm.mainImage = url
    ElMessage.success('主图上传成功')
  } catch (error) {
    console.error('主图上传失败:', error)
    ElMessage.error('主图上传失败')
  } finally {
    uploading.value = false
  }
}

const handleSkuImageUpload = async (row, options) => {
  try {
    const url = await doUpload(options.file)
    row.image = url
    ElMessage.success('SKU图片上传成功')
  } catch (error) {
    console.error('SKU图片上传失败:', error)
    ElMessage.error('SKU图片上传失败')
  }
}

const applyBatchSet = () => {
  if (batchPrice.value == null && batchStock.value == null) {
    ElMessage.warning('请输入要批量设置的价格或库存')
    return
  }
  editableSkuList.value.forEach(sku => {
    if (batchPrice.value != null) sku.price = batchPrice.value
    if (batchStock.value != null) sku.stock = batchStock.value
  })
  updateProductPrice()
  ElMessage.success('批量设置成功')
}

const updateProductPrice = () => {
  if (editableSkuList.value.length > 0) {
    const prices = editableSkuList.value.map(s => s.price).filter(p => p > 0)
    if (prices.length > 0) {
      productForm.price = Math.min(...prices)
    }
  }
}

const rules = {
  productName: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  productCode: [{ required: true, message: '请输入商品编码', trigger: 'blur' }],
  categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [{ required: true, message: '请输入销售价', trigger: 'blur' }]
}

const addSpec = () => {
  specList.value.push({ name: '', values: [], inputVisible: false, inputValue: '' })
}

const removeSpec = (idx) => {
  specList.value.splice(idx, 1)
}

const showSpecInput = (idx) => {
  specList.value[idx].inputVisible = true
}

const confirmSpecValue = (idx) => {
  const spec = specList.value[idx]
  const val = spec.inputValue?.trim()
  if (val && !spec.values.includes(val)) {
    spec.values.push(val)
  }
  spec.inputVisible = false
  spec.inputValue = ''
}

const removeSpecValue = (sIdx, vIdx) => {
  specList.value[sIdx].values.splice(vIdx, 1)
}

const cartesian = (arrays) => {
  if (arrays.length === 0) return [[]]
  return arrays.reduce((acc, arr) => {
    const result = []
    acc.forEach(combo => {
      arr.forEach(item => {
        result.push([...combo, item])
      })
    })
    return result
  }, [[]])
}

const generatedSkuList = computed(() => {
  const validSpecs = specList.value.filter(s => s.name && s.values.length > 0)
  if (validSpecs.length === 0) return []

  const names = validSpecs.map(s => s.name)
  const valueArrays = validSpecs.map(s => s.values)
  const combinations = cartesian(valueArrays)

  return combinations.map(combo => {
    const specs = {}
    names.forEach((name, i) => {
      specs[name] = combo[i]
    })
    const skuName = productForm.productName
      ? productForm.productName + ' ' + combo.join(' ')
      : combo.join(' ')

    return {
      skuName,
      skuCode: productForm.productCode ? `${productForm.productCode}-${combo.join('-')}` : '',
      price: productForm.price || 0,
      stock: 0,
      image: '',
      specs
    }
  })
})

watch(generatedSkuList, (newList) => {
  if (newList.length > 0) {
    editableSkuList.value = newList.map(sku => ({ ...sku }))
  } else {
    editableSkuList.value = []
  }
  updateProductPrice()
}, { deep: true })

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

const fetchCategoryList = async () => {
  try {
    const res = await getCategoryList()
    categoryList.value = res.data || []
  } catch (error) {
    console.error('获取分类列表失败:', error)
  }
}

const fetchBrandList = async () => {
  try {
    const res = await getBrandList()
    brandList.value = res.data || []
  } catch (error) {
    console.error('获取品牌列表失败:', error)
  }
}

const fetchProductList = async () => {
  loading.value = true
  try {
    const res = await getProductList({
      ...searchForm,
      pageNum: pagination.pageNum,
      pageSize: pagination.pageSize
    })
    productList.value = res.data.records || []
    pagination.total = res.data.total || 0
  } catch (error) {
    console.error('获取商品列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.pageNum = 1
  fetchProductList()
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.categoryId = null
  handleSearch()
}

const handleAdd = () => {
  dialogTitle.value = '添加商品'
  Object.assign(productForm, {
    id: null,
    productName: '',
    productCode: '',
    categoryId: null,
    brandId: null,
    price: 0,
    mainImage: '',
    description: '',
    sort: 0,
    status: 1
  })
  specList.value = []
  editSkuList.value = []
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  dialogTitle.value = '编辑商品'
  Object.assign(productForm, { ...row })
  specList.value = []
  editSkuList.value = []

  try {
    const res = await getProductSkus(row.id)
    const skus = res.data || []
    editSkuList.value = skus.map(sku => ({
      ...sku,
      specsObj: sku.specs ? JSON.parse(sku.specs) : null
    }))
  } catch (error) {
    console.error('获取SKU列表失败:', error)
  }

  dialogVisible.value = true
}

const getCategoryPath = (categoryId) => {
  const parts = []
  let current = categoryList.value.find(c => c.id === categoryId)
  while (current) {
    parts.unshift(current.categoryName)
    current = current.parentId
      ? categoryList.value.find(c => c.id === current.parentId)
      : null
  }
  return parts.length > 0 ? parts.join(' > ') : '-'
}

const handleDetail = async (row) => {
  try {
    const res = await getProductById(row.id)
    const product = res.data || {}
    detailData.value = {
      ...product,
      categoryName: getCategoryPath(product.categoryId)
    }

    const skuRes = await getProductSkus(row.id)
    const skus = skuRes.data || []
    detailSkuList.value = skus.map(sku => ({
      ...sku,
      specsObj: sku.specs ? JSON.parse(sku.specs) : null
    }))

    detailVisible.value = true
  } catch (error) {
    console.error('获取商品详情失败:', error)
    ElMessage.error('获取商品详情失败')
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该商品吗?', '提示', {
    type: 'warning'
  }).then(async () => {
    await deleteProduct(row.id)
    ElMessage.success('删除成功')
    fetchProductList()
  })
}

const handleStatusChange = async (row) => {
  const newStatus = row.status === 1 ? 0 : 1
  try {
    await updateProduct({ id: row.id, status: newStatus })
    ElMessage.success(newStatus === 1 ? '上架成功' : '下架成功')
    fetchProductList()
  } catch (error) {
    console.error('操作失败:', error)
  }
}

const handleSubmit = async () => {
  if (!productFormRef.value) return

  await productFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      if (productForm.id) {
        await updateProduct(productForm)
        ElMessage.success('更新成功')
      } else {
        const data = { ...productForm }
        if (editableSkuList.value.length > 0) {
          data.skuList = editableSkuList.value
        }
        await createProduct(data)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchProductList()
    } catch (error) {
      console.error('操作失败:', error)
    }
  })
}

const handleSizeChange = (val) => {
  pagination.pageSize = val
  fetchProductList()
}

const handleCurrentChange = (val) => {
  pagination.pageNum = val
  fetchProductList()
}

onMounted(() => {
  fetchCategoryList()
  fetchBrandList()
  fetchProductList()
})
</script>

<style scoped>
.products-container {
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

.product-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.product-thumb {
  width: 50px;
  height: 50px;
  border-radius: 4px;
  flex-shrink: 0;
}

.product-text {
  overflow: hidden;
}

.product-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-code {
  font-size: 12px;
  color: #909399;
}

.upload-area {
  display: flex;
  align-items: center;
}

.main-image-uploader :deep(.el-upload) {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: border-color 0.3s;
}

.main-image-uploader :deep(.el-upload:hover) {
  border-color: #409eff;
}

.uploaded-image {
  width: 120px;
  height: 120px;
}

.upload-icon {
  font-size: 28px;
  color: #8c939d;
}

.sku-thumb {
  width: 50px;
  height: 50px;
  border-radius: 4px;
  cursor: pointer;
}

.sku-upload-icon {
  font-size: 20px;
  color: #8c939d;
  width: 50px;
  height: 50px;
  border: 1px dashed #d9d9d9;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color 0.3s;
}

.sku-upload-icon:hover {
  border-color: #409eff;
}

.spec-section {
  margin-bottom: 16px;
}

.spec-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.spec-tip {
  color: #909399;
  font-size: 12px;
}

.spec-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}

.spec-colon {
  font-size: 18px;
  color: #999;
  font-weight: bold;
}

.spec-values {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.spec-tag {
  margin-right: 4px;
}

.sku-table-section {
  margin-top: 16px;
}

.sku-table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.sku-table-header h4 {
  margin: 0;
  color: #333;
}

.batch-set {
  display: flex;
  align-items: center;
  gap: 8px;
}

.batch-label {
  color: #909399;
  font-size: 13px;
}

.price-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
