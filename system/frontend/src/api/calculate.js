import request from './request'

// 执行批量计算（根据版本模式自动选择）
export function executeBatchCalculate(versionMode = 'global') {
  const basePath = versionMode === 'aggregation' ? '/calculate_aggregation' : '/calculate'
  return request({
    url: `${basePath}/batch`,
    method: 'post'
  })
}

// 执行批量计算（聚合版本）- 已实现
export function executeBatchCalculateAggregation() {
  return request({
    url: '/calculate_aggregation/batch',
    method: 'post'
  })
}

// 获取计算状态
export function getCalculateStatus(versionMode = 'global') {
  const basePath = versionMode === 'aggregation' ? '/calculate_aggregation' : '/calculate'
  return request({
    url: `${basePath}/status`,
    method: 'get'
  })
}

