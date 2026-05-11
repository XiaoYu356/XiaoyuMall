<template>
  <div class="user-page">
    <div class="container">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="user-card">
            <div class="avatar-section">
              <el-avatar :size="80" :src="userStore.userInfo?.avatar">
                <el-icon :size="40"><User /></el-icon>
              </el-avatar>
              <h3>{{ userStore.userInfo?.nickname || '用户' }}</h3>
              <p>会员等级：Lv.{{ userStore.userInfo?.level || 1 }}</p>
            </div>

            <el-menu :default-active="activeMenu" @select="handleMenuSelect">
              <el-menu-item index="info">
                <el-icon><User /></el-icon>
                <span>个人信息</span>
              </el-menu-item>
              <el-menu-item index="address">
                <el-icon><Location /></el-icon>
                <span>收货地址</span>
              </el-menu-item>
              <el-menu-item index="coupon">
                <el-icon><Ticket /></el-icon>
                <span>我的优惠券</span>
              </el-menu-item>
            </el-menu>

            <div style="padding: 20px">
              <el-button type="danger" style="width: 100%" @click="handleLogout">退出登录</el-button>
            </div>
          </el-card>
        </el-col>

        <el-col :span="18">
          <el-card>
            <template #header>
              <span>{{ menuTitle }}</span>
            </template>

            <div v-if="activeMenu === 'info'" class="info-section">
              <el-form :model="editForm" label-width="100px">
                <el-form-item label="用户名">
                  <el-input v-model="editForm.username" disabled />
                </el-form-item>
                <el-form-item label="昵称">
                  <el-input v-model="editForm.nickname" />
                </el-form-item>
                <el-form-item label="手机号">
                  <el-input v-model="editForm.phone" />
                </el-form-item>
                <el-form-item label="邮箱">
                  <el-input v-model="editForm.email" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="updateInfo">保存修改</el-button>
                </el-form-item>
              </el-form>
            </div>

            <div v-else-if="activeMenu === 'address'" class="address-section">
              <el-button type="primary" style="margin-bottom: 20px" @click="showAddressDialog = true">添加地址</el-button>

              <el-empty v-if="addresses.length === 0" description="暂无收货地址" />

              <div v-else class="address-list">
                <div v-for="addr in addresses" :key="addr.id" class="address-item">
                  <div class="address-info">
                    <div class="name-phone">
                      <span class="name">{{ addr.receiverName }}</span>
                      <span class="phone">{{ addr.receiverPhone }}</span>
                      <el-tag v-if="addr.isDefault === 1" type="success" size="small">默认</el-tag>
                    </div>
                    <div class="detail">{{ addr.province }}{{ addr.city }}{{ addr.district }}{{ addr.detailAddress }}</div>
                  </div>
                  <div class="address-actions">
                    <el-button v-if="addr.isDefault !== 1" type="primary" text size="small" @click="setDefault(addr.id)">设为默认</el-button>
                    <el-button type="danger" text size="small" @click="deleteAddress(addr.id)">删除</el-button>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeMenu === 'coupon'" class="coupon-section">
              <div class="coupon-tabs">
                <el-radio-group v-model="couponStatus" @change="fetchMyCoupons" size="small">
                  <el-radio-button :value="null">全部</el-radio-button>
                  <el-radio-button :value="0">未使用</el-radio-button>
                  <el-radio-button :value="1">已使用</el-radio-button>
                  <el-radio-button :value="2">已过期</el-radio-button>
                </el-radio-group>
                <el-button type="primary" text @click="$router.push('/coupons')">去领券</el-button>
              </div>

              <el-empty v-if="myCoupons.length === 0" description="暂无优惠券" />

              <div v-else class="my-coupon-list">
                <div v-for="coupon in myCoupons" :key="coupon.id" class="my-coupon-item" :class="{ disabled: coupon.status !== 0 }">
                  <div class="coupon-left" :class="getCouponColor(coupon)">
                    <div class="coupon-value">
                      <template v-if="coupon.couponType === 2">
                        <span class="number">{{ coupon.couponValue }}</span>
                        <span class="unit">折</span>
                      </template>
                      <template v-else>
                        <span class="symbol">¥</span>
                        <span class="number">{{ coupon.couponValue }}</span>
                      </template>
                    </div>
                    <div class="coupon-condition">满{{ coupon.minAmount }}可用</div>
                  </div>
                  <div class="coupon-right">
                    <div class="coupon-name">{{ coupon.templateName }}</div>
                    <div class="coupon-time">有效期至 {{ formatDate(coupon.expireTime) }}</div>
                    <div class="coupon-status">
                      <el-tag v-if="coupon.status === 0" type="success" size="small">可使用</el-tag>
                      <el-tag v-else-if="coupon.status === 1" type="info" size="small">已使用</el-tag>
                      <el-tag v-else-if="coupon.status === 2" type="danger" size="small">已过期</el-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <el-dialog v-model="showAddressDialog" title="添加地址" width="500px">
      <el-form :model="addressForm" :rules="addressRules" ref="addressFormRef" label-width="80px">
        <el-form-item label="收货人" prop="receiverName">
          <el-input v-model="addressForm.receiverName" placeholder="请输入收货人姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="receiverPhone">
          <el-input v-model="addressForm.receiverPhone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="省份" prop="province">
          <el-input v-model="addressForm.province" placeholder="请输入省份" />
        </el-form-item>
        <el-form-item label="城市" prop="city">
          <el-input v-model="addressForm.city" placeholder="请输入城市" />
        </el-form-item>
        <el-form-item label="区县" prop="district">
          <el-input v-model="addressForm.district" placeholder="请输入区县" />
        </el-form-item>
        <el-form-item label="详细地址" prop="detailAddress">
          <el-input v-model="addressForm.detailAddress" placeholder="请输入详细地址" />
        </el-form-item>
        <el-form-item label="默认地址">
          <el-switch v-model="addressForm.isDefault" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddressDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAddress">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Location, Ticket } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { updateUserInfo, getAddressList, addAddress, deleteAddress as deleteAddressApi, setDefaultAddress as setDefaultAddressApi } from '@/api/user'
