<template>
  <div class="products-page">
    <div class="container">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item>商品列表</el-breadcrumb-item>
      </el-breadcrumb>

      <div class="filter-section">
        <el-input
          v-model="searchForm.keyword"
          placeholder="搜索商品"
          style="width: 300px"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>

        <el-select v-model="searchForm.categoryId" placeholder="选择分类" clearable @change="handleSearch">
          <el-option label="全部" :value="null" />
          <el-option
            v-for="category in categories"
            :key="category.id"
            :label="category.categoryName"
            :value="category.id"
          />
        </el-select>
      </div>

      <div class="product-list">
        <div
          v-for="product in products"
          :key="product.id"
          class="product-item"
          @click="goToDetail(product.id)"
        >
          <el-image :src="product.mainImage" fit="cover">
            <template #error>
              <div class="image-placeholder">
                <el-icon :size="60"><Picture /></el-icon>
              </div>
            </template>
          </el-image>
          <div class="product-info">
            <h3>{{ product.productName }}</h3>
            <p class="price">¥{{ product.price }}</p>
            <p class="sales">已售 {{ product.sales || 0 }} 件</p>
          </div>
        </div>
      </div>

      <el-pagination
        v-model:current-page="pagination.pageNum"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        layout="prev, pager, next"
        @current-change="fetchProducts"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, Picture } from '@element-plus/icons-vue'
import { getProductList, getCategories } from '@/api/product'

const router = useRouter()
const route = useRoute()

const products = ref([])
const categories = ref([])
const searchForm = reactive({
  keyword: '',
  categoryId: null
})

const pagination = reactive({
  pageNum: 1,
  pageSize: 12,
  total: 0
})

onMounted(() => {
  if (route.query.keyword) {
    searchForm.keyword = route.query.keyword
  }
  fetchCategories()
  fetchProducts()
})

const fetchCategories = async () => {
  try {
    const res = await getCategories()
    categories.value = res.data || []
  } catch (error) {
    console.error('获取分类失败:', error)
  }
}

const fetchProducts = async () => {
  try {
    const res = await getProductList({
      ...searchForm,
      pageNum: pagination.pageNum,
      pageSize: pagination.pageSize
    })
    products.value = res.data?.records || []
    pagination.total = res.data?.total || 0
  } catch (error) {
    console.error('获取商品失败:', error)
  }
}

const handleSearch = () => {
  pagination.pageNum = 1
  fetchProducts()
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
  margin: 20px 0;
  display: flex;
  gap: 20px;
}

.product-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
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

.image-placeholder {
  width: 100%;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  color: #ccc;
}

.product-info {
  padding: 15px;
}

.product-info h3 {
  font-size: 16px;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.price {
  font-size: 18px;
  color: #F56C6C;
  font-weight: bold;
  margin-bottom: 5px;
}

.sales {
  font-size: 12px;
  color: #999;
}
</style>
