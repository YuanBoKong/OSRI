<template>
  <div class="output-results">
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
          <el-icon :size="28"><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ fileList.length }}</div>
          <div class="stat-label">计算结果文件</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
          <el-icon :size="28"><DataAnalysis /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ tableData.length || (isSingleValue ? 1 : 0) }}</div>
          <div class="stat-label">{{ isSingleValue ? '单值结果' : '数据年份' }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
          <el-icon :size="28"><Collection /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ countryCount }}</div>
          <div class="stat-label">国家/地区/组织</div>
        </div>
      </div>
    </div>

    <!-- 主内容卡片 -->
    <el-card class="main-card" shadow="always">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon class="header-icon"><TrendCharts /></el-icon>
            <div>
              <h2 class="card-title">计算结果</h2>
              <p class="card-subtitle">查看和管理计算结果输出文件</p>
            </div>
          </div>
          <el-button 
            type="primary" 
            size="large"
            @click="handleRefresh" 
            :icon="Refresh"
            circle
            class="refresh-btn"
          />
        </div>
      </template>

      <!-- 文件列表 - 层级结构 -->
      <div v-if="fileList.length > 0" class="category-container">
        <!-- 一级分类：横向标签页 -->
        <el-tabs 
          v-model="activeCategory" 
          @tab-change="handleCategoryChange"
          class="category-tabs"
          type="card"
        >
          <el-tab-pane
            v-for="category in categoryOrder"
            :key="category"
            :name="category"
          >
            <template #label>
              <div class="category-label">
                <el-icon class="category-icon"><FolderOpened /></el-icon>
                <span class="category-name">{{ category }}</span>
                <el-badge 
                  :value="getCategoryFileCount(category)" 
                  class="category-badge"
                  :max="99"
                />
              </div>
            </template>
            
            <!-- 二级文件：嵌套标签页 -->
            <div class="category-files">
              <el-tabs 
                v-model="activeTab" 
                @tab-click="onTabClick" 
                class="nested-tabs"
                type="card"
                @tab-change="(name) => handleCategoryTabChange(name, category)"
              >
                <el-tab-pane
                  v-for="filename in getCategoryFiles(category)"
                  :key="filename"
                  :name="filename"
                  :label="filename"
                >
                  <template #label>
                    <el-tooltip 
                      :content="getFileDescription(filename) || filename" 
                      placement="top"
                      :disabled="!getFileDescription(filename)"
                    >
                      <span>{{ filename }}</span>
                    </el-tooltip>
                  </template>
                  
                  <div class="file-content">
            <!-- 显示文件描述 -->
            <div v-if="getFileDescription(activeTab)" class="file-description">
              <el-icon :size="18"><InfoFilled /></el-icon>
              <span>{{ getFileDescription(activeTab) }}</span>
            </div>
            
            <!-- 单值文件显示 -->
            <div v-if="isSingleValue" class="single-value-display">
              <div class="single-value-card">
                <div class="single-value-header">
                  <div class="function-name">
                    <el-icon :size="24"><DataAnalysis /></el-icon>
                    <span>{{ activeTab.replace('.json', '') }}</span>
                  </div>
                </div>
                <div class="single-value-content">
                  <div class="value-display">
                    <div class="value-label">计算结果</div>
                    <el-input-number
                      v-model="singleValue"
                      :precision="10"
                      :step="0.0001"
                      size="large"
                      @change="handleSingleValueChange"
                      class="value-input"
                    />
                  </div>
                  <div class="single-value-actions">
                    <el-button 
                      type="primary" 
                      size="large"
                      @click="handleSaveSingleValue" 
                      :icon="Document"
                      class="save-btn"
                    >
                      保存修改
                    </el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 表格显示 -->
            <div v-else>
              <div class="toolbar">
                <el-button 
                  type="primary" 
                  size="large"
                  @click="handleSave(activeTab)" 
                  :icon="Document"
                  class="tool-btn save-btn"
                >
                  保存修改
                </el-button>
                <el-button 
                  type="success" 
                  size="large"
                  @click="handleExportExcel(activeTab)" 
                  :icon="Download"
                  class="tool-btn"
                >
                  导出Excel
                </el-button>
                <el-button 
                  type="info" 
                  size="large"
                  @click="handleFilter(activeTab)" 
                  :icon="Filter"
                  class="tool-btn"
                >
                  筛选数据
                </el-button>
              </div>

              <div class="table-container">
                <div class="split-table-wrapper">
                  <!-- 左侧固定表格：只显示年份列 -->
                  <div class="fixed-table-left" ref="fixedTableLeftRef">
                    <el-table
                      ref="fixedTableRef"
                      :data="tableData"
                      height="600"
                      v-loading="loading"
                      class="modern-table fixed-table"
                      :row-class-name="tableRowClassName"
                    >
                      <el-table-column prop="year" label="年份" width="120" align="center">
                        <template #default="scope">
                          <div class="year-cell">
                            <el-input
                              v-if="editingCell === `${scope.row.year}_year`"
                              v-model="scope.row.year"
                              @blur="saveCellEdit(scope.row, 'year')"
                              @keyup.enter="saveCellEdit(scope.row, 'year')"
                              size="large"
                            />
                            <div v-else @click="startCellEdit(`${scope.row.year}_year`)" class="editable-cell">
                              {{ scope.row.year }}
                            </div>
                          </div>
                        </template>
                      </el-table-column>
                    </el-table>
                  </div>
                  
                  <!-- 右侧滚动表格：显示其他列 -->
                  <div class="scroll-table-right" ref="scrollTableRightRef">
                    <el-table
                      ref="scrollTableRef"
                      :data="tableData"
                      height="600"
                      v-loading="loading"
                      class="modern-table scroll-table"
                      :row-class-name="tableRowClassName"
                    >
                      <el-table-column
                        v-for="country in countries"
                        :key="country"
                        :prop="country"
                        :label="country"
                        width="160"
                        align="center"
                      >
                        <template #default="scope">
                          <div class="data-cell">
                            <el-input-number
                              v-if="editingCell === `${scope.row.year}_${country}`"
                              v-model="scope.row[country]"
                              :precision="10"
                              :step="0.0001"
                              @blur="saveCellEdit(scope.row, country)"
                              @keyup.enter="saveCellEdit(scope.row, country)"
                              size="small"
                              :controls="false"
                            />
                            <div v-else @click="startCellEdit(`${scope.row.year}_${country}`)" class="editable-cell">
                              {{ scope.row[country] !== null && scope.row[country] !== undefined 
                                ? Number(scope.row[country]).toFixed(8) 
                                : '—' }}
                            </div>
                          </div>
                        </template>
                      </el-table-column>
                      
                    </el-table>
                  </div>
                </div>
              </div>
            </div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>

    <!-- 筛选对话框 -->
    <el-dialog
      v-model="filterDialogVisible"
      title="筛选数据"
      width="600px"
      class="modern-dialog"
    >
      <el-form :model="filterForm" label-width="100px" label-position="top">
        <el-form-item label="选择年份（可多选）">
          <el-select
            v-model="filterForm.years"
            placeholder="请选择年份"
            multiple
            size="large"
            style="width: 100%"
            filterable
            clearable
          >
            <el-option
              v-for="year in availableYears"
              :key="year"
              :label="year"
              :value="year"
            />
          </el-select>
          <div class="filter-tip">
            <el-text type="info" size="small">不选择则显示所有年份</el-text>
          </div>
        </el-form-item>
        <el-form-item label="选择国家/地区（可多选，支持搜索）">
          <el-select
            v-model="filterForm.countries"
            placeholder="请输入或选择国家/地区"
            multiple
            size="large"
            style="width: 100%"
            filterable
            clearable
            :filter-method="filterCountries"
          >
            <el-option
              v-for="country in filteredCountryOptions"
              :key="country"
              :label="country"
              :value="country"
            />
          </el-select>
          <div class="filter-tip">
            <el-text type="info" size="small">不选择则显示所有国家/地区</el-text>
          </div>
        </el-form-item>
        <el-alert
          title="提示"
          type="info"
          :closable="false"
          style="margin-top: 16px"
        >
          <template #default>
            筛选后的数据将替换当前显示的数据，点击"清除筛选"可恢复原始数据
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="handleClearFilter" size="large">清除筛选</el-button>
        <el-button @click="filterDialogVisible = false" size="large">取消</el-button>
        <el-button type="primary" @click="confirmFilter" :loading="filtering" size="large">
          {{ filtering ? '筛选中...' : '确定筛选' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed, nextTick, watch, inject } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Document, TrendCharts, DataAnalysis, Collection, InfoFilled, Download, Filter, FolderOpened } from '@element-plus/icons-vue'
