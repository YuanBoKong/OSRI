<template>
  <div id="app">
    <div class="app-container">
      <!-- 顶部导航栏 -->
      <header class="main-header">
        <div class="header-wrapper">
          <div class="logo-section">
            <div class="logo-icon">
              <el-icon :size="32"><DataAnalysis /></el-icon>
            </div>
            <div class="logo-text">
              <h1 class="app-title">OSRI指标计算平台</h1>
              <p class="app-subtitle">Open Science Research Index Calculation System</p>
            </div>
          </div>
          
          <nav class="main-nav">
            <div class="nav-buttons">
              <router-link 
                to="/jsondata" 
                class="nav-button"
                :class="{ 'is-active': activeMenu === '/jsondata' || activeMenu.startsWith('/jsondata') }"
              >
                <el-icon><FolderOpened /></el-icon>
                <span>数据管理</span>
              </router-link>
              <router-link 
                to="/output" 
                class="nav-button"
                :class="{ 'is-active': activeMenu === '/output' || activeMenu.startsWith('/output') }"
              >
                <el-icon><TrendCharts /></el-icon>
                <span>计算结果</span>
              </router-link>
              <router-link
                to="/datavis"
                class="nav-button"
                :class="{ 'is-active': activeMenu === '/datavis' || activeMenu.startsWith('/datavis') }"
              >
                <el-icon><DataAnalysis /></el-icon>
                <span>结果可视化</span>
              </router-link>
            </div>
          </nav>
          
          <div class="header-actions">
            <!-- 版本切换 -->
            <div class="version-switch">
              <span class="version-label">全球</span>
              <el-switch
                v-model="isAggregationMode"
                size="large"
                @change="handleVersionChange"
                active-text="聚合"
                inactive-text="全球"
                inline-prompt
                active-color="#667eea"
                inactive-color="#67c23a"
              />
              <span class="version-label">聚合</span>
            </div>
            <el-button 
              type="primary"
              size="large"
              :loading="calculating"
              @click="handleCalculate"
              class="calculate-btn"
            >
              <template #icon>
                <el-icon v-if="!calculating"><RefreshRight /></el-icon>
              </template>
              {{ calculating ? '计算中...' : '重新计算' }}
            </el-button>
          </div>
        </div>
      </header>

      <!-- 主内容区 -->
      <main class="main-content" :class="{ 'main-content--immersive': isDataVisRoute }">
        <div class="content-wrapper" :class="{ 'content-wrapper--immersive': isDataVisRoute }">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import { ref, computed, provide, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, FolderOpened, TrendCharts, RefreshRight } from '@element-plus/icons-vue'
import { executeBatchCalculate, getCalculateStatus } from './api/calculate'

