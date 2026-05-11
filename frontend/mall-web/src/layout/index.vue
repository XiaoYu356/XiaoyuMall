<template>
  <div class="layout">
    <header class="header">
      <div class="container">
        <div class="logo" @click="$router.push('/')">
          <el-icon :size="32" color="#409EFF"><Shop /></el-icon>
          <span class="logo-text">智能百货</span>
        </div>
        
        <div class="search-bar">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索商品..."
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </div>
        
        <div class="nav-actions">
          <el-button :icon="MagicStick" @click="$router.push('/ai-assistant')">AI助手</el-button>
          <el-button :icon="Ticket" @click="$router.push('/coupons')">领券中心</el-button>

          <el-badge :value="cartCount" :hidden="cartCount === 0" class="nav-item">
            <el-button :icon="ShoppingCart" @click="$router.push('/cart')">购物车</el-button>
          </el-badge>
          
          <el-badge :value="orderCount" :hidden="orderCount === 0" class="nav-item">
            <el-button :icon="Document" @click="$router.push('/orders')">订单</el-button>
          </el-badge>
          
          <el-dropdown v-if="isLoggedIn" @command="handleCommand">
            <el-button :icon="User">
              {{ userInfo.nickname || '用户' }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="user">个人中心</el-dropdown-item>
                <el-dropdown-item command="orders">我的订单</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <el-button v-else type="primary" @click="$router.push('/login')">
            登录/注册
          </el-button>
        </div>
      </div>
    </header>
    
    <main class="main">
      <router-view />
    </main>
    
    <footer class="footer">
      <div class="container">
        <p>© 2026 智能百货平台 - 您的购物首选</p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, ShoppingCart, Document, User, ArrowDown, Shop, Ticket, MagicStick } from '@element-plus/icons-vue'
import { getCartList } from '@/api/cart'
import { getOrderList } from '@/api/order'

const router = useRouter()

const searchKeyword = ref('')
const cartCount = ref(0)
const orderCount = ref(0)

const isLoggedIn = computed(() => !!localStorage.getItem('token'))
const userInfo = ref({})

const loadUserInfo = () => {
  const savedUserInfo = localStorage.getItem('userInfo')
  if (savedUserInfo) {
    userInfo.value = JSON.parse(savedUserInfo)
  }
}

const fetchCartCount = async () => {
  if (!isLoggedIn.value) return
  
  try {
    const res = await getCartList()
    const cartItems = res.data || []
    cartCount.value = cartItems.reduce((sum, item) => sum + item.quantity, 0)
  } catch (error) {
    console.error('获取购物车数量失败:', error)
  }
}

const fetchOrderCount = async () => {
  if (!isLoggedIn.value) return
  
  try {
    const res = await getOrderList({ status: 1 })
    orderCount.value = res.data?.total || 0
  } catch (error) {
    console.error('获取订单数量失败:', error)
  }
}

const handleSearch = () => {
  if (searchKeyword.value) {
    router.push({ path: '/products', query: { keyword: searchKeyword.value } })
  }
}

const handleCommand = (command) => {
  if (command === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    ElMessage.success('退出成功')
    router.push('/')
  } else {
    router.push(`/${command}`)
  }
}

onMounted(() => {
  loadUserInfo()
  fetchCartCount()
  fetchOrderCount()
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header .container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 15px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.logo-text {
  font-size: 24px;
  font-weight: bold;
  margin-left: 10px;
  color: #409EFF;
}

.search-bar {
  flex: 1;
  max-width: 500px;
  margin: 0 40px;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.nav-item {
  cursor: pointer;
}

.main {
  flex: 1;
  background: #f5f5f5;
}

.footer {
  background: #333;
  color: white;
  padding: 20px;
  text-align: center;
}

.footer p {
  margin: 0;
}
</style>