import { getMyCoupons } from '@/api/coupon'

const router = useRouter()
const userStore = useUserStore()

const activeMenu = ref('info')
const addresses = ref([])
const showAddressDialog = ref(false)
const addressFormRef = ref(null)

const myCoupons = ref([])
const couponStatus = ref(null)

const editForm = reactive({
  username: '',
  nickname: '',
  phone: '',
  email: ''
})

const addressForm = ref({
  receiverName: '',
  receiverPhone: '',
  province: '',
  city: '',
  district: '',
  detailAddress: '',
  isDefault: 0
})

const addressRules = {
  receiverName: [{ required: true, message: '请输入收货人姓名', trigger: 'blur' }],
  receiverPhone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  province: [{ required: true, message: '请输入省份', trigger: 'blur' }],
  city: [{ required: true, message: '请输入城市', trigger: 'blur' }],
  detailAddress: [{ required: true, message: '请输入详细地址', trigger: 'blur' }]
}

const menuTitle = computed(() => {
  const titles = { info: '个人信息', address: '收货地址', coupon: '我的优惠券' }
  return titles[activeMenu.value]
})

watch(() => userStore.userInfo, (info) => {
  if (info) {
    editForm.username = info.username || ''
    editForm.nickname = info.nickname || ''
    editForm.phone = info.phone || ''
    editForm.email = info.email || ''
  }
}, { immediate: true })

const handleMenuSelect = (index) => {
  activeMenu.value = index
  if (index === 'address') {
    fetchAddresses()
  }
  if (index === 'coupon') {
    fetchMyCoupons()
  }
}

const fetchMyCoupons = async () => {
  try {
    const params = { pageSize: 100 }
    if (couponStatus.value !== null) {
      params.status = couponStatus.value
    }
    const res = await getMyCoupons(params)
    myCoupons.value = res.data?.records || []
  } catch (error) {
    console.error('获取优惠券失败:', error)
  }
}

const getCouponColor = (coupon) => {
  if (coupon.status !== 0) return 'gray'
  const map = { 1: 'blue', 2: 'orange', 3: 'red' }
  return map[coupon.couponType] || 'blue'
}

