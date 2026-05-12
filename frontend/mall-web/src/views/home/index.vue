<template>
  <div class="home-page">
    <div class="banner">
      <el-carousel height="400px">
        <el-carousel-item v-for="item in banners" :key="item.id">
          <div class="banner-item" :style="{ background: item.color }">
            <h2>{{ item.title }}</h2>
            <p>{{ item.desc }}</p>
          </div>
        </el-carousel-item>
      </el-carousel>
    </div>
    
    <div class="container">
      <section class="section category-section">
        <div class="section-header">
          <h2>📂 商品分类</h2>
        </div>
        <div class="category-grid">
          <div
            v-for="category in categoryTree.slice(0, 8)"
            :key="category.id"
            class="category-card"
            @click="goToCategory(category.id)"
          >
            <div class="category-icon">
              <el-icon :size="32"><component :is="category.icon || 'Goods'" /></el-icon>
            </div>
            <span class="category-name">{{ category.categoryName }}</span>
            <div v-if="category.children && category.children.length" class="category-children">
              <span
                v-for="child in category.children.slice(0, 4)"
                :key="child.id"
                class="category-child"
                @click.stop="goToCategory(child.id)"
              >{{ child.categoryName }}</span>
              <span v-if="category.children.length > 4" class="category-more">更多...</span>
            </div>
          </div>
        </div>
      </section>

      <section class="section coupon-section">
        <div class="section-header">
          <h2>🎟️ 限时抢券</h2>
          <el-button text @click="$router.push('/coupons')">更多优惠 ></el-button>
        </div>
        <div class="coupon-banner" @click="$router.push('/coupons')">
          <div class="coupon-banner-item">
            <div class="coupon-icon">💰</div>
            <div class="coupon-text">
              <h3>满减券</h3>
              <p>满额立减，省上加省</p>
            </div>
          </div>
          <div class="coupon-banner-item">
            <div class="coupon-icon">🏷️</div>
            <div class="coupon-text">
              <h3>折扣券</h3>
              <p>限时折扣，抢到就是赚到</p>
            </div>
          </div>
          <div class="coupon-banner-item">
            <div class="coupon-icon">🎁</div>
            <div class="coupon-text">
              <h3>现金券</h3>
              <p>无门槛抵扣，直接当钱花</p>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2>🔥 热门推荐</h2>
          <el-button text @click="$router.push('/products')">查看更多 ></el-button>
        </div>
        
        <div class="product-grid">
          <div
            v-for="product in hotProducts"
            :key="product.id"
            class="product-card"
            @click="goToDetail(product.id)"
          >
            <div class="product-image">
              <el-image :src="product.mainImage" fit="cover">
                <template #error>
                  <div class="image-placeholder">
                    <el-icon :size="60"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
            <div class="product-info">
              <h3 class="product-name">{{ product.productName }}</h3>
              <p class="product-desc">{{ product.description }}</p>
              <div class="product-price">
                <span class="current-price">¥{{ product.price }}</span>
                <span v-if="product.originalPrice" class="original-price">
                  ¥{{ product.originalPrice }}
                </span>
              </div>
              <div class="product-sales">已售 {{ product.sales || 0 }} 件</div>
            </div>
          </div>
        </div>
      </section>
      
      <section class="section">
        <div class="section-header">
          <h2>🎁 新品上架</h2>
        </div>
        
        <div class="product-grid">
          <div
            v-for="product in newProducts"
            :key="product.id"
            class="product-card"
            @click="goToDetail(product.id)"
          >
            <div class="product-image">
              <el-tag class="new-tag" type="danger">新品</el-tag>
              <el-image :src="product.mainImage" fit="cover">
                <template #error>
                  <div class="image-placeholder">
                    <el-icon :size="60"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
            <div class="product-info">
              <h3 class="product-name">{{ product.productName }}</h3>
              <div class="product-price">
                <span class="current-price">¥{{ product.price }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Picture, Goods } from '@element-plus/icons-vue'
import { getProductList, getCategories } from '@/api/product'

const router = useRouter()

const banners = ref([
  { id: 1, title: '智能百货，品质生活', desc: '精选好物，品质保证', color: '#409EFF' },
  { id: 2, title: '新品上市，限时优惠', desc: '新品首发，立享8折', color: '#67C23A' },
  { id: 3, title: '会员专享，更多福利', desc: '注册会员，享受专属优惠', color: '#E6A23C' }
])

