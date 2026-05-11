<template>
  <div class="checkout-page">
    <div class="container">
      <h2>确认订单</h2>

      <div class="checkout-content">
        <div class="main-content">
          <el-card class="address-card">
            <template #header>
              <div class="card-header">
                <span>收货地址</span>
                <el-button type="primary" text @click="showAddressDialog = true">新增地址</el-button>
              </div>
            </template>

            <div v-if="addresses.length === 0" class="empty-address">
              <el-empty description="暂无收货地址" :image-size="100" />
            </div>

            <div v-else class="address-list">
              <div
                v-for="addr in addresses"
                :key="addr.id"
                class="address-item"
                :class="{ active: selectedAddress?.id === addr.id }"
                @click="selectedAddress = addr"
              >
                <div class="address-info">
                  <div class="name-phone">
                    <span class="name">{{ addr.receiverName }}</span>
                    <span class="phone">{{ addr.receiverPhone }}</span>
                    <el-tag v-if="addr.isDefault === 1" type="success" size="small">默认</el-tag>
                  </div>
                  <div class="detail">{{ addr.province }}{{ addr.city }}{{ addr.district }}{{ addr.detailAddress }}</div>
                </div>
                <el-icon v-if="selectedAddress?.id === addr.id" class="check-icon"><CircleCheck /></el-icon>
              </div>
            </div>
          </el-card>

          <el-card class="products-card">
            <template #header><span>商品清单</span></template>
            <div class="product-list">
              <div v-for="item in checkoutItems" :key="item.id" class="product-item">
                <el-image :src="item.productImage" fit="cover" class="product-image">
                  <template #error>
                    <div class="image-placeholder"><el-icon :size="30"><Picture /></el-icon></div>
                  </template>
                </el-image>
                <div class="product-info">
                  <h4>{{ item.productName }}</h4>
                  <p v-if="item.skuName" class="sku-name">{{ item.skuName }}</p>
                </div>
                <div class="product-price">¥{{ item.price }}</div>
                <div class="product-quantity">x{{ item.quantity }}</div>
                <div class="product-total">¥{{ (item.price * item.quantity).toFixed(2) }}</div>
              </div>
            </div>
          </el-card>

          <el-card class="coupon-card">
            <template #header>
              <div class="card-header">
                <span>优惠券</span>
                <el-button type="primary" text @click="$router.push('/coupons')">去领券</el-button>
              </div>
            </template>
            <div v-if="myCoupons.length === 0" class="no-coupon">
              <el-empty description="暂无可用优惠券" :image-size="80" />
            </div>
            <div v-else class="coupon-select">
              <div
                class="checkout-coupon"
                :class="{ active: selectedCouponId === null }"
                @click="selectCoupon(null)"
              >
                <div class="coupon-body">
                  <div class="coupon-icon-none">
                    <el-icon :size="24"><Close /></el-icon>
                  </div>
                  <div class="coupon-detail">
                    <span class="coupon-name">不使用优惠券</span>
                  </div>
                </div>
                <el-icon v-if="selectedCouponId === null" class="coupon-check"><CircleCheck /></el-icon>
              </div>
              <div
                v-for="coupon in myCoupons"
                :key="coupon.id"
                class="checkout-coupon"
                :class="{ active: selectedCouponId === coupon.id, disabled: !isCouponUsable(coupon) }"
                @click="isCouponUsable(coupon) && selectCoupon(coupon.id)"
              >
                <div class="coupon-body">
                  <div class="coupon-value-side" :class="getCouponColor(coupon)">
                    <template v-if="coupon.couponType === 2">
                      <span class="val-num">{{ coupon.couponValue }}</span>
                      <span class="val-unit">折</span>
                    </template>
                    <template v-else>
                      <span class="val-sym">¥</span>
                      <span class="val-num">{{ coupon.couponValue }}</span>
                    </template>
                  </div>
                  <div class="coupon-detail">
                    <span class="coupon-name">{{ coupon.templateName }}</span>
                    <span class="coupon-condition">满{{ coupon.minAmount }}可用</span>
                    <span v-if="!isCouponUsable(coupon)" class="coupon-unusable">未满足条件</span>
                    <span v-else-if="selectedCouponId === coupon.id" class="coupon-save">可省 ¥{{ previewDiscount(coupon) }}</span>
                  </div>
                </div>
                <el-icon v-if="selectedCouponId === coupon.id" class="coupon-check"><CircleCheck /></el-icon>
              </div>
            </div>
          </el-card>

          <el-card class="remark-card">
            <template #header><span>订单备注</span></template>
            <el-input v-model="orderRemark" type="textarea" :rows="3" placeholder="选填，可以告诉卖家您的特殊需求" />
          </el-card>
        </div>

        <div class="sidebar">
          <el-card class="summary-card">
            <template #header><span>订单汇总</span></template>
            <div class="summary-item">
              <span>商品总额</span>
              <span>¥{{ totalPrice.toFixed(2) }}</span>
            </div>
            <div class="summary-item">
              <span>运费</span>
              <span>¥{{ shippingFee.toFixed(2) }}</span>
            </div>
            <div v-if="discountAmount > 0" class="summary-item discount">
              <span>优惠券减免</span>
              <span>-¥{{ discountAmount.toFixed(2) }}</span>
            </div>
            <div class="summary-item total">
              <span>应付总额</span>
              <span class="amount">¥{{ payAmount.toFixed(2) }}</span>
            </div>
            <el-button type="danger" size="large" style="width: 100%; margin-top: 20px" @click="submitOrder" :loading="submitting">
              提交订单
            </el-button>
          </el-card>
        </div>
      </div>
    </div>

    <el-dialog v-model="showAddressDialog" title="新增地址" width="500px">
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Picture, Close } from '@element-plus/icons-vue'
import { createOrder } from '@/api/order'
import { getAddressList, addAddress } from '@/api/user'
import { getMyCoupons, calculateDiscount } from '@/api/coupon'

