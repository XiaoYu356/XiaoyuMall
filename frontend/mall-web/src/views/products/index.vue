<template>
  <div class="products-page">
    <div class="container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>商品列表</el-breadcrumb-item>
      </el-breadcrumb>

      <div class="filter-section">
        <div class="filter-row">
          <span class="filter-label">分类：</span>
          <div class="filter-options">
            <span
              class="filter-option"
              :class="{ active: !searchForm.categoryId }"
              @click="selectCategory(null)"
            >全部</span>
            <span
              v-if="parentCategory"
              class="filter-option"
              @click="selectCategory(parentCategory.id)"
            >‹ 返回{{ parentCategory.categoryName }}</span>
            <span
              v-for="cat in visibleCategories"
              :key="cat.id"
              class="filter-option"
              :class="{ active: searchForm.categoryId === cat.id }"
              @click="selectCategory(cat.id)"
            >{{ cat.name }} ({{ cat.count }})</span>
            <span
              v-if="categories.length > MAX_VISIBLE_CATEGORIES"
              class="filter-option more-toggle"
              @click="categoryExpanded = !categoryExpanded"
            >{{ categoryExpanded ? '收起' : `更多 (${categories.length - MAX_VISIBLE_CATEGORIES})` }}</span>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">品牌：</span>
          <div class="filter-options">
            <span
              class="filter-option"
              :class="{ active: !searchForm.brandId }"
              @click="searchForm.brandId = null; handleSearch()"
            >全部</span>
            <span
              v-for="brand in brandFilters"
              :key="brand.name"
              class="filter-option"
              :class="{ active: searchForm.brandId === getBrandId(brand.name) }"
              @click="toggleBrand(brand.name)"
            >{{ brand.name }} ({{ brand.count }})</span>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">价格：</span>
          <div class="filter-options">
            <span
              class="filter-option"
              :class="{ active: !searchForm.minPrice && !searchForm.maxPrice }"
              @click="clearPriceFilter"
            >全部</span>
            <span
              v-for="range in priceRanges"
              :key="range.label"
              class="filter-option"
              :class="{ active: isPriceRangeActive(range) }"
              @click="applyPriceRange(range)"
            >¥{{ range.label }}</span>
            <span class="price-input-group">
              <el-input-number v-model="customMinPrice" :min="0" :controls="false" size="small" placeholder="最低价" style="width: 80px" />
              <span class="price-sep">-</span>
              <el-input-number v-model="customMaxPrice" :min="0" :controls="false" size="small" placeholder="最高价" style="width: 80px" />
              <el-button size="small" type="primary" @click="applyCustomPrice">确定</el-button>
            </span>
          </div>
        </div>
      </div>

      <div class="sort-section">
        <span class="sort-label">排序：</span>
        <el-radio-group v-model="searchForm.sortBy" size="small" @change="handleSearch">
          <el-radio-button value="default">综合</el-radio-button>
          <el-radio-button value="sales">销量</el-radio-button>
          <el-radio-button value="newest">最新</el-radio-button>
          <el-radio-button value="price_asc">价格↑</el-radio-button>
          <el-radio-button value="price_desc">价格↓</el-radio-button>
        </el-radio-group>
        <span class="result-count">共 {{ pagination.total }} 件商品</span>
      </div>

      <div v-loading="loading" class="product-list">
        <div
          v-for="product in products"
          :key="product.id"
          class="product-item"
          @click="goToDetail(product.id)"
        >
          <el-image :src="product.mainImage" fit="cover" class="product-image">
            <template #error>
              <div class="image-placeholder">
                <el-icon :size="60"><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          <div class="product-info">
            <h3 class="product-name" v-html="product.productName"></h3>
            <p class="product-desc" v-if="product.description" v-html="truncateDescription(product.description)"></p>
            <div class="price-row">
              <span class="price">¥{{ product.price }}</span>
              <span v-if="product.originalPrice && product.originalPrice > product.price" class="original-price">¥{{ product.originalPrice }}</span>
              <span v-if="product.originalPrice && product.originalPrice > product.price" class="discount-tag">{{ Math.round((1 - product.price / product.originalPrice) * 100) }}% OFF</span>
            </div>
            <p class="sales">已售 {{ product.sales || 0 }} 件</p>
          </div>
        </div>
      </div>

      <el-empty v-if="!loading && products.length === 0" description="暂无商品" />

      <el-pagination
        v-model:current-page="pagination.pageNum"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[12, 24, 48]"
        layout="total, sizes, prev, pager, next"
        @current-change="fetchProducts"
        @size-change="handleSearch"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Picture } from '@element-plus/icons-vue'
