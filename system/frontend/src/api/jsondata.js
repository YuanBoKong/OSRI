import request from './request'

// 根据版本模式获取基础路径
const getBasePath = (versionMode = 'global') => {
  const basePaths = {
    global: '/jsondata',
    global_plus: '/jsondata_global_plus',
    aggregation: '/jsondata_aggregation'
  }
  return basePaths[versionMode] || basePaths.global
}

// 列出所有jsondata文件
export function listJsonDataFiles(versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/files`,
    method: 'get'
  })
}

// 读取jsondata文件
export function getJsonDataFile(filename, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}`,
    method: 'get'
  })
}

// 更新jsondata文件
export function updateJsonDataFile(filename, data, expectedRevision = null, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}`,
    method: 'put',
    data: {
      data,
      expected_revision: expectedRevision
    }
  })
}

// 添加数据（年份或国家）
export function addJsonDataData(filename, year, country, value, expectedRevision = null, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}/add`,
    method: 'post',
    data: {
      year,
      country,
      value,
      expected_revision: expectedRevision
    }
  })
}

// 删除数据（年份或国家）
export function deleteJsonDataData(filename, year, country, expectedRevision = null, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}/delete`,
    method: 'delete',
    data: {
      year: year || null,
      country: country || null,
      expected_revision: expectedRevision
    }
  })
}

// 从Excel导入数据
export function importExcelData(filename, file, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: `${basePath}/${filename}/import-excel`,
    method: 'post',
    data: formData
  })
}

// 导出单个文件为Excel
export function exportJsonDataToExcel(filename, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}/export-excel`,
    method: 'get',
    responseType: 'blob'
  })
}

// 筛选数据
export function filterJsonDataFile(filename, years, countries, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}/filter`,
    method: 'post',
    data: {
      years: years || null,
      countries: countries || null
    }
  })
}
