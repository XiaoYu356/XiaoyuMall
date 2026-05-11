<template>
  <div class="cart-page">
    <div class="container">
      <h2>购物车</h2>

      <el-empty v-if="!userStore.isLoggedIn" description="请先登录">
        <el-button type="primary" @click="$router.push('/login')">去登录</el-button>
      </el-empty>

      <el-empty v-else-if="cartItems.length === 0" description="购物车是空的">
        <el-button type="primary" @click="$router.push('/products')">去购物</el-button>
      </el-empty>

      <div v-else class="cart-content">
        <div class="cart-header">
          <el-checkbox v-model="selectAllFlag" @change="handleSelectAll">全选</el-checkbox>
        </div>

        <div class="cart-items">
          <div v-for="item in cartItems" :key="item.id" class="cart-item">
            <el-checkbox v-model="item.selected" :true-label="1" :false-label="0" @change="handleUpdateCart(item)" />
            <el-image :src="item.productImage" fit="cover" class="item-image">
              <template #error>
                <div class="image-placeholder"><el-icon :size="40"><Picture /></el-icon></div>
              </template>
            </el-image>
            <div class="item-info">
              <h3>{{ item.productName }}</h3>
              <p v-if="item.skuName" class="sku-name">{{ item.skuName }}</p>
              <p class="item-price">¥{{ item.price }}</p>
            </div>
            <el-input-number
              v-model="item.quantity"
              :min="1"
              :max="99"
              @change="handleQuantityChange(item)"
            />
            <span class="item-total">¥{{ (item.price * item.quantity).toFixed(2) }}</span>
            <el-button type="danger" text @click="removeItem(item.id)">删除</el-button>
          </div>
        </div>

        <div class="cart-footer">
          <div class="total-info">
            <span>已选 {{ selectedCount }} 件</span>
            <span class="total-price">合计：¥{{ totalPrice.toFixed(2) }}</span>
          </div>
          <div class="footer-actions">
            <el-button @click="clearCart">清空购物车</el-button>
            <el-button type="danger" size="large" @click="checkout" :disabled="selectedCount === 0">去结算</el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import * as cartApi from '@/api/cart'

const router = useRouter()
const userStore = useUserStore()

const cartItems = ref([])
const loading = ref(false)

const selectAllFlag = computed({
  get: () => cartItems.value.length > 0 && cartItems.value.every(item => item.selected === 1),
  set: () => {}
})

const selectedCount = computed(() => {
  return cartItems.value.filter(item => item.selected === 1).reduce((sum, item) => sum + item.quantity, 0)
})

const totalPrice = computed(() => {
  return cartItems.value
    .filter(item => item.selected === 1)
    .reduce((sum, item) => sum + Number(item.price) * item.quantity, 0)
})

const fetchCartList = async () => {
  if (!userStore.isLoggedIn) return

  loading.value = true
  try {
    const res = await cartApi.getCartList()
    cartItems.value = res.data || []
  } catch (error) {
    console.error('获取购物车失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSelectAll = async (val) => {
  try {
    await cartApi.selectAll(val ? 1 : 0)
    cartItems.value.forEach(item => {
      item.selected = val ? 1 : 0
    })
  } catch (error) {
    console.error('全选操作失败:', error)
  }
}

const handleUpdateCart = async (item) => {
  try {
    await cartApi.updateCart({
      id: item.id,
      selected: item.selected
    })
  } catch (error) {
    console.error('更新购物车失败:', error)
    fetchCartList()
  }
}

const handleQuantityChange = async (item) => {
  try {
    await cartApi.updateCart({
      id: item.id,
      quantity: item.quantity
    })
  } catch (error) {
    console.error('更新数量失败:', error)
    fetchCartList()
  }
}

const removeItem = async (cartId) => {
  try {
    await ElMessageBox.confirm('确定要删除该商品吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await cartApi.deleteCart(cartId)
    cartItems.value = cartItems.value.filter(item => item.id !== cartId)
    ElMessage.success('已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const clearCart = async () => {
  try {
    await ElMessageBox.confirm('确定要清空购物车吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await cartApi.clearCart()
    cartItems.value = []
    ElMessage.success('购物车已清空')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空购物车失败:', error)
    }
  }
}

const checkout = () => {
  const selectedItems = cartItems.value.filter(item => item.selected === 1)
  if (selectedItems.length === 0) {
    ElMessage.warning('请选择要结算的商品')
    return
  }

  localStorage.setItem('checkoutItems', JSON.stringify(selectedItems))
  router.push('/checkout')
}

onMounted(() => {
  fetchCartList()
})
</script>

<style scoped>
.cart-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.cart-content {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.cart-header {
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.cart-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 0;
  border-bottom: 1px solid #eee;
}

.item-image {
  width: 100px;
  height: 100px;
  border-radius: 8px;
}

.image-placeholder {
  width: 100px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  color: #ccc;
}

.item-info {
  flex: 1;
}

.item-info h3 {
  margin-bottom: 10px;
}

.sku-name {
  color: #999;
  font-size: 14px;
  margin-bottom: 5px;
}

.item-price {
  color: #F56C6C;
  font-size: 18px;
  font-weight: bold;
}

.item-total {
  font-size: 18px;
  color: #F56C6C;
  font-weight: bold;
  min-width: 100px;
  text-align: right;
}

.cart-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 2px solid #eee;
}

.total-info {
  display: flex;
  gap: 20px;
  align-items: center;
}

.total-price {
  font-size: 24px;
  color: #F56C6C;
  font-weight: bold;
}

.footer-actions {
  display: flex;
  gap: 10px;
}
</style>
