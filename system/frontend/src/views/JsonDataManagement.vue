<template>
  <div class="json-data-management">
    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
          <el-icon :size="28"><FolderOpened /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ fileList.length }}</div>
          <div class="stat-label">数据文件</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
          <el-icon :size="28"><Calendar /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ tableData.length }}</div>
          <div class="stat-label">数据年份</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
          <el-icon :size="28"><Location /></el-icon>
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
            <el-icon class="header-icon"><FolderOpened /></el-icon>
            <div>
              <h2 class="card-title">数据管理</h2>
              <p class="card-subtitle">管理 jsondata 文件夹中的数据文件</p>
            </div>
          </div>
          <div class="header-right">
            <!-- 警告信息 -->
            <div 
              v-if="warningInfo.hasWarning" 
              class="warning-info"
              @click="warningDialogVisible = true"
            >
              <el-icon class="warning-icon"><WarningFilled /></el-icon>
              <span class="warning-text">数据不一致警告</span>
            </div>
            <div 
              v-else 
              class="warning-info success"
            >
              <el-icon class="warning-icon"><CircleCheckFilled /></el-icon>
              <span class="warning-text">当前无警告信息</span>
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
        </div>
      </template>
      <!-- 文件列表 -->
      <el-tabs v-model="activeTab" @tab-click="onTabClick" class="modern-tabs" v-if="fileList.length > 0">
        <el-tab-pane
          v-for="file in fileList"
          :key="file.filename"
          :name="file.filename"
        >
          <template #label>
            <el-tooltip 
              :content="getFileDescription(file.filename) || file.filename" 
              placement="top"
              :disabled="!getFileDescription(file.filename)"
            >
              <span>{{ file.filename }}</span>
            </el-tooltip>
          </template>
          
          <div class="file-content">
            <!-- 显示文件描述 -->
            <div v-if="getFileDescription(activeTab)" class="file-description">
              <el-icon :size="18"><InfoFilled /></el-icon>
              <span>{{ getFileDescription(activeTab) }}</span>
            </div>
            <div class="toolbar">
              <el-button 
                type="success" 
                size="large"
                @click="handleAddYear(file.filename)" 
                :icon="Plus"
                class="tool-btn"
              >
                添加年份
              </el-button>
              <el-button 
                type="success" 
                size="large"
                @click="handleAddCountry(file.filename)" 
                :icon="Plus"
                class="tool-btn"
              >
                添加国家
              </el-button>
              <el-button 
                type="danger" 
                size="large"
                @click="handleDeleteCountry(file.filename)" 
                :icon="Delete"
                class="tool-btn"
              >
                删除国家
              </el-button>
              <el-button 
                type="warning" 
                size="large"
                @click="handleImportExcel(file.filename)" 
                :icon="Upload"
                class="tool-btn"
              >
                导入Excel
              </el-button>
              <el-button 
                type="primary" 
                size="large"
                @click="handleSave(file.filename)" 
                :icon="Document"
                class="tool-btn save-btn"
              >
                保存修改
              </el-button>
              <el-button 
                type="success" 
                size="large"
                @click="handleExportExcel(file.filename)" 
                :icon="Download"
                class="tool-btn"
              >
                导出Excel
              </el-button>
              <el-button 
                type="info" 
                size="large"
                @click="handleFilter(file.filename)" 
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
                      width="140"
                      align="center"
                    >
                      <template #default="scope">
                        <div class="data-cell">
                          <el-input-number
                            v-if="editingCell === `${scope.row.year}_${country}`"
                            v-model="scope.row[country]"
                            :precision="2"
                            @blur="saveCellEdit(scope.row, country)"
                            @keyup.enter="saveCellEdit(scope.row, country)"
                            size="small"
                            :controls="false"
                          />
                          <div v-else @click="startCellEdit(`${scope.row.year}_${country}`)" class="editable-cell">
                            {{ scope.row[country] !== null && scope.row[country] !== undefined 
                              ? Number(scope.row[country]).toLocaleString() 
                              : '—' }}
                          </div>
                        </div>
                      </template>
                    </el-table-column>
                    
                    <el-table-column label="操作" width="140" align="center">
                      <template #default="scope">
                        <el-button
                          type="danger"
                          size="small"
                          @click="handleDeleteYear(file.filename, scope.row.year)"
                          :icon="Delete"
                          circle
                        />
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 添加年份对话框 -->
    <el-dialog 
      v-model="addYearDialogVisible" 
      title="添加年份" 
      width="500px"
      class="modern-dialog"
    >
      <el-form :model="addYearForm" label-width="100px" label-position="top">
        <el-form-item label="年份">
          <el-input 
            v-model="addYearForm.year" 
            placeholder="例如：2025" 
            size="large"
          />
        </el-form-item>
        <el-alert
          title="提示"
          type="info"
          :closable="false"
          style="margin-top: 16px"
        >
          <template #default>
            新添加的年份数据将与<strong>最后一年</strong>的数据相同
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="addYearDialogVisible = false" size="large">取消</el-button>
        <el-button type="primary" @click="confirmAddYear" size="large">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加国家对话框 -->
    <el-dialog 
      v-model="addCountryDialogVisible" 
      title="添加国家" 
      width="500px"
      class="modern-dialog"
    >
      <el-form :model="addCountryForm" label-width="100px" label-position="top">
        <el-form-item label="国家名称">
          <el-input 
            v-model="addCountryForm.country" 
            placeholder="例如：France" 
            size="large"
          />
        </el-form-item>
        <el-form-item label="初始值">
          <el-input-number 
            v-model="addCountryForm.value" 
            :precision="2" 
            size="large"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addCountryDialogVisible = false" size="large">取消</el-button>
        <el-button type="primary" @click="confirmAddCountry" size="large">确定</el-button>
      </template>
    </el-dialog>

    <!-- 删除国家对话框 -->
    <el-dialog 
      v-model="deleteCountryDialogVisible" 
      title="删除国家" 
      width="500px"
      class="modern-dialog"
    >
      <el-form label-width="100px" label-position="top">
        <el-form-item label="选择要删除的国家">
          <el-select 
            v-model="deleteCountryForm.country" 
            placeholder="请选择国家"
            size="large"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="country in countries"
              :key="country"
              :label="country"
              :value="country"
            />
          </el-select>
        </el-form-item>
        <el-alert
          title="警告"
          type="warning"
          :closable="false"
          style="margin-top: 16px"
        >
          <template #default>
            删除操作将移除该国家在<strong>所有年份</strong>中的数据，此操作不可恢复！
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="deleteCountryDialogVisible = false" size="large">取消</el-button>
        <el-button type="danger" @click="confirmDeleteCountry" size="large">确定删除</el-button>
      </template>
    </el-dialog>

    <!-- 警告详情对话框 -->
    <el-dialog 
      v-model="warningDialogVisible" 
      title="数据一致性警告详情" 
      width="700px"
      class="modern-dialog"
    >
      <div class="warning-details">
        <div v-for="(issues, filename) in warningInfo.details" :key="filename" class="warning-file">
          <div class="warning-file-header">
            <el-icon class="warning-file-icon"><Document /></el-icon>
            <strong>{{ filename }}</strong>
          </div>
          <ul class="warning-issues">
            <li v-for="(issue, index) in issues" :key="index" class="warning-issue">
              {{ issue }}
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="warningDialogVisible = false" size="large">确定</el-button>
      </template>
    </el-dialog>

    <!-- Excel导入对话框 -->
    <el-dialog
      v-model="importExcelDialogVisible"
      title="导入Excel数据"
      width="80%"
      :close-on-click-modal="false"
      class="modern-dialog"
    >
      <div class="import-excel-content">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :on-change="handleFileChange"
          :file-list="excelFileList"
          accept=".xlsx,.xls"
          drag
          class="excel-upload"
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">
            将Excel文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              仅支持 .xlsx 或 .xls 格式，第一列必须是"年份"列
            </div>
          </template>
        </el-upload>

        <!-- Excel预览提示 -->
        <div v-if="selectedFile" class="excel-preview">
          <el-alert
            title="文件已选择"
            :description="`文件名: ${selectedFile.name}`"
            type="info"
            :closable="false"
            show-icon
          />
        </div>

        <!-- 导入结果 -->
        <div v-if="importResult" class="import-result">
          <el-alert
            :title="importResult.status === 'success' ? '导入成功' : '导入失败'"
            :type="importResult.status === 'success' ? 'success' : 'error'"
            :description="importResult.message"
            show-icon
            :closable="false"
          />
          <div v-if="importResult.status === 'success' && importResult.added_years && importResult.added_years.length > 0" class="result-details">
            <p><strong>新增年份：</strong>{{ importResult.added_years.join(', ') }}</p>
          </div>
          <div v-if="importResult.status === 'success' && importResult.added_countries && importResult.added_countries.length > 0" class="result-details">
            <p><strong>新增国家：</strong>{{ importResult.added_countries.join(', ') }}</p>
          </div>
          <div v-if="importResult.status === 'success' && importResult.updated_cells > 0" class="result-details">
            <p><strong>更新单元格：</strong>{{ importResult.updated_cells }} 个</p>
          </div>
          <div v-if="importResult.errors && importResult.errors.length > 0" class="result-details">
            <p><strong>错误信息：</strong></p>
            <ul>
              <li v-for="(error, index) in importResult.errors" :key="index">{{ error }}</li>
            </ul>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="handleCancelImport" size="large">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleConfirmImport" 
          :loading="importing"
          :disabled="!selectedFile"
          size="large"
        >
          {{ importing ? '导入中...' : '确认导入' }}
        </el-button>
      </template>
    </el-dialog>

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
import { Refresh, Plus, Document, Delete, FolderOpened, Calendar, Location, InfoFilled, WarningFilled, CircleCheckFilled, Upload, Download, Filter } from '@element-plus/icons-vue'
import { listJsonDataFiles, getJsonDataFile, updateJsonDataFile, addJsonDataData, deleteJsonDataData, importExcelData, exportJsonDataToExcel, filterJsonDataFile } from '../api/jsondata'

