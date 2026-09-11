import { createRouter, createWebHistory } from 'vue-router'
import JsonDataManagement from '../views/JsonDataManagement.vue'
import OutputResults from '../views/OutputResults.vue'
import DataVis from '../views/DataVis.vue'

const routes = [
  {
    path: '/',
    redirect: '/jsondata'
  },
  {
    path: '/jsondata',
    name: 'JsonDataManagement',
    component: JsonDataManagement,
    meta: { title: '数据管理' }
  },
  {
    path: '/output',
    name: 'OutputResults',
    component: OutputResults,
    meta: { title: '计算结果' }
  },
  {
    path: '/datavis',
    name: 'DataVis',
    component: DataVis,
    meta: { title: '结果可视化' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router