export default {
  name: 'App',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const calculating = ref(false)
    
    // 版本模式：'global' 或 'aggregation'，从 localStorage 读取，默认为 'global'
    const getStoredVersionMode = () => {
      try {
        const stored = localStorage.getItem('osri_version_mode')
        return stored === 'aggregation' ? 'aggregation' : 'global'
      } catch (e) {
        return 'global'
      }
    }
    
    const versionMode = ref(getStoredVersionMode())
    
    // 计算属性：是否为聚合模式（用于 el-switch）
    const isAggregationMode = computed({
      get: () => versionMode.value === 'aggregation',
      set: (value) => {
        versionMode.value = value ? 'aggregation' : 'global'
      }
    })

    const activeMenu = computed(() => route.path)
    const isDataVisRoute = computed(() => route.path.startsWith('/datavis'))
    let calculatePollTimer = null

    // 提供版本模式给子组件
    provide('versionMode', versionMode)

    // 版本切换处理
    const handleVersionChange = (value) => {
      const mode = value ? 'aggregation' : 'global'
      // 保存到 localStorage
      try {
        localStorage.setItem('osri_version_mode', mode)
      } catch (e) {
        console.warn('无法保存版本模式到 localStorage:', e)
      }
      
      // 切换版本时，可以刷新当前页面数据
      // 这里只切换模式，具体的数据刷新由各个子组件监听 versionMode 变化来处理
      ElMessage.info({
        message: `已切换到${mode === 'global' ? '全球' : '聚合'}版本`,
        duration: 2000
      })
    }

    const clearCalculatePollTimer = () => {
      if (calculatePollTimer) {
        clearTimeout(calculatePollTimer)
        calculatePollTimer = null
      }
    }

    const sleep = (ms) => new Promise(resolve => {
      clearCalculatePollTimer()
      calculatePollTimer = window.setTimeout(() => {
        calculatePollTimer = null
        resolve()
      }, ms)
    })

    const waitForCalculationCompletion = async (mode) => {
      const timeoutAt = Date.now() + 30 * 60 * 1000

      while (Date.now() < timeoutAt) {
        const status = await getCalculateStatus(mode)
        if (status.status === 'completed') {
          return status
        }
        if (status.status === 'failed') {
          throw new Error(status.message || '批量计算失败')
        }
        await sleep(2000)
      }

      throw new Error('等待批量计算完成超时')
    }

    const handleCalculate = async () => {
      calculating.value = true
      const currentMode = versionMode.value
      try {
        await executeBatchCalculate(currentMode)
        ElMessage.info({
          message: `${currentMode === 'global' ? '全球' : '聚合'}版本批量计算已启动，正在等待可视化同步完成`,
          duration: 2500
        })

        const status = await waitForCalculationCompletion(currentMode)
        const syncedCount = Array.isArray(status.synced_files) ? status.synced_files.length : 0

        ElMessage.success({
          message: `${currentMode === 'global' ? '全球' : '聚合'}版本计算完成，可视化已同步${syncedCount ? `（${syncedCount}个文件）` : ''}`,
          type: 'success',
          duration: 3500
        })
        router.go(0)
      } catch (error) {
        ElMessage.error({
          message: (error.response?.data?.detail || error.message || '未知错误'),
          duration: 3000
        })
      } finally {
        clearCalculatePollTimer()
        calculating.value = false
      }
    }

    onBeforeUnmount(() => {
      clearCalculatePollTimer()
    })

    return {
      calculating,
      activeMenu,
      isDataVisRoute,
      versionMode,
      isAggregationMode,
      handleVersionChange,
      handleCalculate,
      DataAnalysis,
      FolderOpened,
      TrendCharts,
      RefreshRight
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-attachment: fixed;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 顶部导航栏 */
.main-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-wrapper {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 80px;
  gap: 40px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.logo-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.logo-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
  line-height: 1.2;
}

.app-subtitle {
  font-size: 12px;
  color: #718096;
  margin: 0;
  font-weight: 400;
  letter-spacing: 0.5px;
}

.main-nav {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.nav-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  color: #4a5568;
  text-decoration: none;
  border-radius: 10px;
  transition: all 0.3s ease;
  background: transparent;
  border: none;
  cursor: pointer;
}

.nav-button:hover {
  background: rgba(102, 126, 234, 0.08);
  color: #667eea;
}

.nav-button.is-active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.nav-button.is-active:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.nav-button .el-icon {
  font-size: 18px;
}

.header-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 20px;
}

.version-switch {
  display: flex;
  align-items: center;
  gap: 12px;
}

.version-label {
  font-size: 15px;
  font-weight: 600;
  color: #4a5568;
  min-width: 40px;
  text-align: center;
}

.version-switch :deep(.el-switch) {
  --el-switch-on-color: #667eea;
  --el-switch-off-color: #67c23a;
}

.version-switch :deep(.el-switch__label) {
  font-weight: 600;
  font-size: 14px;
}

.calculate-btn {
  height: 44px;
  padding: 0 28px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.calculate-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

/* 主内容区 */
.main-content {
  flex: 1;
  min-height: 0;
  padding: 40px;
  display: flex;
  justify-content: center;
}

.content-wrapper {
  width: 100%;
  max-width: 1600px;
}

.main-content--immersive {
  padding: 0;
  display: block;
  overflow: hidden;
  height: calc(100vh - 80px);
  min-height: calc(100vh - 80px);
}

.content-wrapper--immersive {
  max-width: none;
  height: calc(100vh - 80px);
  min-height: calc(100vh - 80px);
}

/* 页面过渡动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .header-wrapper {
    padding: 0 24px;
  }
  
  .main-content {
    padding: 24px;
  }
}

@media (max-width: 768px) {
  .header-wrapper {
    flex-wrap: wrap;
    height: auto;
    padding: 16px;
  }
  
  .logo-section {
    width: 100%;
  }
  
  .main-nav {
    width: 100%;
    margin-top: 16px;
  }
  
  .nav-buttons {
    width: 100%;
    justify-content: center;
  }
  
  .nav-button {
    flex: 1;
    justify-content: center;
    max-width: 200px;
  }
  
  .header-actions {
    width: 100%;
    margin-top: 16px;
  }
  
  .calculate-btn {
    width: 100%;
  }

  .main-content--immersive {
    height: calc(100vh - 148px);
    min-height: calc(100vh - 148px);
  }

  .content-wrapper--immersive {
    height: calc(100vh - 148px);
    min-height: calc(100vh - 148px);
  }
}
</style>