export default {
  name: 'JsonDataManagement',
  setup() {
    // 注入版本模式
    const versionMode = inject('versionMode', ref('global'))
    // 文件顺序和描述映射
    const fileOrderAndDescription = {
      'total.json': '每个地理单位按照年份的总发文量数据',
      'world_total.json': '全球层面的数据，包括年份总发文量、OA发文量、撤稿量、前1%科学家数量',
      'OA.json': '每个地理单位按照年份的OA发文量数据',
      'cooperation.json': '每个地理单位按照年份的合作发文量数据',
      'retraction.json': '每个地理单位按照年份的撤稿数据',
      'scientist.json': '每个地理单位按照年份的前1%科学家数量',
      'FWCI.json': '每个地理单位按照年份的领域加权引用影响数据',
      'OP.json': '每个地区的开放政策的指标数据',
      'F2.json': '数据的信息质量，已经除以4放入数据表',
      'F3.json': '数据的完整性，基于撤回率计算',
      'alpha_F.json': '财务可持续性数据',
      'alpha_I.json': '工具/平台可持续性数据',
      'alpha_L.json': '法律可持续性数据'
    }
    
    // 文件顺序列表
    const fileOrder = [
      'total.json',
      'world_total.json',
      'OA.json',
      'cooperation.json',
      'retraction.json',
      'scientist.json',
      'FWCI.json',
      'OP.json',
      'F2.json',
      'F3.json',
      'alpha_F.json',
      'alpha_I.json',
      'alpha_L.json'
    ]
    
    const fileList = ref([])
    const activeTab = ref('')
    const currentFileData = ref({})
    const loading = ref(false)
    const countryCount = ref(0) // 国家/地区/组织数量
    const editingCell = ref(null)
    const addYearDialogVisible = ref(false)
    const addCountryDialogVisible = ref(false)
    const deleteCountryDialogVisible = ref(false)
    const importExcelDialogVisible = ref(false)
    const currentFilename = ref('')
    const currentFileRevision = ref('')
    const uploadRef = ref(null)
    const selectedFile = ref(null)
    const excelFileList = ref([])
    const excelPreview = ref([])
    const excelHeaders = ref([])
    const excelPreviewTotalRows = ref(0)
    const importResult = ref(null)
    const importing = ref(false)
    const fixedTableLeftRef = ref(null)
    const scrollTableRightRef = ref(null)
    const fixedTableRef = ref(null)
    const scrollTableRef = ref(null)
    let isSyncingScroll = false
    const warningDialogVisible = ref(false)
    const warningInfo = ref({
      hasWarning: false,
      details: {}
    })
    
    // 存储所有文件的数据（用于一致性检查）
    const allFilesData = ref({})
    
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
    
    const addYearForm = reactive({
      year: ''
    })
    
    const addCountryForm = reactive({
      country: '',
      value: 0
    })
    
    const deleteCountryForm = reactive({
      country: ''
    })

    const tableData = computed(() => {
      if (!currentFileData.value || typeof currentFileData.value !== 'object') {
        return []
      }
      
      if ('value' in currentFileData.value && Object.keys(currentFileData.value).length === 1) {
        return []
      }
      
      const years = Object.keys(currentFileData.value).sort()
      return years.map(year => {
        const row = { year, ...currentFileData.value[year] }
        return row
      })
    })

    const countries = computed(() => {
      if (!currentFileData.value || typeof currentFileData.value !== 'object') {
        return []
      }
      
      if ('value' in currentFileData.value && Object.keys(currentFileData.value).length === 1) {
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
    
    // 需要排除的文件列表（后端存在但前端不显示）
    const excludedFiles = ['weight.json']
    
    // 对文件列表进行排序
    const sortFileList = (files) => {
      // 先过滤掉需要排除的文件
      const filteredFiles = files.filter(file => !excludedFiles.includes(file.filename))
      
      const fileMap = new Map(filteredFiles.map(file => [file.filename, file]))
      const sortedFiles = []
      
      // 按照预定义顺序添加
      for (const filename of fileOrder) {
        if (fileMap.has(filename)) {
          sortedFiles.push(fileMap.get(filename))
          fileMap.delete(filename)
        }
      }
      
      // 添加其他未在顺序列表中的文件（按文件名排序）
      const remainingFiles = Array.from(fileMap.values()).sort((a, b) => 
        a.filename.localeCompare(b.filename)
      )
      sortedFiles.push(...remainingFiles)
      
      return sortedFiles
    }

    // 加载国家数量（从 OA.json 文件）
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
        const response = await listJsonDataFiles(versionMode.value)
        const files = response.files || []
        // 按照预定义顺序排序
        fileList.value = sortFileList(files)
        // 加载国家数量
        await loadCountryCount()
        // 自动加载第一个文件（total.json）的数据
        if (fileList.value.length > 0 && !activeTab.value) {
          const firstFile = fileList.value[0].filename
          activeTab.value = firstFile
          // 自动加载第一个文件的数据
          await loadFileData(firstFile)
        }
      } catch (error) {
        ElMessage.error('加载文件列表失败')
      }
    }

    const loadFileData = async (filename) => {
      if (!filename) return
      
      loading.value = true
      try {
        const response = await getJsonDataFile(filename, versionMode.value)
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

    const handleRefresh = () => {
      allFilesData.value = {}
      loadFileList()
      if (activeTab.value) {
        loadFileData(activeTab.value)
      }
    }

    // 检查数据一致性
    const checkDataConsistency = async () => {
      const details = {}
      let hasWarning = false
      
      // 需要排除的文件（不参与一致性检测）
      const excludedFromCheck = ['world_total.json', 'weight.json']
      
      // 如果没有文件列表，先加载
      if (fileList.value.length === 0) {
        return
      }
      
      // 过滤掉需要排除的文件
      const filesToCheck = fileList.value.filter(file => !excludedFromCheck.includes(file.filename))
      
      // 收集所有文件的数据（如果还没有加载）
      for (const file of filesToCheck) {
        if (!allFilesData.value[file.filename]) {
          try {
            const response = await getJsonDataFile(file.filename, versionMode.value)
            allFilesData.value[file.filename] = response.data || {}
          } catch (error) {
            // 忽略加载失败的文件
            continue
          }
        }
      }
      
      // 统计所有文件的年份和地区集合
      const allYears = new Set()
      const allCountries = new Set()
      const fileYears = {}
      const fileCountries = {}
      
      for (const file of filesToCheck) {
        const data = allFilesData.value[file.filename]
        if (!data || typeof data !== 'object') continue
        
        // 跳过单值文件（如果有value字段且只有一个键）
        if ('value' in data && Object.keys(data).length === 1) continue
        
        const years = new Set(Object.keys(data))
        years.forEach(year => allYears.add(year))
        fileYears[file.filename] = years
        
        // 获取第一个年份的地区列表（作为基准）
        const firstYear = Array.from(years)[0]
        if (firstYear && data[firstYear]) {
          const countries = new Set(Object.keys(data[firstYear]).filter(k => k !== 'year'))
          countries.forEach(country => allCountries.add(country))
          fileCountries[file.filename] = countries
        }
      }
      
      // 检查每个文件
      for (const file of filesToCheck) {
        const data = allFilesData.value[file.filename]
        if (!data || typeof data !== 'object') continue
        
        // 跳过单值文件
        if ('value' in data && Object.keys(data).length === 1) continue
        
        const fileIssues = []
        const years = fileYears[file.filename] || new Set()
        const countries = fileCountries[file.filename] || new Set()
        
        // 检查年份一致性
        for (const year of allYears) {
          if (!years.has(year)) {
            fileIssues.push(`缺少年份：${year}`)
          }
        }
        
        // 检查每个年份的地区一致性
        for (const year of years) {
          if (!data[year]) continue
          
          const yearCountries = new Set(Object.keys(data[year]).filter(k => k !== 'year'))
          
          for (const country of allCountries) {
            if (!yearCountries.has(country)) {
              fileIssues.push(`${year}年缺少地区：${country}`)
            }
          }
        }
        
        if (fileIssues.length > 0) {
          details[file.filename] = fileIssues
          hasWarning = true
        }
      }
      
      warningInfo.value = {
        hasWarning,
        details
      }
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
        const response = await updateJsonDataFile(
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

    const handleAddYear = async (filename) => {
      try {
        await ensureFileLoaded(filename)
        currentFilename.value = filename
        addYearForm.year = ''
        addYearDialogVisible.value = true
      } catch (error) {
        ElMessage.error(error.message || '文件尚未加载完成')
      }
    }

    const confirmAddYear = async () => {
      if (!addYearForm.year) {
        ElMessage.warning('请输入年份')
        return
      }
      
      // 检查年份是否已存在
      if (currentFileData.value && currentFileData.value[addYearForm.year]) {
        ElMessage.warning('该年份已存在')
        return
      }
      
      try {
        // 获取所有年份并排序，找到最后一年
        const years = Object.keys(currentFileData.value || {}).sort()
        let value = {}
        
        if (years.length > 0) {
          // 复制最后一年的数据
          const lastYear = years[years.length - 1]
          value = { ...currentFileData.value[lastYear] }
        }
        
        const response = await addJsonDataData(
          currentFilename.value,
          addYearForm.year,
          null,
          value,
          currentFileRevision.value,
          versionMode.value
        )
        currentFileRevision.value = response.revision || currentFileRevision.value
        ElMessage.success('添加成功')
        addYearDialogVisible.value = false
        loadFileData(currentFilename.value)
      } catch (error) {
        ElMessage.error('添加失败: ' + (error.message || '未知错误'))
      }
    }

    const handleAddCountry = async (filename) => {
      try {
        await ensureFileLoaded(filename)
        currentFilename.value = filename
        addCountryForm.country = ''
        addCountryForm.value = 0
        addCountryDialogVisible.value = true
      } catch (error) {
        ElMessage.error(error.message || '文件尚未加载完成')
      }
    }

    const confirmAddCountry = async () => {
      if (!addCountryForm.country) {
        ElMessage.warning('请输入国家名称')
        return
      }
      
      try {
        const response = await addJsonDataData(
          currentFilename.value,
          null,
          addCountryForm.country,
          addCountryForm.value,
          currentFileRevision.value,
          versionMode.value
        )
        currentFileRevision.value = response.revision || currentFileRevision.value
        ElMessage.success('添加成功')
        addCountryDialogVisible.value = false
        loadFileData(currentFilename.value)
      } catch (error) {
        ElMessage.error('添加失败')
      }
    }

    const handleDeleteYear = async (filename, year) => {
      try {
        await ensureFileLoaded(filename)
        await ElMessageBox.confirm(`确定要删除 ${year} 年的数据吗？`, '删除确认', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const response = await deleteJsonDataData(
          filename,
          year,
          null,
          currentFileRevision.value,
          versionMode.value
        )
        currentFileRevision.value = response.revision || currentFileRevision.value
        ElMessage.success('删除成功')
        loadFileData(filename)
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
        }
      }
    }

    const handleDeleteCountry = async (filename) => {
      try {
        await ensureFileLoaded(filename)
        if (countries.value.length === 0) {
          ElMessage.warning('当前文件没有国家数据')
          return
        }
        currentFilename.value = filename
        deleteCountryForm.country = ''
        deleteCountryDialogVisible.value = true
      } catch (error) {
        ElMessage.error(error.message || '文件尚未加载完成')
      }
    }

    const confirmDeleteCountry = async () => {
      if (!deleteCountryForm.country) {
        ElMessage.warning('请选择要删除的国家')
        return
      }
      
      try {
        await ElMessageBox.confirm(
          `确定要删除国家 "${deleteCountryForm.country}" 在所有年份中的数据吗？此操作不可恢复！`,
          '删除确认',
          {
            confirmButtonText: '确定删除',
            cancelButtonText: '取消',
            type: 'warning',
            dangerouslyUseHTMLString: false
          }
        )
        
        const response = await deleteJsonDataData(
          currentFilename.value,
          null,
          deleteCountryForm.country,
          currentFileRevision.value,
          versionMode.value
        )
        currentFileRevision.value = response.revision || currentFileRevision.value
        ElMessage.success('删除成功')
        deleteCountryDialogVisible.value = false
        // 重新加载文件数据
        loadFileData(currentFilename.value)
        // 重新检查数据一致性
        checkDataConsistency()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('删除失败: ' + (error.message || '未知错误'))
        }
      }
    }

    // Excel导入相关函数
    const handleImportExcel = async (filename) => {
      try {
        await ensureFileLoaded(filename)
        currentFilename.value = filename
        selectedFile.value = null
        excelPreview.value = []
        excelHeaders.value = []
        excelPreviewTotalRows.value = 0
        importResult.value = null
        excelFileList.value = []
        if (uploadRef.value) {
          uploadRef.value.clearFiles()
        }
        importExcelDialogVisible.value = true
      } catch (error) {
        ElMessage.error(error.message || '文件尚未加载完成')
      }
    }

    const handleFileChange = (file) => {
      selectedFile.value = file.raw
      excelPreview.value = []
      excelHeaders.value = []
      excelPreviewTotalRows.value = 0
      importResult.value = null
      // 文件选择后，预览会在确认导入后由后端返回的数据显示
    }

    const handleCancelImport = () => {
      importExcelDialogVisible.value = false
      selectedFile.value = null
      excelPreview.value = []
      excelHeaders.value = []
      excelPreviewTotalRows.value = 0
      importResult.value = null
      excelFileList.value = []
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
    }

    const handleConfirmImport = async () => {
      if (!selectedFile.value) {
        ElMessage.warning('请先选择Excel文件')
        return
      }

      importing.value = true
      importResult.value = null

      try {
        const response = await importExcelData(currentFilename.value, selectedFile.value, versionMode.value)
        importResult.value = response
        currentFileRevision.value = response.revision || currentFileRevision.value

        if (response.status === 'success') {
          ElMessage.success('导入成功')
          // 延迟关闭对话框，让用户查看结果
          setTimeout(() => {
            // 重新加载文件数据
            loadFileData(currentFilename.value)
            // 重新检查数据一致性
            checkDataConsistency()
            // 关闭对话框
            setTimeout(() => {
              handleCancelImport()
            }, 2000)
          }, 1500)
        } else {
          ElMessage.error(response.message || '导入失败')
        }
      } catch (error) {
        importResult.value = {
          status: 'error',
          message: error.response?.data?.detail || error.message || '导入失败',
          errors: []
        }
        ElMessage.error(importResult.value.message)
      } finally {
        importing.value = false
      }
    }

    // Excel导出相关函数
    const handleExportExcel = async (filename) => {
      try {
        const response = await exportJsonDataToExcel(filename, versionMode.value)
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

        const response = await filterJsonDataFile(currentFilename.value, years, countries, versionMode.value)
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
      currentFileData.value = {}
      currentFilename.value = ''
      currentFileRevision.value = ''
      fileList.value = []
      // 重新加载文件列表
      loadFileList()
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
      // 懒加载：不自动根据 activeTab 加载数据，等待用户点击 tab
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
      addYearDialogVisible,
      addCountryDialogVisible,
      deleteCountryDialogVisible,
      importExcelDialogVisible,
      addYearForm,
      addCountryForm,
      deleteCountryForm,
      handleRefresh,
      startCellEdit,
      saveCellEdit,
      handleSave,
      handleAddYear,
      handleAddCountry,
      confirmAddYear,
      confirmAddCountry,
      handleDeleteYear,
      handleDeleteCountry,
      confirmDeleteCountry,
      handleImportExcel,
      handleFileChange,
      handleCancelImport,
      handleConfirmImport,
      handleExportExcel,
      uploadRef,
      selectedFile,
      excelFileList,
      excelPreview,
      excelHeaders,
      excelPreviewTotalRows,
      importResult,
      importing,
      tableRowClassName,
      getFileDescription,
      checkDataConsistency,
      warningInfo,
      warningDialogVisible,
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
      Plus,
      Document,
      Delete,
      FolderOpened,
      Calendar,
      Location,
      InfoFilled,
      WarningFilled,
      CircleCheckFilled,
      Upload,
      Download,
      Filter
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
.json-data-management {
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

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.warning-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  background: rgba(245, 101, 101, 0.1);
  border: 1px solid rgba(245, 101, 101, 0.3);
  color: #f56565;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
}

.warning-info:hover {
  background: rgba(245, 101, 101, 0.15);
  transform: translateY(-1px);
}

.warning-info.success {
  background: rgba(72, 187, 120, 0.1);
  border: 1px solid rgba(72, 187, 120, 0.3);
  color: #48bb78;
  cursor: default;
}

.warning-info.success:hover {
  background: rgba(72, 187, 120, 0.15);
  transform: none;
}

.warning-icon {
  font-size: 18px;
}

.warning-text {
  font-weight: 500;
}

.warning-details {
  max-height: 500px;
  overflow-y: auto;
}

.warning-file {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(245, 101, 101, 0.05);
  border-radius: 8px;
  border-left: 3px solid #f56565;
}

.warning-file-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 16px;
  color: #1a202c;
}

.warning-file-icon {
  color: #f56565;
  font-size: 20px;
}

.warning-issues {
  margin: 0;
  padding-left: 28px;
  list-style: disc;
}

.warning-issue {
  margin: 8px 0;
  color: #4a5568;
  font-size: 14px;
  line-height: 1.6;
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

/* 标签页 */
.modern-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 32px;
  background: rgba(102, 126, 234, 0.03);
}

.modern-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: rgba(0, 0, 0, 0.06);
}

.modern-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
  padding: 0 24px;
  height: 56px;
  line-height: 56px;
  color: #4a5568;
  transition: all 0.3s ease;
}

.modern-tabs :deep(.el-tabs__item:hover) {
  color: #667eea;
}

.modern-tabs :deep(.el-tabs__item.is-active) {
  color: #667eea;
  font-weight: 600;
}

.modern-tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  height: 3px;
  border-radius: 2px 2px 0 0;
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
}

/* Excel导入相关样式 */
.import-excel-content {
  padding: 20px 0;
}

.excel-upload {
  margin-bottom: 30px;
}

.excel-preview {
  margin-top: 30px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.excel-preview h3 {
  margin: 0 0 16px 0;
  color: #1a202c;
  font-size: 16px;
  font-weight: 600;
}

.preview-info {
  margin-top: 12px;
  color: #718096;
  font-size: 14px;
}

.import-result {
  margin-top: 30px;
}

.result-details {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
}

.result-details p {
  margin: 8px 0;
  color: #4a5568;
}

.result-details ul {
  margin: 8px 0 0 0;
  padding-left: 24px;
  color: #e53e3e;
}

.result-details li {
  margin: 4px 0;
}

/* 筛选相关样式 */
.filter-tip {
  margin-top: 8px;
}

.filter-tip .el-text {
  font-size: 12px;
}
</style>
