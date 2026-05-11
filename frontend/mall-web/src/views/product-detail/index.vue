<template>
  <div class="product-detail-page">
    <div class="container">
      <el-skeleton v-if="loading" :rows="10" animated />

      <div v-else class="detail-content">
        <div class="product-gallery">
          <el-image :src="product.mainImage" fit="contain">
            <template #error>
              <div class="image-placeholder">
                <el-icon :size="100"><Picture /></el-icon>
              </div>
            </template>
          </el-image>
        </div>

        <div class="product-info">
          <h1 class="product-name">{{ product.productName }}</h1>
          <p class="product-desc">{{ product.description }}</p>

          <div class="price-section">
            <span class="label">价格：</span>
            <span class="price">¥{{ currentPrice }}</span>
            <span v-if="product.originalPrice" class="original-price">
              ¥{{ product.originalPrice }}
            </span>
          </div>

          <div class="sales-section">
            <span class="label">销量：</span>
            <span>{{ product.sales || 0 }} 件</span>
          </div>

          <div v-if="skuList.length > 0" class="sku-section">
            <span class="label">规格：</span>
            <div class="sku-options">
              <div
                v-for="sku in skuList"
                :key="sku.id"
                class="sku-item"
                :class="{ active: selectedSku?.id === sku.id, disabled: sku.stock <= 0 }"
                @click="selectSku(sku)"
              >
                {{ sku.skuName }}
                <span v-if="sku.stock <= 0" class="out-of-stock">缺货</span>
              </div>
            </div>
          </div>

          <div v-if="selectedSku" class="stock-section">
            <span class="label">库存：</span>
            <span>{{ selectedSku.stock }} 件</span>
          </div>

          <div class="quantity-section">
            <span class="label">数量：</span>
            <el-input-number v-model="quantity" :min="1" :max="maxQuantity" />
          </div>

          <div class="action-buttons">
            <el-button type="primary" size="large" @click="addToCart" :loading="addingToCart" :disabled="!canBuy">
              <el-icon><ShoppingCart /></el-icon>
              加入购物车
            </el-button>
            <el-button type="danger" size="large" @click="buyNow" :disabled="!canBuy">
              立即购买
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Picture, ShoppingCart } from '@element-plus/icons-vue'
import { getProductById, getProductSkus } from '@/api/product'
import { addCart } from '@/api/cart'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const product = ref({})
const skuList = ref([])
const selectedSku = ref(null)
const quantity = ref(1)
const addingToCart = ref(false)

const currentPrice = computed(() => {
  return selectedSku.value?.price || product.value.price || 0
})

const maxQuantity = computed(() => {
  if (!selectedSku.value) return 99
  return Math.min(selectedSku.value.stock, 99)
})

const canBuy = computed(() => {
  return selectedSku.value && selectedSku.value.stock > 0
})

onMounted(async () => {
  const id = route.params.id
  try {
    const [productRes, skuRes] = await Promise.all([
      getProductById(id),
      getProductSkus(id)
    ])
    product.value = productRes.data || {}
    skuList.value = skuRes.data || []

    if (skuList.value.length > 0) {
      const availableSku = skuList.value.find(s => s.stock > 0)
      if (availableSku) {
        selectSku(availableSku)
      }
    }
  } catch (error) {
    console.error('获取商品详情失败:', error)
  } finally {
    loading.value = false
  }
})

const selectSku = (sku) => {
  if (sku.stock <= 0) return
  selectedSku.value = sku
  if (quantity.value > sku.stock) {
    quantity.value = sku.stock
  }
}

const addToCart = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  if (!selectedSku.value) {
    ElMessage.warning('请选择商品规格')
    return
  }

  addingToCart.value = true
  try {
    await addCart({
      productId: product.value.id,
      skuId: selectedSku.value.id,
      productName: product.value.productName,
      skuName: selectedSku.value.skuName,
      price: selectedSku.value.price,
      quantity: quantity.value,
      productImage: product.value.mainImage
    })
    ElMessage.success('已加入购物车')
  } catch (error) {
    console.error('加入购物车失败:', error)
    ElMessage.error('加入购物车失败')
  } finally {
    addingToCart.value = false
  }
}

const buyNow = async () => {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  await addToCart()
  if (selectedSku.value) {
    router.push('/cart')
  }
}
</script>

<style scoped>
.product-detail-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.detail-content {
  display: flex;
  gap: 40px;
  background: white;
  padding: 30px;
  border-radius: 8px;
}

.product-gallery {
  flex: 0 0 400px;
  height: 400px;
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
}

.product-info {
  flex: 1;
}

.product-name {
  font-size: 24px;
  margin-bottom: 20px;
}

.product-desc {
  color: #999;
  margin-bottom: 20px;
}

.price-section,
.sales-section,
.stock-section,
.quantity-section {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.label {
  width: 60px;
  color: #999;
  flex-shrink: 0;
}

.price {
  font-size: 28px;
  color: #F56C6C;
  font-weight: bold;
}

.original-price {
  font-size: 16px;
  color: #999;
  text-decoration: line-through;
  margin-left: 10px;
}

.sku-section {
  margin-bottom: 20px;
  display: flex;
  align-items: flex-start;
}

.sku-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.sku-item {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 14px;
  position: relative;
}

.sku-item:hover {
  border-color: #409EFF;
}

.sku-item.active {
  border-color: #409EFF;
  color: #409EFF;
  background: #ecf5ff;
}

.sku-item.disabled {
  background: #f5f5f5;
  color: #ccc;
  cursor: not-allowed;
  border-color: #eee;
}

.out-of-stock {
  font-size: 12px;
  color: #F56C6C;
  margin-left: 4px;
}

.action-buttons {
  margin-top: 30px;
  display: flex;
  gap: 20px;
}
</style>