const router = useRouter()

const checkoutItems = ref([])
const addresses = ref([])
const selectedAddress = ref(null)
const orderRemark = ref('')
const submitting = ref(false)
const showAddressDialog = ref(false)
const addressFormRef = ref(null)

const myCoupons = ref([])
const selectedCouponId = ref(null)
const discountAmount = ref(0)

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

const totalPrice = computed(() => {
  return checkoutItems.value.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0)
})

const shippingFee = computed(() => {
  return totalPrice.value >= 99 ? 0 : 10
})

const payAmount = computed(() => {
  const amount = totalPrice.value + shippingFee.value - discountAmount.value
  return Math.max(0, amount)
})

const isCouponUsable = (coupon) => {
  return totalPrice.value >= Number(coupon.minAmount || 0)
}

const getCouponColor = (coupon) => {
  if (!isCouponUsable(coupon)) return 'gray'
  const map = { 1: 'blue', 2: 'orange', 3: 'red' }
  return map[coupon.couponType] || 'blue'
}

const previewDiscount = (coupon) => {
  if (coupon.couponType === 2) {
    return (totalPrice.value * (1 - coupon.couponValue / 10)).toFixed(2)
  }
  return Number(coupon.couponValue || 0).toFixed(2)
}

const selectCoupon = async (couponId) => {
  selectedCouponId.value = couponId
  await handleCouponChange(couponId)
}

onMounted(() => {
  const items = localStorage.getItem('checkoutItems')
  if (items) {
    checkoutItems.value = JSON.parse(items)
  } else {
    ElMessage.warning('没有要结算的商品')
    router.push('/cart')
  }

  fetchAddresses()
  fetchMyCoupons()
})

const fetchAddresses = async () => {
  try {
    const res = await getAddressList()
    addresses.value = res.data || []
    if (addresses.value.length > 0) {
      selectedAddress.value = addresses.value.find(addr => addr.isDefault === 1) || addresses.value[0]
    }
  } catch (error) {
    console.error('获取地址失败:', error)
  }
}

const fetchMyCoupons = async () => {
  try {
    const res = await getMyCoupons({ status: 0, pageSize: 100 })
    myCoupons.value = res.data?.records || []
  } catch (error) {
    console.error('获取优惠券失败:', error)
  }
}

const handleCouponChange = async (couponId) => {
  if (!couponId) {
    discountAmount.value = 0
    return
  }

  try {
    const res = await calculateDiscount(couponId, totalPrice.value)
    discountAmount.value = Number(res.data) || 0
  } catch (error) {
    console.error('计算优惠失败:', error)
    discountAmount.value = 0
  }
}