import { getProductList, getCategories, getBrandList, getSearchFilters } from '@/api/product'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const products = ref([])
const categoryList = ref([])
const categories = ref([])
const categoryExpanded = ref(false)
const MAX_VISIBLE_CATEGORIES = 8
const brandFilters = ref([])
const priceRanges = ref([])
const customMinPrice = ref(null)
const customMaxPrice = ref(null)
const brandIdMap = ref({})

const searchForm = reactive({
  keyword: '',
  categoryId: null,
  brandId: null,
  minPrice: null,
  maxPrice: null,
  sortBy: 'default'
})

const pagination = reactive({
  pageNum: 1,
  pageSize: 12,
  total: 0
})

const currentCategory = computed(() =>
  categoryList.value.find(c => c.id === searchForm.categoryId) || null
)

// 有父分类时展示“返回上级”，避免只能一路点“全部”重置
const parentCategory = computed(() => {
  const parentId = currentCategory.value?.parentId
  if (!parentId) return null
  return categoryList.value.find(c => c.id === parentId) || null
})

const visibleCategories = computed(() =>
  categoryExpanded.value
    ? categories.value
    : categories.value.slice(0, MAX_VISIBLE_CATEGORIES)
)

const selectCategory = (categoryId) => {
  searchForm.categoryId = categoryId
  handleSearch()
}

watch(categories, () => {
  categoryExpanded.value = false
})

onMounted(() => {
  if (route.query.keyword) {
    searchForm.keyword = route.query.keyword
  }
  if (route.query.categoryId) {
    searchForm.categoryId = Number(route.query.categoryId)
  }
  fetchCategories()
  fetchProducts()
})

watch(() => route.query, (query) => {
  // keyword 被清空（query 里没有 keyword）时也要同步，否则会一直保留上一次的搜索结果
  const nextKeyword = query.keyword || ''
  const nextCategoryId = query.categoryId ? Number(query.categoryId) : null
  let needRefresh = false
  if (nextKeyword !== searchForm.keyword) {
    searchForm.keyword = nextKeyword
    needRefresh = true
  }
  if (nextCategoryId !== searchForm.categoryId) {
    searchForm.categoryId = nextCategoryId
    needRefresh = true
  }
  if (needRefresh) {
    pagination.pageNum = 1
    fetchProducts()
  }
})

