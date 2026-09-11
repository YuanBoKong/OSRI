import request from './request'

// 根据版本模式获取基础路径
const getBasePath = (versionMode = 'global') => {
  return versionMode === 'aggregation' ? '/output_aggregation' : '/output'
}

// 列出所有output文件
export function listOutputFiles(versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/files`,
    method: 'get'
  })
}

// 读取output文件
export function getOutputFile(filename, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}`,
    method: 'get'
  })
}

// 更新output文件
export function updateOutputFile(filename, data, expectedRevision = null, versionMode = 'global') {
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
export function addOutputData(filename, year, country, value, expectedRevision = null, versionMode = 'global') {
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
export function deleteOutputData(filename, year, country, expectedRevision = null, versionMode = 'global') {
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

// 导出单个文件为Excel
export function exportOutputToExcel(filename, versionMode = 'global') {
  const basePath = getBasePath(versionMode)
  return request({
    url: `${basePath}/${filename}/export-excel`,
    method: 'get',
    responseType: 'blob'
  })
}

// 筛选数据
export function filterOutputFile(filename, years, countries, versionMode = 'global') {
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