const saveAddress = async () => {
  if (!addressFormRef.value) return

  await addressFormRef.value.validate(async (valid) => {
    if (!valid) return

    try {
      const res = await addAddress(addressForm.value)
      addresses.value.push(res.data)
      selectedAddress.value = res.data
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

const submitOrder = async () => {
  if (!selectedAddress.value) {
    ElMessage.warning('请选择收货地址')
    return
  }

  if (checkoutItems.value.length === 0) {
    ElMessage.warning('没有要结算的商品')
    return
  }

  submitting.value = true
  try {
    const orderData = {
      receiverName: selectedAddress.value.receiverName,
      receiverPhone: selectedAddress.value.receiverPhone,
      receiverAddress: `${selectedAddress.value.province}${selectedAddress.value.city}${selectedAddress.value.district || ''}${selectedAddress.value.detailAddress}`,
      remark: orderRemark.value,
      couponId: selectedCouponId.value,
      items: checkoutItems.value.map(item => ({
        productId: item.productId,
        skuId: item.skuId,
        quantity: item.quantity
      }))
    }

    await createOrder(orderData)

    localStorage.removeItem('checkoutItems')
    ElMessage.success('订单创建成功')
    router.push('/orders')
  } catch (error) {
    console.error('创建订单失败:', error)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.checkout-page {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.checkout-content {
  display: flex;
  gap: 20px;
  margin-top: 20px;
}

.main-content {
  flex: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.address-card,
.products-card,
.coupon-card,
.remark-card {
  margin-bottom: 20px;
}

.empty-address {
  padding: 20px 0;
}

.address-list {
  display: grid;
  gap: 10px;
}

.address-item {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}

.address-item:hover {
  border-color: #409EFF;
}

.address-item.active {
  border-color: #409EFF;
  background: #ecf5ff;
}

.address-info .name-phone {
  margin-bottom: 8px;
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

.check-icon {
  position: absolute;
  top: 15px;
  right: 15px;
  color: #409EFF;
  font-size: 24px;
}

.product-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.product-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.product-item:last-child {
  border-bottom: none;
}

.product-image {
  width: 80px;
  height: 80px;
  border-radius: 8px;
}

.image-placeholder {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  color: #ccc;
}

.product-info {
  flex: 1;
}

.product-info h4 {
  margin-bottom: 5px;
}

.sku-name {
  color: #999;
  font-size: 12px;
}

.product-price,
.product-quantity,
.product-total {
  width: 100px;
  text-align: center;
}

.product-total {
  color: #F56C6C;
  font-weight: bold;
}

.no-coupon {
  padding: 10px 0;
}

.coupon-select {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.checkout-coupon {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 2px solid #eee;
  border-radius: 10px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.25s;
  position: relative;
}

.checkout-coupon:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.checkout-coupon.active {
  border-color: #409EFF;
  background: #f0f7ff;
}

.checkout-coupon.disabled {
  background: #fafafa;
  cursor: not-allowed;
  opacity: 0.6;
}

.checkout-coupon.disabled:hover {
  border-color: #eee;
  box-shadow: none;
}

.coupon-body {
  display: flex;
  align-items: center;
  gap: 14px;
}

.coupon-icon-none {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

.coupon-value-side {
  width: 80px;
  height: 56px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  flex-shrink: 0;
}

.coupon-value-side.blue {
  background: linear-gradient(135deg, #409EFF, #337ecc);
}

.coupon-value-side.orange {
  background: linear-gradient(135deg, #E6A23C, #cf8e24);
}

.coupon-value-side.red {
  background: linear-gradient(135deg, #F56C6C, #dd4a4a);
}

.coupon-value-side.gray {
  background: #c0c4cc;
}

.val-sym {
  font-size: 14px;
  margin-right: 1px;
}

.val-num {
  font-size: 22px;
  line-height: 1;
}

.val-unit {
  font-size: 13px;
  margin-left: 1px;
}

.coupon-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.coupon-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.coupon-condition {
  font-size: 12px;
  color: #999;
}

.coupon-unusable {
  font-size: 12px;
  color: #c0c4cc;
}

.coupon-save {
  font-size: 12px;
  color: #F56C6C;
  font-weight: 500;
}

.coupon-check {
  color: #409EFF;
  font-size: 22px;
  flex-shrink: 0;
}

.sidebar {
  width: 300px;
}

.summary-card {
  position: sticky;
  top: 100px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.summary-item.discount {
  color: #F56C6C;
}

.summary-item.total {
  border-bottom: none;
  font-size: 18px;
  font-weight: bold;
  margin-top: 10px;
}

.summary-item .amount {
  color: #F56C6C;
  font-size: 24px;
}
</style>