const fetchCategories = async () => {
  try {
    const res = await getCategories()
    categoryList.value = res.data || []
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

const fetchProducts = async () => {
  loading.value = true
  try {
    const params = {
      pageNum: pagination.pageNum,
      pageSize: pagination.pageSize,
      sortBy: searchForm.sortBy
    }
    if (searchForm.keyword) params.keyword = searchForm.keyword
    if (searchForm.categoryId) params.categoryId = searchForm.categoryId
    if (searchForm.brandId) params.brandId = searchForm.brandId
    if (searchForm.minPrice != null) params.minPrice = searchForm.minPrice
    if (searchForm.maxPrice != null) params.maxPrice = searchForm.maxPrice
    const res = await getProductList(params)
    products.value = res.data?.records || []
    pagination.total = res.data?.total || 0
    fetchFilters()
  } catch (error) {
    console.error('获取商品失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchFilters = async () => {
  try {
    const params = {}
    if (searchForm.keyword) params.keyword = searchForm.keyword
    if (searchForm.categoryId) params.categoryId = searchForm.categoryId
    const [filtersRes, brandsRes] = await Promise.all([
      getSearchFilters(params),
      getBrandList()
    ])
    if (filtersRes.data) {
      brandFilters.value = filtersRes.data.brands || []
      priceRanges.value = filtersRes.data.priceRanges || []
      categories.value = filtersRes.data.categories || []
    }
    if (brandsRes.data) {
      const map = {}
      brandsRes.data.forEach(b => {
        map[b.brandName] = b.id
      })
      brandIdMap.value = map
    }
  } catch (error) {
    console.error('获取筛选条件失败:', error)
  }
}

const handleSearch = () => {
  pagination.pageNum = 1
  fetchProducts()
}

const getBrandId = (brandName) => {
  return brandIdMap.value[brandName]
}

const toggleBrand = (brandName) => {
  const id = brandIdMap.value[brandName]
  if (searchForm.brandId === id) {
    searchForm.brandId = null
  } else {
    searchForm.brandId = id
  }
  handleSearch()
}

const clearPriceFilter = () => {
  searchForm.minPrice = null
  searchForm.maxPrice = null
  customMinPrice.value = null
  customMaxPrice.value = null
  handleSearch()
}

const isPriceRangeActive = (range) => {
  return searchForm.minPrice === range.min && searchForm.maxPrice === range.max
}

const applyPriceRange = (range) => {
  searchForm.minPrice = range.min
  searchForm.maxPrice = range.max
  customMinPrice.value = null
  customMaxPrice.value = null
  handleSearch()
}

const applyCustomPrice = () => {
  if (customMinPrice.value != null) searchForm.minPrice = customMinPrice.value
  if (customMaxPrice.value != null) searchForm.maxPrice = customMaxPrice.value
  handleSearch()
}

const truncateDescription = (desc) => {
  if (!desc) return ''
  const plainText = desc.replace(/<[^>]*>/g, '')
  return plainText.length > 60 ? plainText.substring(0, 60) + '...' : plainText
}

const goToDetail = (id) => {
  router.push(`/product/${id}`)
}
</script>

<style scoped>
.products-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.filter-section {
  background: white;
  border-radius: 8px;
  padding: 15px 20px;
  margin-bottom: 15px;
}

.filter-row {
  display: flex;
  align-items: flex-start;
  padding: 8px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.filter-row:last-child {
  border-bottom: none;
}

.filter-label {
  width: 60px;
  font-size: 14px;
  color: #666;
  line-height: 32px;
  flex-shrink: 0;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  flex: 1;
}

.filter-option {
  padding: 4px 12px;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  color: #333;
  transition: all 0.2s;
}

.filter-option:hover {
  color: #409EFF;
}

.filter-option.active {
  color: #409EFF;
  background: #ecf5ff;
}

.more-toggle {
  color: #999;
}

.price-input-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.price-sep {
  color: #999;
}

.sort-section {
  background: white;
  border-radius: 8px;
  padding: 10px 20px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.sort-label {
  font-size: 14px;
  color: #666;
}

.result-count {
  font-size: 13px;
  color: #999;
  margin-left: auto;
}

.product-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
  min-height: 200px;
}

.product-item {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
}

.product-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.product-image {
  width: 100%;
  height: 220px;
}

.image-placeholder {
  width: 100%;
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  color: #ccc;
}

.product-info {
  padding: 12px 15px;
}

.product-name {
  font-size: 14px;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.product-name :deep(.highlight) {
  color: #F56C6C;
  font-style: normal;
  font-weight: bold;
}

.product-desc {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-desc :deep(.highlight) {
  color: #F56C6C;
  font-style: normal;
}

.price-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;
}

.price {
  font-size: 20px;
  color: #F56C6C;
  font-weight: bold;
}

.original-price {
  font-size: 13px;
  color: #ccc;
  text-decoration: line-through;
}

.discount-tag {
  font-size: 11px;
  color: white;
  background: #F56C6C;
  padding: 1px 4px;
  border-radius: 3px;
}

.sales {
  font-size: 12px;
  color: #999;
}

@media (max-width: 1024px) {
  .product-list {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .product-list {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