const formatDate = (time) => {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const handleLogout = () => {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

const updateInfo = async () => {
  try {
    await updateUserInfo({
      id: userStore.userInfo.id,
      nickname: editForm.nickname,
      phone: editForm.phone,
      email: editForm.email
    })
    await userStore.fetchUserInfo()
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('更新用户信息失败:', error)
  }
}

const fetchAddresses = async () => {
  try {
    const res = await getAddressList()
    addresses.value = res.data || []
  } catch (error) {
    console.error('获取地址失败:', error)
  }
}

const saveAddress = async () => {
  if (!addressFormRef.value) return

  await addressFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      const res = await addAddress(addressForm.value)
      addresses.value.push(res.data)
      showAddressDialog.value = false

      addressForm.value = {
        receiverName: '',
        receiverPhone: '',
        province: '',
        city: '',
        district: '',
        detailAddress: '',
        isDefault: 0
      }

      ElMessage.success('地址添加成功')
    } catch (error) {
      console.error('添加地址失败:', error)
    }
  })
}

const setDefault = async (addressId) => {
  try {
    await setDefaultAddressApi(addressId)
    await fetchAddresses()
    ElMessage.success('已设为默认地址')
  } catch (error) {
    console.error('设置默认地址失败:', error)
  }
}

const deleteAddress = async (addressId) => {
  try {
    await ElMessageBox.confirm('确定要删除该地址吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteAddressApi(addressId)
    addresses.value = addresses.value.filter(addr => addr.id !== addressId)
    ElMessage.success('地址已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除地址失败:', error)
    }
  }
}

onMounted(() => {
  if (!userStore.userInfo) {
    userStore.fetchUserInfo()
  }
})
</script>

<style scoped>
.user-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.user-card {
  text-align: center;
}

.avatar-section {
  padding: 20px 0;
  border-bottom: 1px solid #eee;
  margin-bottom: 20px;
}

.avatar-section h3 {
  margin: 15px 0 10px;
}

.avatar-section p {
  color: #999;
  font-size: 14px;
}

.info-section,
.address-section,
.coupon-section {
  padding: 20px 0;
}

.address-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.address-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 8px;
}

.address-info .name-phone {
  margin-bottom: 5px;
}

.address-info .name {
  font-weight: bold;
  margin-right: 15px;
}

.address-info .phone {
  color: #666;
  margin-right: 10px;
}

.address-info .detail {
  color: #999;
  font-size: 14px;
}

.address-actions {
  display: flex;
  gap: 5px;
}

.coupon-tabs {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.my-coupon-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.my-coupon-item {
  display: flex;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #eee;
  transition: all 0.3s;
}

.my-coupon-item.disabled {
  opacity: 0.6;
}

.my-coupon-item .coupon-left {
  width: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  padding: 15px;
}

.my-coupon-item .coupon-left.blue {
  background: linear-gradient(135deg, #409EFF, #337ecc);
}

.my-coupon-item .coupon-left.orange {
  background: linear-gradient(135deg, #E6A23C, #cf8e24);
}

.my-coupon-item .coupon-left.red {
  background: linear-gradient(135deg, #F56C6C, #dd4a4a);
}

.my-coupon-item .coupon-left.gray {
  background: #c0c4cc;
}

.my-coupon-item .coupon-value {
  display: flex;
  align-items: baseline;
  margin-bottom: 4px;
}

.my-coupon-item .coupon-value .symbol {
  font-size: 14px;
}

.my-coupon-item .coupon-value .number {
  font-size: 28px;
  font-weight: bold;
  line-height: 1;
}

.my-coupon-item .coupon-value .unit {
  font-size: 14px;
  margin-left: 2px;
}

.my-coupon-item .coupon-condition {
  font-size: 12px;
  opacity: 0.9;
}

.my-coupon-item .coupon-right {
  flex: 1;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
}

.my-coupon-item .coupon-name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.my-coupon-item .coupon-time {
  font-size: 12px;
  color: #999;
}

.my-coupon-item .coupon-status {
  margin-top: 2px;
}
</style>
