<template>
  <div class="ai-assistant-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>AI智能购物助手</span>
          <el-tag type="success">多智能体协作</el-tag>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="12">
          <div class="input-section">
            <h3>输入信息</h3>

            <el-form :model="analysisForm" label-width="100px">
              <el-form-item label="商品ID">
                <el-input v-model="analysisForm.productId" placeholder="请输入商品ID" />
              </el-form-item>

              <el-form-item label="用户ID">
                <el-input v-model="analysisForm.userId" placeholder="请输入用户ID" />
              </el-form-item>

              <el-form-item label="您的需求">
                <el-input
                  v-model="analysisForm.userQuery"
                  type="textarea"
                  :rows="3"
                  placeholder="请描述您的购物需求..."
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="startAnalysis" :loading="loading">
                  开始AI分析
                </el-button>
                <el-button @click="startStreamAnalysis" :loading="streamLoading">
                  流式分析
                </el-button>
                <el-button @click="clearResults">
                  清空结果
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-col>

        <el-col :span="12">
          <div class="result-section">
            <h3>分析结果</h3>

            <div v-if="streamingText" class="stream-result">
              <el-card shadow="hover">
                <div class="stream-content" v-html="streamingText"></div>
              </el-card>
            </div>

            <div v-else-if="!hasResult" class="empty-result">
              <el-empty description="暂无分析结果，请开始分析" />
            </div>

            <div v-else class="analysis-result">
              <el-card class="result-card" shadow="hover">
                <template #header>
                  <div class="result-header">
                    <span>综合评分</span>
                    <el-rate
                      v-model="overallScore"
                      disabled
                      show-score
                      :max="10"
                      text-color="#ff9900"
                    />
                  </div>
                </template>

                <el-descriptions :column="2" border>
                  <el-descriptions-item label="商品名称">
                    {{ recommendation.productName }}
                  </el-descriptions-item>
                  <el-descriptions-item label="当前价格">
                    <span style="color: #F56C6C; font-weight: bold;">
                      ¥{{ recommendation.currentPrice }}
                    </span>
                  </el-descriptions-item>
                  <el-descriptions-item label="最终价格">
                    <span style="color: #67C23A; font-weight: bold;">
                      ¥{{ recommendation.finalPrice }}
                    </span>
                  </el-descriptions-item>
                  <el-descriptions-item label="节省金额">
                    <span style="color: #E6A23C;">
                      ¥{{ recommendation.totalSavings }}
                    </span>
                  </el-descriptions-item>
                </el-descriptions>

                <div class="recommendation-text">
                  <h4>购买建议</h4>
                  <p>{{ recommendation.buyRecommendation }}</p>
                </div>

                <div v-if="recommendation.summary" class="summary-section">
                  <h4>分析摘要</h4>
                  <el-tag
                    v-for="(value, key) in recommendation.summary"
                    :key="key"
                    :type="getTagType(key)"
                    style="margin: 5px"
                  >
                    {{ value }}
                  </el-tag>
                </div>
              </el-card>

              <el-divider>详细分析</el-divider>

              <el-tabs v-model="activeTab">
                <el-tab-pane label="商品分析" name="product">
                  <div class="analysis-detail">
                    <el-descriptions :column="1" border>
                      <el-descriptions-item label="商品特点">
                        {{ productAnalysis.features }}
                      </el-descriptions-item>
                      <el-descriptions-item label="品质评估">
                        {{ productAnalysis.quality }}
                      </el-descriptions-item>
                      <el-descriptions-item label="适用人群">
                        {{ productAnalysis.targetAudience }}
                      </el-descriptions-item>
                      <el-descriptions-item label="使用场景">
                        {{ productAnalysis.usageScenarios }}
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="价格分析" name="price">
                  <div class="analysis-detail">
                    <el-descriptions :column="2" border>
                      <el-descriptions-item label="当前价格">
                        ¥{{ priceAnalysis.currentPrice }}
                      </el-descriptions-item>
                      <el-descriptions-item label="原价">
                        ¥{{ priceAnalysis.originalPrice }}
                      </el-descriptions-item>
                      <el-descriptions-item label="折扣率">
                        {{ priceAnalysis.discountRate }}%
                      </el-descriptions-item>
                      <el-descriptions-item label="价格趋势">
                        <el-tag :type="getTrendType(priceAnalysis.priceTrend)">
                          {{ priceAnalysis.priceTrend }}
                        </el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item label="购买建议" :span="2">
                        {{ priceAnalysis.buyRecommendation }}
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                </el-tab-pane>

                <el-tab-pane label="优惠券分析" name="coupon">
                  <div class="analysis-detail">
                    <el-alert
                      v-if="couponStrategy.recommendation"
                      :title="couponStrategy.recommendation"
                      type="success"
                      :closable="false"
                      style="margin-bottom: 20px"
                    />

                    <el-descriptions :column="2" border v-if="couponStrategy.bestCoupon">
                      <el-descriptions-item label="优惠券名称">
                        {{ couponStrategy.bestCoupon.templateName }}
                      </el-descriptions-item>
                      <el-descriptions-item label="优惠金额">
                        ¥{{ couponStrategy.maxDiscount }}
                      </el-descriptions-item>
                      <el-descriptions-item label="最终价格" :span="2">
                        <span style="color: #67C23A; font-weight: bold;">
                          ¥{{ couponStrategy.finalPrice }}
                        </span>
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                </el-tab-pane>
              </el-tabs>

              <div class="execution-info">
                <el-tag type="info">
                  执行时间: {{ executionTime }}秒
                </el-tag>
                <el-tag type="info" style="margin-left: 10px">
                  参与智能体: {{ agentsInvolved.join(', ') }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { analyzeProduct, streamAnalyze } from '@/api/ai'

const loading = ref(false)
const streamLoading = ref(false)
const hasResult = ref(false)
const activeTab = ref('product')
const streamingText = ref('')

const analysisForm = reactive({
  productId: '',
  userId: '',
  userQuery: '我想买一款性价比高的手机'
})

const result = ref({})
const recommendation = ref({})
const productAnalysis = ref({})
const priceAnalysis = ref({})
const couponStrategy = ref({})
const executionTime = ref(0)
const agentsInvolved = ref([])

const overallScore = computed(() => recommendation.value.overallScore || 0)

const startAnalysis = async () => {
  if (!analysisForm.productId || !analysisForm.userQuery) {
    ElMessage.warning('请填写商品ID和您的需求')
    return
  }

  loading.value = true
  streamingText.value = ''

  try {
    const res = await analyzeProduct({
      productId: analysisForm.productId,
      userId: analysisForm.userId,
      userQuery: analysisForm.userQuery
    })

    result.value = res.data || res
    recommendation.value = result.value.recommendation || {}
    productAnalysis.value = result.value.productAnalysis?.analysis || {}
    priceAnalysis.value = result.value.priceAnalysis?.priceAnalysis || {}
    couponStrategy.value = result.value.couponStrategy || result.value.couponAnalysis?.bestStrategy || {}
    executionTime.value = result.value.executionTime || 0
    agentsInvolved.value = result.value.agentsInvolved || []

    hasResult.value = true
    ElMessage.success('AI分析完成！')
  } catch (error) {
    console.error('AI分析失败:', error)
    ElMessage.error('AI分析失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const startStreamAnalysis = async () => {
  if (!analysisForm.productId || !analysisForm.userQuery) {
    ElMessage.warning('请填写商品ID和您的需求')
    return
  }

  streamLoading.value = true
  hasResult.value = false
  streamingText.value = ''

  await streamAnalyze(
    {
      productId: analysisForm.productId,
      userId: analysisForm.userId,
      userQuery: analysisForm.userQuery
    },
    (data) => {
      if (data.content) {
        streamingText.value += data.content
      } else if (data.recommendation) {
        streamingText.value = ''
        result.value = data
        recommendation.value = data.recommendation || {}
        productAnalysis.value = data.productAnalysis?.analysis || {}
        priceAnalysis.value = data.priceAnalysis?.priceAnalysis || {}
        couponStrategy.value = data.couponStrategy || data.couponAnalysis?.bestStrategy || {}
        executionTime.value = data.executionTime || 0
        agentsInvolved.value = data.agentsInvolved || []
        hasResult.value = true
      }
    },
    (error) => {
      console.error('流式分析失败:', error)
      ElMessage.error('流式分析失败，请稍后重试')
      streamLoading.value = false
    },
    () => {
      streamLoading.value = false
      if (streamingText.value && !hasResult.value) {
        ElMessage.success('流式分析完成')
      }
    }
  )
}

const clearResults = () => {
  hasResult.value = false
  streamingText.value = ''
  result.value = {}
  recommendation.value = {}
  productAnalysis.value = {}
  priceAnalysis.value = {}
  couponStrategy.value = {}
}

const getTagType = (key) => {
  const typeMap = {
    productQuality: 'success',
    priceRating: 'warning',
    couponBenefit: 'danger',
    action: 'primary'
  }
  return typeMap[key] || 'info'
}

const getTrendType = (trend) => {
  const typeMap = {
    '下降': 'success',
    '上升': 'danger',
    '稳定': 'info'
  }
  return typeMap[trend] || 'info'
}
</script>

<style scoped>
.ai-assistant-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-section,
.result-section {
  padding: 20px;
}

.input-section h3,
.result-section h3 {
  margin-bottom: 20px;
  color: #303133;
}

.empty-result {
  padding: 50px 0;
  text-align: center;
}

.stream-result {
  margin-bottom: 20px;
}

.stream-content {
  white-space: pre-wrap;
  line-height: 1.8;
  color: #303133;
}

.result-card {
  margin-bottom: 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recommendation-text {
  margin-top: 20px;
  padding: 15px;
  background: #f0f9ff;
  border-radius: 8px;
}

.recommendation-text h4 {
  margin-bottom: 10px;
  color: #409EFF;
}

.summary-section {
  margin-top: 20px;
}

.summary-section h4 {
  margin-bottom: 10px;
}

.analysis-detail {
  padding: 10px;
}

.execution-info {
  margin-top: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  text-align: center;
}
</style>