const categoryList = ref([])
const hotProducts = ref([])
const newProducts = ref([])

const categoryTree = computed(() => {
  const list = categoryList.value
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

onMounted(async () => {
  try {
    const [productRes, categoryRes] = await Promise.all([
      getProductList({ pageNum: 1, pageSize: 8 }),
      getCategories()
    ])
    hotProducts.value = productRes.data?.records || []
    newProducts.value = hotProducts.value.slice(0, 4)
    categoryList.value = categoryRes.data || []
  } catch (error) {
    console.error('获取数据失败:', error)
  }
})

const goToDetail = (id) => {
  router.push(`/product/${id}`)
}

const goToCategory = (categoryId) => {
  router.push(`/products?categoryId=${categoryId}`)
}
</script>

<style scoped>
.home-page {
  padding-bottom: 40px;
}

.banner-item {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
}

.banner-item h2 {
  font-size: 48px;
  margin-bottom: 20px;
}

.banner-item p {
  font-size: 24px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.section {
  margin-top: 40px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  font-size: 24px;
  color: #333;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 16px;
}

.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 10px;
  background: white;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.category-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.category-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409EFF, #66b1ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 10px;
}

.category-card:nth-child(2) .category-icon {
  background: linear-gradient(135deg, #67C23A, #85ce61);
}

.category-card:nth-child(3) .category-icon {
  background: linear-gradient(135deg, #E6A23C, #ebb563);
}

.category-card:nth-child(4) .category-icon {
  background: linear-gradient(135deg, #F56C6C, #f78989);
}

.category-card:nth-child(5) .category-icon {
  background: linear-gradient(135deg, #909399, #a6a9ad);
}

.category-card:nth-child(6) .category-icon {
  background: linear-gradient(135deg, #9b59b6, #b07cc6);
}

.category-card:nth-child(7) .category-icon {
  background: linear-gradient(135deg, #3498db, #5dade2);
}

.category-card:nth-child(8) .category-icon {
  background: linear-gradient(135deg, #1abc9c, #48c9b0);
}

.category-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.category-children {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
  justify-content: center;
}

.category-child {
  font-size: 12px;
  color: #666;
  padding: 2px 8px;
  border-radius: 10px;
  background: #f5f7fa;
  cursor: pointer;
  transition: all 0.2s;
}

.category-child:hover {
  background: #409EFF;
  color: white;
}

.category-more {
  font-size: 12px;
  color: #409EFF;
  padding: 2px 8px;
  cursor: pointer;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.product-card {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
}

.product-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.product-image {
  position: relative;
  width: 100%;
  height: 200px;
  background: #f5f5f5;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
}

.new-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1;
}

.product-info {
  padding: 15px;
}

.product-name {
  font-size: 16px;
  color: #333;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-desc {
  font-size: 14px;
  color: #999;
  margin-bottom: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-price {
  margin-bottom: 5px;
}

.current-price {
  font-size: 20px;
  color: #F56C6C;
  font-weight: bold;
}

.original-price {
  font-size: 14px;
  color: #999;
  text-decoration: line-through;
  margin-left: 10px;
}

.product-sales {
  font-size: 12px;
  color: #999;
}

.coupon-banner {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  cursor: pointer;
}

.coupon-banner-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: linear-gradient(135deg, #fff5f5, #fff0f0);
  border-radius: 12px;
  border: 1px solid #ffe0e0;
  transition: all 0.3s;
}

.coupon-banner-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
}

.coupon-banner-item:nth-child(2) {
  background: linear-gradient(135deg, #fff8e6, #fff3d6);
  border-color: #ffe0a0;
}

.coupon-banner-item:nth-child(2):hover {
  box-shadow: 0 4px 12px rgba(230, 162, 60, 0.2);
}

.coupon-banner-item:nth-child(3) {
  background: linear-gradient(135deg, #f0f9ff, #e6f4ff);
  border-color: #b3d8ff;
}

.coupon-banner-item:nth-child(3):hover {
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.coupon-icon {
  font-size: 40px;
}

.coupon-text h3 {
  font-size: 18px;
  color: #333;
  margin-bottom: 4px;
}

.coupon-text p {
  font-size: 13px;
  color: #999;
}

@media (max-width: 1024px) {
  .product-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .category-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 768px) {
  .product-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .category-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  .coupon-banner {
    grid-template-columns: 1fr;
  }
}
</style>