import { listOutputFiles, getOutputFile, updateOutputFile, exportOutputToExcel, filterOutputFile } from '../api/output'
import { getJsonDataFile } from '../api/jsondata'

export default {
  name: 'OutputResults',
  setup() {
    // 注入版本模式
    const versionMode = inject('versionMode', ref('global'))
    // 文件顺序和描述映射
    const fileOrderAndDescription = {
      'R.json': 'OSRI计算结果数据',
      'R_oa.json': '开放获取准备度',
      'R_oa_bar.json': '开放获取准备度',
      'R_open.json': '开放性',
      'r_open_t.json': 'OA论文的占比',
      'r_open_t1.json': 'OA论文年均占比的最大值',
      'P_open_t.json': 'OA数量',
      'P_open_t1.json': 'OA数量均值最大值',
      'R_incl.json': '包容性',
      'P_incl_t.json': '合著论文数量',
      'P_incl_t1.json': '合著论文数量均值的最大值',
      'r_incl_t.json': '合著论文占比',
      'r_incl_t1.json': '合著论文占比均值的最大值',
      'R_od.json': '开放获取准备度',
      'R_od_bar.json': '开放获取准备度',
      'A_od_t.json': '可访问数据量',
      'A_od_t1.json': '可访问数据量均值最大值',
      'S_od_t.json': '可共享数据量',
      'S_od_t1.json': '可共享数据量均值最大值',
      'f1.json': '数据学术质量',
      'f2.json': '数据信息质量',
      'f3.json': '数据完整性（基于撤回率）',
      'R_op_bar.json': '开放政策准备度',
      'S_journal_t.json': '收录期刊',
      'S_policy_t.json': 'OS政策',
      'IPRI.json': 'IPRI'
    }
    
    // 一级和二级的层级结构
    const categoryStructure = {
      '开放科学成熟度': {
        files: ['R.json']
      },
      '开放获取': {
        files: [
          'R_oa.json',
          'R_oa_bar.json',
          'R_open.json',
          'r_open_t.json',
          'r_open_t1.json',
          'P_open_t.json',
          'P_open_t1.json',
          'R_incl.json',
          'P_incl_t.json',
          'P_incl_t1.json',
          'r_incl_t.json',
          'r_incl_t1.json'
        ]
      },
      '开放数据': {
        files: [
          'R_od.json',
          'R_od_bar.json',
          'A_od_t.json',
          'A_od_t1.json',
          'S_od_t.json',
          'S_od_t1.json',
          'f1.json',
          'f2.json',
          'f3.json'
        ]
      },
      '开放政策': {
        files: [
          'R_op_bar.json',
          'S_journal_t.json',
          'S_policy_t.json',
          'IPRI.json',
          "S_law_t.json",
          "S_platform_t.json"
        ]
      }
    }
    
    // 一级分类顺序
    const categoryOrder = ['开放科学成熟度', '开放获取', '开放数据', '开放政策']
    
    const fileList = ref([])
    const activeTab = ref('')
    const currentFileData = ref({})
    const loading = ref(false)
    const editingCell = ref(null)
    const currentFilename = ref('')
    const currentFileRevision = ref('')
    const fixedTableLeftRef = ref(null)
    const scrollTableRightRef = ref(null)
    const fixedTableRef = ref(null)
    const scrollTableRef = ref(null)
    let isSyncingScroll = false
    const activeCategory = ref('') // 当前激活的一级分类
    const countryCount = ref(0) // 国家/地区/组织数量
    
    // 筛选相关
    const filterDialogVisible = ref(false)
    const filtering = ref(false)
    const filterForm = reactive({
      years: [],
      countries: []
    })
    const originalFileData = ref({}) // 保存原始数据，用于清除筛选
    const isFiltered = ref(false) // 标记是否已应用筛选
    const countrySearchText = ref('') // 国家搜索文本

    const isSingleValue = computed(() => {
      return currentFileData.value && 
             'value' in currentFileData.value && 
             Object.keys(currentFileData.value).length === 1
    })

    const singleValue = computed({
      get() {
        return isSingleValue.value ? currentFileData.value.value : null
      },
      set(val) {
        if (isSingleValue.value) {
          currentFileData.value.value = val
        }
      }
    })

    const tableData = computed(() => {
      if (!currentFileData.value || typeof currentFileData.value !== 'object') {
        return []
      }
      
      if (isSingleValue.value) {
        return []
      }
      
      const years = Object.keys(currentFileData.value).sort()
      return years.map(year => {
        const row = { year, ...currentFileData.value[year] }
        return row
      })
    })

    const countries = computed(() => {
      if (!currentFileData.value || typeof currentFileData.value !== 'object' || isSingleValue.value) {
        return []
      }
      
      const firstYear = Object.keys(currentFileData.value)[0]
      if (firstYear && currentFileData.value[firstYear]) {
        return Object.keys(currentFileData.value[firstYear])
          .filter(key => key !== 'year')
          .slice(0, 10)
      }
      return []
    })

    // 获取所有可用的年份（用于筛选）
    const availableYears = computed(() => {
      // 优先从原始数据获取（如果存在），否则从当前数据获取
      const dataSource = (isFiltered.value && originalFileData.value && Object.keys(originalFileData.value).length > 0) 
        ? originalFileData.value 
        : currentFileData.value
        
      if (!dataSource || typeof dataSource !== 'object') {
        return []
      }
      if ('value' in dataSource && Object.keys(dataSource).length === 1) {
        return []
      }
      return Object.keys(dataSource).sort()
    })

    // 获取所有可用的国家（用于筛选）
    const availableCountries = computed(() => {
      // 优先从原始数据获取（如果存在），否则从当前数据获取
      const dataSource = (isFiltered.value && originalFileData.value && Object.keys(originalFileData.value).length > 0) 
        ? originalFileData.value 
        : currentFileData.value
        
      if (!dataSource || typeof dataSource !== 'object') {
        return []
      }
      if ('value' in dataSource && Object.keys(dataSource).length === 1) {
        return []
      }
      const allCountries = new Set()
      for (const yearData of Object.values(dataSource)) {
        if (typeof yearData === 'object' && yearData !== null) {
          Object.keys(yearData).forEach(key => {
            if (key !== 'year') {
              allCountries.add(key)
            }
          })
        }
      }
      return Array.from(allCountries).sort()
    })

    // 过滤后的国家选项（用于搜索）
    const filteredCountryOptions = computed(() => {
      if (!countrySearchText.value) {
        return availableCountries.value
      }
      const searchLower = countrySearchText.value.toLowerCase()
      return availableCountries.value.filter(country => 
        country.toLowerCase().includes(searchLower)
      )
    })

    // 获取文件描述
    const getFileDescription = (filename) => {
      return fileOrderAndDescription[filename] || ''
    }
    
    // 获取分类下的文件列表（过滤出实际存在的文件）
    const getCategoryFiles = (category) => {
      const expectedFiles = categoryStructure[category]?.files || []
      const fileMap = new Map(fileList.value.map(file => [file.filename, file]))
      return expectedFiles.filter(filename => fileMap.has(filename))
    }
    
    // 获取分类下的文件数量
    const getCategoryFileCount = (category) => {
      return getCategoryFiles(category).length
    }
    
    // 对文件列表进行排序（保留用于其他用途）
    const sortFileList = (files) => {
      const fileMap = new Map(files.map(file => [file.filename, file]))
      const sortedFiles = []
      
      // 按照层级结构顺序添加
      for (const category of categoryOrder) {
        const categoryFiles = categoryStructure[category]?.files || []
        for (const filename of categoryFiles) {
          if (fileMap.has(filename)) {
            sortedFiles.push(fileMap.get(filename))
            fileMap.delete(filename)
          }
        }
      }
      
      // 添加其他未在结构中的文件（按文件名排序）
      const remainingFiles = Array.from(fileMap.values()).sort((a, b) => 
        a.filename.localeCompare(b.filename)
      )
      sortedFiles.push(...remainingFiles)
      
      return sortedFiles
    }

    // 加载国家数量（从 jsondata 的 OA.json 文件）
    const loadCountryCount = async () => {
      try {
        const response = await getJsonDataFile('OA.json', versionMode.value)
        const data = response.data || {}
        
        // 获取第一个年份的国家列表
        const years = Object.keys(data).sort()
        if (years.length > 0) {
          const firstYear = years[0]
          const yearData = data[firstYear]
          if (yearData && typeof yearData === 'object') {
            // 排除 'year' 字段
            const countries = Object.keys(yearData).filter(key => key !== 'year')
            countryCount.value = countries.length
          } else {
            countryCount.value = 0
          }
        } else {
          countryCount.value = 0
        }
      } catch (error) {
        // 如果加载失败，设置为 0
        console.warn('加载国家数量失败:', error)
        countryCount.value = 0
      }
    }

    const loadFileList = async () => {
      try {
        const response = await listOutputFiles(versionMode.value)
        const files = response.files || []
        // 按照层级结构顺序排序
        fileList.value = sortFileList(files)
        // 加载国家数量
        await loadCountryCount()
        // 自动激活第一个有文件的分类
        if (fileList.value.length > 0) {
          // 使用 nextTick 确保 fileList.value 已更新
          nextTick(() => {
            for (const category of categoryOrder) {
              const categoryFiles = getCategoryFiles(category)
              if (categoryFiles.length > 0) {
                activeCategory.value = category
                // 设置默认激活标签为第一个分类的第一个文件
                const firstFile = categoryFiles[0]
                if (firstFile) {
                  activeTab.value = firstFile
                  // 自动加载第一个文件的数据
                  loadFileData(firstFile)
                }
                break
              }
            }
          })
        }
      } catch (error) {
        ElMessage.error('加载文件列表失败')
      }
    }

    const loadFileData = async (filename) => {
      if (!filename) return
      
      loading.value = true
      try {
        const response = await getOutputFile(filename, versionMode.value)
        currentFileData.value = response.data || {}
        currentFilename.value = filename
        currentFileRevision.value = response.revision || ''
        
        // 清除筛选状态
        isFiltered.value = false
        originalFileData.value = {}
        
        // 数据加载后，重新布局表格并绑定滚动
        nextTick(() => {
          setTimeout(() => {
            if (fixedTableRef.value && fixedTableRef.value.doLayout) {
              fixedTableRef.value.doLayout()
            }
            if (scrollTableRef.value && scrollTableRef.value.doLayout) {
              scrollTableRef.value.doLayout()
            }
            // 重置绑定标志，允许重新绑定
            resetScrollBinding()
            // 重置重试次数
            bindAttempts = 0
            // 延迟绑定，确保 DOM 完全渲染
            setTimeout(() => {
              bindScrollEvents()
            }, 500)
          }, 300)
        })
      } catch (error) {
        ElMessage.error('加载文件数据失败')
      } finally {
        loading.value = false
      }
    }

    const ensureFileLoaded = async (filename) => {
      if (!filename) {
        throw new Error('未指定文件')
      }

      if (loading.value) {
        throw new Error('文件正在加载，请稍后重试')
      }

      if (currentFilename.value !== filename) {
        await loadFileData(filename)
      }

      if (currentFilename.value !== filename) {
        throw new Error(`当前文件未就绪: ${filename}`)
      }
    }

    const onTabClick = (pane) => {
      const filename = pane?.paneName || pane?.props?.name
      loadFileData(filename)
    }

    const handleCategoryChange = (categoryName) => {
      // 当一级分类切换时，自动选择该分类的第一个文件
      if (categoryName) {
        const categoryFiles = getCategoryFiles(categoryName)
        if (categoryFiles.length > 0) {
          const firstFile = categoryFiles[0]
          activeTab.value = firstFile
          loadFileData(firstFile)
        }
      }
    }

    const handleCategoryTabChange = (name, category) => {
      // 当标签切换时，确保加载数据
      if (name) {
        loadFileData(name)
      }
    }

    const handleRefresh = () => {
      // 懒加载：刷新仅更新文件列表，不自动加载当前数据
      loadFileList()
    }

    const startCellEdit = (cellKey) => {
      editingCell.value = cellKey
    }

    const saveCellEdit = (row, field) => {
      editingCell.value = null
      if (field === 'year') {
        const oldYear = Object.keys(currentFileData.value).find(y => {
          const yearData = currentFileData.value[y]
          return yearData && JSON.stringify(yearData) === JSON.stringify(
            Object.fromEntries(Object.entries(row).filter(([k]) => k !== 'year'))
          )
        })
        if (oldYear && oldYear !== row.year) {
          const yearData = { ...currentFileData.value[oldYear] }
          delete currentFileData.value[oldYear]
          currentFileData.value[row.year] = yearData
        }
      } else {
        if (currentFileData.value[row.year]) {
          currentFileData.value[row.year][field] = row[field]
        }
      }
    }

    const handleSave = async (filename) => {
      try {
        await ensureFileLoaded(filename)
        const response = await updateOutputFile(
          filename,
          currentFileData.value,
          currentFileRevision.value,
          versionMode.value
        )
        currentFileRevision.value = response.revision || currentFileRevision.value
        ElMessage.success({
          message: '保存成功',
          type: 'success'
        })
      } catch (error) {
        ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
      }
    }

    const handleSaveSingleValue = async () => {
      await handleSave(currentFilename.value)
    }

    const handleSingleValueChange = () => {
      // 值已通过computed自动更新
    }

    // Excel导出相关函数
    const handleExportExcel = async (filename) => {
      try {
        const response = await exportOutputToExcel(filename, versionMode.value)
        // 处理blob响应
        const blob = new Blob([response.data], { 
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
        })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${filename.replace('.json', '')}.xlsx`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        ElMessage.success('导出成功')
      } catch (error) {
        ElMessage.error('导出失败: ' + (error.message || '未知错误'))
      }
    }

    // 筛选相关函数
    const handleFilter = async (filename) => {
      try {
        await ensureFileLoaded(filename)
        // 单值文件不支持筛选
        if (isSingleValue.value) {
          ElMessage.warning('单值文件不支持筛选')
          return
        }
        currentFilename.value = filename
        // 如果还没有保存原始数据，先保存
        if (!isFiltered.value) {
          originalFileData.value = JSON.parse(JSON.stringify(currentFileData.value))
        }
        // 初始化筛选表单
        filterForm.years = []
        filterForm.countries = []
        countrySearchText.value = ''
        filterDialogVisible.value = true
      } catch (error) {
        ElMessage.error(error.message || '文件尚未加载完成')
      }
    }

    const filterCountries = (query) => {
      countrySearchText.value = query
    }

    const confirmFilter = async () => {
      filtering.value = true
      try {
        const years = filterForm.years.length > 0 ? filterForm.years : null
        const countries = filterForm.countries.length > 0 ? filterForm.countries : null
        
        // 如果都没有选择，相当于清除筛选
        if (!years && !countries) {
          handleClearFilter()
          filterDialogVisible.value = false
          return
        }

        const response = await filterOutputFile(currentFilename.value, years, countries, versionMode.value)
        currentFileData.value = response.data || {}
        isFiltered.value = true
        ElMessage.success('筛选成功')
        filterDialogVisible.value = false

        // 重新布局表格
        nextTick(() => {
          setTimeout(() => {
            if (fixedTableRef.value && fixedTableRef.value.doLayout) {
              fixedTableRef.value.doLayout()
            }
            if (scrollTableRef.value && scrollTableRef.value.doLayout) {
              scrollTableRef.value.doLayout()
            }
          }, 300)
        })
      } catch (error) {
        ElMessage.error('筛选失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
      } finally {
        filtering.value = false
      }
    }

    const handleClearFilter = () => {
      if (originalFileData.value && Object.keys(originalFileData.value).length > 0) {
        currentFileData.value = JSON.parse(JSON.stringify(originalFileData.value))
        isFiltered.value = false
        originalFileData.value = {}
        ElMessage.success('已清除筛选')
        
        // 重新布局表格
        nextTick(() => {
          setTimeout(() => {
            if (fixedTableRef.value && fixedTableRef.value.doLayout) {
              fixedTableRef.value.doLayout()
            }
            if (scrollTableRef.value && scrollTableRef.value.doLayout) {
              scrollTableRef.value.doLayout()
            }
          }, 300)
        })
      } else {
        // 如果没有原始数据，重新加载文件
        loadFileData(currentFilename.value)
        isFiltered.value = false
        ElMessage.success('已清除筛选')
      }
    }

    const tableRowClassName = ({ rowIndex }) => {
      return rowIndex % 2 === 1 ? 'even-row' : ''
    }

    // 同步滚动：左侧表格滚动时同步右侧表格
    const handleFixedTableScroll = (e) => {
      if (isSyncingScroll || !scrollTableRef.value) return
      
      let fixedContainer = fixedTableLeftRef.value
      let scrollContainer = scrollTableRightRef.value
      
      // 如果是组件实例，获取 DOM 元素
      if (fixedContainer && !(fixedContainer instanceof Element)) {
        fixedContainer = fixedContainer.$el || fixedContainer.el || fixedContainer
      }
      if (scrollContainer && !(scrollContainer instanceof Element)) {
        scrollContainer = scrollContainer.$el || scrollContainer.el || scrollContainer
      }
      
      if (!fixedContainer || !scrollContainer || 
          !(fixedContainer instanceof Element) || 
          !(scrollContainer instanceof Element)) {
        return
      }
      
      isSyncingScroll = true
      nextTick(() => {
        const fixedWrapper = fixedContainer.querySelector('.el-table__body-wrapper')
        const scrollWrapper = scrollContainer.querySelector('.el-table__body-wrapper')
        
        if (fixedWrapper && scrollWrapper) {
          scrollWrapper.scrollTop = fixedWrapper.scrollTop
        }
        setTimeout(() => { isSyncingScroll = false }, 50)
      })
    }
    
    // 同步滚动：右侧表格滚动时同步左侧表格
    const handleScrollTableScroll = (e) => {
      if (isSyncingScroll || !fixedTableRef.value) return
      
      let fixedContainer = fixedTableLeftRef.value
      let scrollContainer = scrollTableRightRef.value
      
      // 如果是组件实例，获取 DOM 元素
      if (fixedContainer && !(fixedContainer instanceof Element)) {
        fixedContainer = fixedContainer.$el || fixedContainer.el || fixedContainer
      }
      if (scrollContainer && !(scrollContainer instanceof Element)) {
        scrollContainer = scrollContainer.$el || scrollContainer.el || scrollContainer
      }
      
      if (!fixedContainer || !scrollContainer || 
          !(fixedContainer instanceof Element) || 
          !(scrollContainer instanceof Element)) {
        return
      }
      
      isSyncingScroll = true
      nextTick(() => {
        const fixedWrapper = fixedContainer.querySelector('.el-table__body-wrapper')
        const scrollWrapper = scrollContainer.querySelector('.el-table__body-wrapper')
        
        if (fixedWrapper && scrollWrapper) {
          fixedWrapper.scrollTop = scrollWrapper.scrollTop
        }
        setTimeout(() => { isSyncingScroll = false }, 50)
      })
    }
    
    // 绑定滚动事件（允许在数据变化时重新绑定）
    let scrollEventsBound = false
    let bindAttempts = 0
    let currentFixedWrapper = null
    let currentScrollWrapper = null
    
    const resetScrollBinding = () => {
      // 清除之前绑定的事件监听器
      if (currentFixedWrapper && currentFixedWrapper._syncScrollHandler2) {
        currentFixedWrapper.removeEventListener('scroll', currentFixedWrapper._syncScrollHandler2)
        currentFixedWrapper._syncScrollHandler2 = null
      }
      if (currentScrollWrapper && currentScrollWrapper._syncScrollHandler1) {
        currentScrollWrapper.removeEventListener('scroll', currentScrollWrapper._syncScrollHandler1)
        currentScrollWrapper._syncScrollHandler1 = null
      }
      
      // 清除绑定标记
      if (currentFixedWrapper) {
        currentFixedWrapper.dataset.scrollBound = 'false'
      }
      if (currentScrollWrapper) {
        currentScrollWrapper.dataset.scrollBound = 'false'
      }
      
      scrollEventsBound = false
      bindAttempts = 0
      currentFixedWrapper = null
      currentScrollWrapper = null
    }
    
    const bindScrollEvents = () => {
      // 防止无限重试
      if (bindAttempts > 20) {
        console.error('滚动绑定失败，已重试20次')
        return
      }
      bindAttempts++
      
      // 优先使用 ref 查找当前活动的表格元素
      let fixedTableEl = null
      let scrollTableEl = null
      
      // 方法1: 从 ref 获取容器（注意：ref 可能是数组）
      let fixedContainer = fixedTableLeftRef.value
      let scrollContainer = scrollTableRightRef.value
      
      // 如果 ref 是数组，我们需要找到当前活动标签页对应的容器
      // Element Plus 使用 display 样式控制显示，而不是 is-active 类
      if (Array.isArray(fixedContainer)) {
        let activeTabPane = null
        const allTabPanes = document.querySelectorAll('.el-tab-pane')
        
        for (const pane of allTabPanes) {
          const computedStyle = window.getComputedStyle(pane)
          const isVisible = computedStyle.display !== 'none'
          const paneId = pane.id || ''
          const paneName = paneId.replace('pane-', '') || 
                         pane.getAttribute('aria-labelledby')?.replace('tab-', '') ||
                         pane.getAttribute('data-name') ||
                         pane.getAttribute('name')
          
          // 优先：既可见又匹配 activeTab
          if (isVisible && paneName === activeTab.value) {
            activeTabPane = pane
            break
          }
          // 其次：如果可见但 name 不匹配，也使用它（可能是活动标签）
          if (isVisible && !activeTabPane) {
            activeTabPane = pane
          }
        }
        
        if (activeTabPane) {
          const container = activeTabPane.querySelector('.fixed-table-left')
          if (container) {
            fixedContainer = container
          }
        }
      }
      
      if (Array.isArray(scrollContainer)) {
        let activeTabPane = null
        const allTabPanes = document.querySelectorAll('.el-tab-pane')
        
        for (const pane of allTabPanes) {
          const computedStyle = window.getComputedStyle(pane)
          const isVisible = computedStyle.display !== 'none'
          const paneId = pane.id || ''
          const paneName = paneId.replace('pane-', '') || 
                         pane.getAttribute('aria-labelledby')?.replace('tab-', '')
          
          if (isVisible && paneName === activeTab.value) {
            activeTabPane = pane
            break
          }
          if (isVisible && !activeTabPane) {
            activeTabPane = pane
          }
        }
        
        if (activeTabPane) {
          const container = activeTabPane.querySelector('.scroll-table-right')
          if (container) {
            scrollContainer = container
          }
        }
      }
      
      // 如果 ref 是 Vue 组件实例，获取其 $el
      if (fixedContainer && !(fixedContainer instanceof Element)) {
        if (fixedContainer.$el) {
          fixedContainer = fixedContainer.$el
        } else if (fixedContainer.el) {
          fixedContainer = fixedContainer.el
        }
      }
      if (scrollContainer && !(scrollContainer instanceof Element)) {
        if (scrollContainer.$el) {
          scrollContainer = scrollContainer.$el
        } else if (scrollContainer.el) {
          scrollContainer = scrollContainer.el
        }
      }
      
      // 从容器中查找表格
      if (fixedContainer instanceof Element) {
        fixedTableEl = fixedContainer.querySelector('.el-table')
      }
      
      if (scrollContainer instanceof Element) {
        scrollTableEl = scrollContainer.querySelector('.el-table')
      }
      
      // 方法2: 如果 ref 无效，尝试从组件实例的 $el 获取（但要注意可能是数组）
      if (!fixedTableEl && fixedTableRef.value) {
        let tableEl = null
        if (Array.isArray(fixedTableRef.value)) {
          // ref 是数组，需要通过 activeTab 找到对应的表格
          const allTabPanes = document.querySelectorAll('.el-tab-pane')
          for (const pane of allTabPanes) {
            const computedStyle = window.getComputedStyle(pane)
            const isVisible = computedStyle.display !== 'none'
            const paneId = pane.id || ''
            const paneName = paneId.replace('pane-', '') || 
                           pane.getAttribute('aria-labelledby')?.replace('tab-', '')
            
            if (isVisible && paneName === activeTab.value) {
              const activeFixedTable = pane.querySelector('.fixed-table-left .el-table')
              if (activeFixedTable) {
                tableEl = activeFixedTable
                break
              }
            }
          }
        } else {
          tableEl = fixedTableRef.value.$el || fixedTableRef.value.el
        }
        if (tableEl instanceof Element) {
          fixedTableEl = tableEl
        }
      }
      
      if (!scrollTableEl && scrollTableRef.value) {
        let tableEl = null
        if (Array.isArray(scrollTableRef.value)) {
          const allTabPanes = document.querySelectorAll('.el-tab-pane')
          for (const pane of allTabPanes) {
            const computedStyle = window.getComputedStyle(pane)
            const isVisible = computedStyle.display !== 'none'
            const paneId = pane.id || ''
            const paneName = paneId.replace('pane-', '') || 
                           pane.getAttribute('aria-labelledby')?.replace('tab-', '')
            
            if (isVisible && paneName === activeTab.value) {
              const activeScrollTable = pane.querySelector('.scroll-table-right .el-table')
              if (activeScrollTable) {
                tableEl = activeScrollTable
                break
              }
            }
          }
        } else {
          tableEl = scrollTableRef.value.$el || scrollTableRef.value.el
        }
        if (tableEl instanceof Element) {
          scrollTableEl = tableEl
        }
      }
      
      // 方法3: 如果还是找不到，使用全局查询，通过 display 样式查找活动的 tab-pane
      if (!fixedTableEl) {
        const allFixedTables = document.querySelectorAll('.fixed-table-left .el-table')
        // 通过 display 样式查找活动的 tab-pane（Element Plus 不使用 is-active 类）
        for (const table of allFixedTables) {
          const tabPane = table.closest('.el-tab-pane')
          if (tabPane) {
            const computedStyle = window.getComputedStyle(tabPane)
            const isVisible = computedStyle.display !== 'none'
            const paneId = tabPane.id || ''
            const paneName = paneId.replace('pane-', '') || 
                           tabPane.getAttribute('aria-labelledby')?.replace('tab-', '')
            
            // 优先：既可见又匹配 activeTab
            if (isVisible && paneName === activeTab.value) {
              fixedTableEl = table
              break
            }
            // 如果可见但 name 不匹配，作为后备
            if (isVisible && !fixedTableEl) {
              fixedTableEl = table
            }
          }
        }
      }
      
      if (!scrollTableEl) {
        const allScrollTables = document.querySelectorAll('.scroll-table-right .el-table')
        // 通过 display 样式查找活动的 tab-pane
        for (const table of allScrollTables) {
          const tabPane = table.closest('.el-tab-pane')
          if (tabPane) {
            const computedStyle = window.getComputedStyle(tabPane)
            const isVisible = computedStyle.display !== 'none'
            const paneId = tabPane.id || ''
            const paneName = paneId.replace('pane-', '') || 
                           tabPane.getAttribute('aria-labelledby')?.replace('tab-', '')
            
            // 优先：既可见又匹配 activeTab
            if (isVisible && paneName === activeTab.value) {
              scrollTableEl = table
              break
            }
            // 如果可见但 name 不匹配，作为后备
            if (isVisible && !scrollTableEl) {
              scrollTableEl = table
            }
          }
        }
      }
      
      if (!fixedTableEl || !scrollTableEl || 
          !(fixedTableEl instanceof Element) || 
          !(scrollTableEl instanceof Element)) {
        setTimeout(bindScrollEvents, 200)
        return
      }
      
      // 查找滚动容器 - 尝试多个可能的选择器
      // Element Plus 表格的滚动可能发生在不同的元素上
      const possibleSelectors = [
        '.el-table__body-wrapper',
        '.el-scrollbar__wrap',
        '.el-table__body',
        '.el-scrollbar__view'
      ]
      
      let fixedWrapper = null
      let scrollWrapper = null
      
      // 尝试找到真正可滚动的元素（scrollHeight > clientHeight）
      for (const selector of possibleSelectors) {
        const fixedCandidates = fixedTableEl.querySelectorAll(selector)
        const scrollCandidates = scrollTableEl.querySelectorAll(selector)
        
        // 找到第一个可滚动的元素
        for (const el of fixedCandidates) {
          if (el.scrollHeight > el.clientHeight) {
            fixedWrapper = el
            break
          }
        }
        
        for (const el of scrollCandidates) {
          if (el.scrollHeight > el.clientHeight) {
            scrollWrapper = el
            break
          }
        }
        
        if (fixedWrapper && scrollWrapper) break
      }
      
      // 如果还是找不到，使用第一个找到的元素（即使不可滚动）
      if (!fixedWrapper) {
        fixedWrapper = fixedTableEl.querySelector('.el-table__body-wrapper') ||
                      fixedTableEl.querySelector('.el-scrollbar__wrap')
      }
      
      if (!scrollWrapper) {
        scrollWrapper = scrollTableEl.querySelector('.el-table__body-wrapper') ||
                       scrollTableEl.querySelector('.el-scrollbar__wrap')
      }
      
      if (!fixedWrapper || !scrollWrapper) {
        setTimeout(bindScrollEvents, 200)
        return
      }
      
      // 检查是否应该跳过绑定
      const isSameElement = fixedWrapper === currentFixedWrapper && scrollWrapper === currentScrollWrapper
      const alreadyBound = fixedWrapper.dataset.scrollBound === 'true' || scrollWrapper.dataset.scrollBound === 'true'
      
      // 即使元素已经标记为绑定，但如果文件名不同，说明是切换了标签，需要重新绑定
      // 或者如果是不同的元素，也需要绑定
      if (isSameElement && alreadyBound) {
        scrollEventsBound = true
        return
      }
      
      // 如果是不同的元素，清除旧绑定
      if (!isSameElement && alreadyBound) {
        fixedWrapper.dataset.scrollBound = 'false'
        scrollWrapper.dataset.scrollBound = 'false'
      }
      
      // 如果之前绑定的是不同的元素，先清除旧绑定
      if (currentFixedWrapper && currentFixedWrapper !== fixedWrapper) {
        if (currentFixedWrapper._syncScrollHandler2) {
          currentFixedWrapper.removeEventListener('scroll', currentFixedWrapper._syncScrollHandler2)
        }
      }
      if (currentScrollWrapper && currentScrollWrapper !== scrollWrapper) {
        if (currentScrollWrapper._syncScrollHandler1) {
          currentScrollWrapper.removeEventListener('scroll', currentScrollWrapper._syncScrollHandler1)
        }
      }
      
      // 创建滚动处理函数
      const syncScrollRightToLeft = () => {
        if (!isSyncingScroll && fixedWrapper && scrollWrapper) {
          isSyncingScroll = true
          const targetScrollTop = scrollWrapper.scrollTop
          if (Math.abs(fixedWrapper.scrollTop - targetScrollTop) > 1) {
            fixedWrapper.scrollTop = targetScrollTop
          }
          requestAnimationFrame(() => {
            isSyncingScroll = false
          })
        }
      }
      
      const syncScrollLeftToRight = () => {
        if (!isSyncingScroll && fixedWrapper && scrollWrapper) {
          isSyncingScroll = true
          const targetScrollTop = fixedWrapper.scrollTop
          if (Math.abs(scrollWrapper.scrollTop - targetScrollTop) > 1) {
            scrollWrapper.scrollTop = targetScrollTop
          }
          requestAnimationFrame(() => {
            isSyncingScroll = false
          })
        }
      }
      
      // 保存处理器引用，以便后续移除
      fixedWrapper._syncScrollHandler2 = syncScrollLeftToRight
      scrollWrapper._syncScrollHandler1 = syncScrollRightToLeft
      
      // 保存当前绑定的元素引用
      currentFixedWrapper = fixedWrapper
      currentScrollWrapper = scrollWrapper
      
      // 绑定右侧滚动到左侧
      scrollWrapper.addEventListener('scroll', syncScrollRightToLeft, { passive: true })
      
      // 绑定左侧滚动到右侧
      fixedWrapper.addEventListener('scroll', syncScrollLeftToRight, { passive: true })
      
      // 标记为已绑定
      fixedWrapper.dataset.scrollBound = 'true'
      scrollWrapper.dataset.scrollBound = 'true'
      scrollEventsBound = true
      
      // 立即同步一次，确保初始位置一致
      if (scrollWrapper.scrollTop !== fixedWrapper.scrollTop) {
        fixedWrapper.scrollTop = scrollWrapper.scrollTop
      }
    }

    // 监听版本模式变化，切换版本时重新加载数据
    watch(versionMode, () => {
      // 重置状态
      activeTab.value = ''
      activeCategory.value = ''
      currentFileData.value = {}
      currentFilename.value = ''
      currentFileRevision.value = ''
      fileList.value = []
      // 重新加载文件列表
      loadFileList()
    })

    // 监听一级分类切换，自动选择第一个文件
    watch(activeCategory, (newCategory) => {
      if (newCategory) {
        const categoryFiles = getCategoryFiles(newCategory)
        
        // 如果当前 activeTab 不在该分类中，或者 activeTab 为空，选择该分类的第一个文件
        if (categoryFiles.length > 0) {
          if (!activeTab.value || !categoryFiles.includes(activeTab.value)) {
            activeTab.value = categoryFiles[0]
            loadFileData(categoryFiles[0])
          }
        }
      }
    })

    // 监听 activeTab 变化，切换标签时重新绑定
    let isInitialLoad = true
    watch(activeTab, () => {
      // 跳过初始化时的触发
      if (isInitialLoad) {
        isInitialLoad = false
        return
      }
      
      // 切换标签时，先重置绑定
      resetScrollBinding()
      bindAttempts = 0
      // 等待标签切换完成，DOM 更新后再绑定
      nextTick(() => {
        setTimeout(() => {
          if (fixedTableRef.value && scrollTableRef.value && tableData.value?.length > 0) {
            // 调用 doLayout 确保表格布局正确
            if (fixedTableRef.value.doLayout) {
              fixedTableRef.value.doLayout()
            }
            if (scrollTableRef.value.doLayout) {
              scrollTableRef.value.doLayout()
            }
            // 绑定滚动事件
            bindScrollEvents()
          }
        }, 500)
      })
    })
    
    // 监听 ref 和 tableData 变化，当它们就绪时绑定
    watch([fixedTableRef, scrollTableRef, tableData], () => {
      if (fixedTableRef.value && scrollTableRef.value && tableData.value?.length > 0) {
        // 如果还没有绑定，尝试绑定
        if (!scrollEventsBound) {
          nextTick(() => {
            setTimeout(() => {
              bindScrollEvents()
            }, 300)
          })
        }
      }
    }, { immediate: false, deep: false })

    onMounted(async () => {
      await loadFileList()
      // 懒加载：不根据 activeTab 自动加载数据
      // 等待表格渲染后再绑定和布局
      nextTick(() => {
        setTimeout(() => {
          // 调用 doLayout 重新计算表格布局
          if (fixedTableRef.value && fixedTableRef.value.doLayout) {
            fixedTableRef.value.doLayout()
          }
          if (scrollTableRef.value && scrollTableRef.value.doLayout) {
            scrollTableRef.value.doLayout()
          }
          // 然后绑定滚动事件
          bindScrollEvents()
          // mounted 之后，允许 activeTab watch 触发
          setTimeout(() => {
            isInitialLoad = false
          }, 500)
        }, 1000)
      })
    })

    return {
      fileList,
      activeTab,
        onTabClick,
      fixedTableLeftRef,
      scrollTableRightRef,
      fixedTableRef,
      scrollTableRef,
      handleFixedTableScroll,
      handleScrollTableScroll,
      tableData,
      countries,
      countryCount,
      loading,
      editingCell,
      isSingleValue,
      singleValue,
      handleRefresh,
      startCellEdit,
      saveCellEdit,
      handleSave,
      handleSaveSingleValue,
      handleSingleValueChange,
      handleExportExcel,
      getFileDescription,
      tableRowClassName,
      handleFilter,
      filterDialogVisible,
      filterForm,
      filtering,
      confirmFilter,
      handleClearFilter,
      filterCountries,
      availableYears,
      availableCountries,
      filteredCountryOptions,
      Refresh,
      Document,
      TrendCharts,
      DataAnalysis,
      Collection,
      InfoFilled,
      Download,
      Filter,
      FolderOpened,
      activeCategory,
      categoryOrder,
      getCategoryFiles,
      getCategoryFileCount,
      handleCategoryChange,
      handleCategoryTabChange
    }
  }
}
</script>

<style scoped>
/* 文件描述样式 */
.file-description {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  font-size: 14px;
  line-height: 1.6;
}

.file-description .el-icon {
  flex-shrink: 0;
}

.file-description span {
  flex: 1;
}
.output-results {
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 28px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #1a202c;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: #718096;
  font-weight: 500;
}

/* 主卡片 */
.main-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.main-card :deep(.el-card__header) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  padding: 24px 32px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.card-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
  line-height: 1.2;
}

.card-subtitle {
  font-size: 14px;
  color: #718096;
  margin: 4px 0 0 0;
}

.refresh-btn {
  width: 48px;
  height: 48px;
}

/* 层级结构容器 */
.category-container {
  padding: 0;
}

/* 一级分类标签页 */
.category-tabs {
  margin-bottom: 20px;
}

.category-tabs :deep(.el-tabs__header) {
  margin: 0;
  background: rgba(102, 126, 234, 0.03);
  border-radius: 12px;
  padding: 8px;
}

.category-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.category-tabs :deep(.el-tabs__item) {
  font-size: 16px;
  font-weight: 600;
  padding: 12px 24px;
  height: 56px;
  line-height: 32px;
  color: #4a5568;
  border-radius: 8px;
  margin-right: 8px;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  background: rgba(255, 255, 255, 0.8);
}

.category-tabs :deep(.el-tabs__item:hover) {
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  border-color: rgba(102, 126, 234, 0.2);
}

.category-tabs :deep(.el-tabs__item.is-active) {
  color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
  border-color: rgba(102, 126, 234, 0.4);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

.category-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.category-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-icon {
  font-size: 18px;
  color: #667eea;
}

.category-name {
  font-weight: 600;
}

.category-badge {
  margin-left: 4px;
}

/* 嵌套的标签页 */
.nested-tabs {
  padding: 20px 24px;
}

.nested-tabs :deep(.el-tabs__header) {
  margin: 0 0 20px 0;
  background: rgba(102, 126, 234, 0.03);
  border-radius: 8px;
  padding: 8px;
}

.nested-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.nested-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  padding: 8px 16px;
  height: 40px;
  line-height: 24px;
  color: #4a5568;
  border-radius: 6px;
  margin-right: 8px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.nested-tabs :deep(.el-tabs__item:hover) {
  color: #667eea;
  background: rgba(102, 126, 234, 0.08);
}

.nested-tabs :deep(.el-tabs__item.is-active) {
  color: #667eea;
  font-weight: 600;
  background: rgba(102, 126, 234, 0.12);
  border-color: rgba(102, 126, 234, 0.3);
}

.nested-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

/* 单值显示 */
.single-value-display {
  padding: 40px 0;
  display: flex;
  justify-content: center;
}

.single-value-card {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-radius: 20px;
  padding: 48px;
  max-width: 600px;
  width: 100%;
  border: 1px solid rgba(102, 126, 234, 0.2);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.1);
}

.single-value-header {
  margin-bottom: 32px;
}

.function-name {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 700;
  color: #1a202c;
}

.single-value-content {
  text-align: center;
}

.value-display {
  margin-bottom: 32px;
}

.value-label {
  font-size: 14px;
  color: #718096;
  margin-bottom: 16px;
  font-weight: 500;
}

.value-input {
  width: 100%;
}

.value-input :deep(.el-input__inner) {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  height: 80px;
  color: #667eea;
}

.single-value-actions {
  text-align: center;
}

/* 工具栏 */
.toolbar {
  margin: 32px 0 24px 0;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.tool-btn {
  border-radius: 10px;
  font-weight: 600;
  padding: 12px 24px;
  transition: all 0.3s ease;
}

.tool-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

.save-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

/* 表格容器 */
.table-container {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

/* 双表格布局：左侧固定 + 右侧滚动 */
.split-table-wrapper {
  display: flex;
  position: relative;
}

.fixed-table-left {
  flex-shrink: 0;
  width: 120px;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  background: #ffffff;
  z-index: 10;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.scroll-table-right {
  flex: 1;
  overflow-x: auto;
  background: #ffffff;
}

/* 隐藏右侧表格的左侧边框，避免重复 */
.scroll-table :deep(.el-table) {
  border-left: none;
}

/* 确保左侧固定表格的每一行都有背景色 */
.fixed-table :deep(.el-table__body tr),
.fixed-table :deep(.el-table__body td) {
  background-color: #ffffff !important;
}

.fixed-table :deep(.el-table__body tr.even-row),
.fixed-table :deep(.el-table__body tr.even-row td) {
  background-color: rgba(102, 126, 234, 0.02) !important;
}

.modern-table {
  border-radius: 12px;
}

.modern-table :deep(.el-table__header-wrapper) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
}

.modern-table :deep(.el-table__header th) {
  background: transparent;
  color: #1a202c;
  font-weight: 600;
  font-size: 14px;
  padding: 16px 0;
  border-bottom: 2px solid rgba(102, 126, 234, 0.2);
}

.modern-table :deep(.el-table__body tr.even-row) {
  background: rgba(102, 126, 234, 0.02);
}

.modern-table :deep(.el-table__body tr:hover) {
  background: rgba(102, 126, 234, 0.05);
}

.modern-table :deep(.el-table__row) {
  transition: all 0.2s ease;
}

.year-cell, .data-cell {
  padding: 8px 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.editable-cell {
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  min-height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.editable-cell:hover {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

/* 对话框 */
.modern-dialog :deep(.el-dialog) {
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 28px 32px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: 20px;
  font-weight: 700;
  color: #1a202c;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 28px 32px;
}

.modern-dialog :deep(.el-dialog__footer) {
  padding: 20px 32px 28px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.file-content {
  padding: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
  
  .toolbar {
    flex-direction: column;
  }
  
  .tool-btn {
    width: 100%;
  }
  
  .single-value-card {
    padding: 32px 24px;
  }
}

/* 筛选相关样式 */
.filter-tip {
  margin-top: 8px;
}

.filter-tip .el-text {
  font-size: 12px;
}
</style>
