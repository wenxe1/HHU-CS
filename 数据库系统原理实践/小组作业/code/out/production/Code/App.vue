<template>
  <div class="common-layout">
    <el-container class="layout-container">
      <!-- 侧边导航 -->
      <el-aside width="220px" class="aside">
        <div class="logo">
          <el-icon><DataBoard /></el-icon>
          <span>一卡通 DB 管理</span>
        </div>
        <el-menu
            active-text-color="#409EFF"
            background-color="#304156"
            text-color="#fff"
            :default-active="activeTab"
            @select="handleMenuSelect"
            class="el-menu-vertical"
        >
          <el-menu-item index="user">
            <el-icon><User /></el-icon><span>用户信息查询</span>
          </el-menu-item>
          <el-menu-item index="card">
            <el-icon><CreditCard /></el-icon><span>卡片与余额管理</span>
          </el-menu-item>
          <el-menu-item index="merchant">
            <el-icon><Shop /></el-icon><span>商户信息与状态</span>
          </el-menu-item>
          <el-menu-item index="consume">
            <el-icon><ShoppingCart /></el-icon><span>消费记录流水</span>
          </el-menu-item>
          <el-menu-item index="recharge">
            <el-icon><Wallet /></el-icon><span>充值记录流水</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header class="header">
          <div class="header-title">基于 openGauss 的校园一卡通消费系统</div>
          <el-tag type="success" effect="dark" round>数据库连接正常</el-tag>
        </el-header>

        <el-main class="main-content">
          <!-- 模块 1: 用户信息 -->
          <div v-if="activeTab === 'user'">
            <div class="module-header">
              <h2>用户信息表 (Users)</h2>
              <el-input v-model="searchText" placeholder="输入姓名/证件号查询" style="width: 200px" prefix-icon="Search"/>
            </div>
            <el-table :data="filterUsers" border stripe style="width: 100%">
              <el-table-column prop="user_id" label="用户编号" width="100" />
              <el-table-column prop="name" label="姓名" width="120" />
              <el-table-column prop="type" label="用户类型">
                <template #default="scope">
                  <el-tag :type="scope.row.type === '教职工' ? 'warning' : ''">{{ scope.row.type }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="id_card" label="证件号" width="180" />
              <el-table-column prop="phone" label="联系方式" />
              <el-table-column prop="email" label="电子邮箱" />
            </el-table>
          </div>

          <!-- 模块 2: 卡片与余额 (核心) -->
          <div v-if="activeTab === 'card'">
            <div class="module-header">
              <h2>一卡通卡片表 (Card)</h2>
              <el-button type="primary" plain>+ 补办新卡</el-button>
            </div>
            <el-table :data="cardList" border style="width: 100%">
              <el-table-column prop="card_no" label="卡号" width="150" font-family="monospace"/>
              <el-table-column prop="owner_name" label="所属用户" width="120" />
              <el-table-column prop="balance" label="当前余额" width="150">
                <template #default="scope">
                  <span style="color: #67C23A; font-weight: bold;">¥ {{ scope.row.balance.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="卡片状态">
                <template #default="scope">
                  <el-tag :type="getCardStatusTag(scope.row.status)">{{ scope.row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="issue_time" label="办卡时间" />
              <el-table-column label="操作">
                <template #default="scope">
                  <el-button size="small" type="danger" v-if="scope.row.status === '正常'">挂失</el-button>
                  <el-button size="small" type="success" v-if="scope.row.status === '挂失'">解挂</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 模块 3: 商户管理 (营业状态设置) -->
          <div v-if="activeTab === 'merchant'">
            <div class="module-header">
              <h2>商户信息表 (Merchant)</h2>
            </div>
            <el-table :data="merchantList" border stripe>
              <el-table-column prop="merchant_id" label="商户编号" width="100" />
              <el-table-column prop="name" label="商户名称" width="150" />
              <el-table-column prop="type" label="类型" width="120" />
              <el-table-column prop="location" label="商户位置" />
              <el-table-column label="营业状态设置 (UPDATE)">
                <template #default="scope">
                  <el-switch
                      v-model="scope.row.is_open"
                      active-text="营业"
                      inactive-text="停业"
                      inline-prompt
                      style="--el-switch-on-color: #13ce66; --el-switch-off-color: #ff4949"
                      @change="handleStatusChange(scope.row)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 模块 4: 消费记录 -->
          <div v-if="activeTab === 'consume'">
            <div class="module-header">
              <h2>消费记录流水 (ConsumeRecord)</h2>
            </div>
            <el-table :data="consumeList" stripe style="width: 100%">
              <el-table-column prop="id" label="流水号" width="100" />
              <el-table-column prop="card_no" label="消费卡号" width="140" />
              <el-table-column prop="merchant_name" label="消费商户" />
              <el-table-column prop="amount" label="消费金额">
                <template #default="scope">
                  <span style="color: #F56C6C;">- ¥ {{ scope.row.amount.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="time" label="消费时间" width="180" />
              <el-table-column prop="note" label="备注" />
            </el-table>
          </div>

          <!-- 模块 5: 充值记录 -->
          <div v-if="activeTab === 'recharge'">
            <div class="module-header">
              <h2>充值记录流水 (RechargeRecord)</h2>
            </div>
            <el-table :data="rechargeList" stripe style="width: 100%">
              <el-table-column prop="id" label="充值编号" width="100" />
              <el-table-column prop="card_no" label="充值卡号" width="140" />
              <el-table-column prop="amount" label="充值金额">
                <template #default="scope">
                  <span style="color: #67C23A;">+ ¥ {{ scope.row.amount.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="method" label="充值方式">
                <template #default="scope">
                  <el-tag effect="plain">{{ scope.row.method }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="time" label="充值时间" width="180" />
              <el-table-column prop="status" label="状态">
                <template #default="scope">
                  <el-icon v-if="scope.row.status === '成功'" color="#67C23A"><CircleCheck /></el-icon>
                  <el-icon v-else color="#F56C6C"><CircleClose /></el-icon>
                  {{ scope.row.status }}
                </template>
              </el-table-column>
            </el-table>
          </div>

        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { User, CreditCard, Shop, ShoppingCart, Wallet, DataBoard, Search, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('card') // 默认显示卡片页
const searchText = ref('')

// 模拟数据库数据 (根据你的背景要求设计)
const userList = ref([
  { user_id: 1001, name: '张三', type: '学生', id_card: '1101012002...', phone: '13800138000', email: 'zhangsan@uni.edu' },
  { user_id: 2001, name: '李老师', type: '教职工', id_card: '3201021980...', phone: '13900139000', email: 'li@uni.edu' },
])

const cardList = ref([
  { card_no: 'CARD_2024_001', owner_name: '张三', balance: 125.50, status: '正常', issue_time: '2024-01-10' },
  { card_no: 'CARD_2024_002', owner_name: '李老师', balance: 500.00, status: '挂失', issue_time: '2023-12-05' },
])

const merchantList = ref([
  { merchant_id: 1, name: '第一食堂', type: '食堂', location: '北区一楼', is_open: true },
  { merchant_id: 2, name: '教育超市', type: '超市', location: '生活区', is_open: true },
  { merchant_id: 3, name: '校园书店', type: '书店', location: '图书馆旁', is_open: false },
])

const consumeList = ref([
  { id: 5001, card_no: 'CARD_2024_001', merchant_name: '第一食堂', amount: 15.00, time: '2024-05-20 12:00:00', note: '午餐' },
  { id: 5002, card_no: 'CARD_2024_001', merchant_name: '教育超市', amount: 3.50, time: '2024-05-20 18:30:00', note: '买水' },
])

const rechargeList = ref([
  { id: 8001, card_no: 'CARD_2024_001', amount: 100.00, method: '线上', time: '2024-05-19 10:00:00', status: '成功' },
  { id: 8002, card_no: 'CARD_2024_002', amount: 500.00, method: '线下', time: '2024-05-01 09:00:00', status: '成功' },
])

// 逻辑方法
const handleMenuSelect = (index) => {
  activeTab.value = index
}

const getCardStatusTag = (status) => {
  if (status === '正常') return 'success'
  if (status === '挂失') return 'danger'
  return 'info'
}

const handleStatusChange = (row) => {
  // 模拟发送 Update SQL
  const statusStr = row.is_open ? '营业' : '停业'
  ElMessage.success(`数据库操作成功: UPDATE merchant SET status='${statusStr}' WHERE id=${row.merchant_id}`)
}

const filterUsers = computed(() => {
  return userList.value.filter(u => u.name.includes(searchText.value) || u.id_card.includes(searchText.value))
})
</script>

<style scoped>
.layout-container { height: 100vh; }
.aside { background-color: #304156; color: white; display: flex; flex-direction: column; }
.logo { height: 60px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: bold; background-color: #2b3649; }
.logo .el-icon { margin-right: 8px; font-size: 22px; }
.header { background-color: #fff; border-bottom: 1px solid #dcdfe6; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; }
.header-title { font-size: 18px; font-weight: 600; color: #303133; }
.main-content { background-color: #f0f2f5; padding: 20px; }
.module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: #fff; padding: 15px 20px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,21,41,.08); }
.module-header h2 { margin: 0; font-size: 16px; border-left: 4px solid #409EFF; padding-left: 10px; color: #303133; }
</style>