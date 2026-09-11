// 最早拦截 ResizeObserver 错误（必须在所有导入之前）
(function() {
  // 拦截 webpack-dev-server 客户端脚本的错误处理
  if (typeof window !== 'undefined') {
    // 定义 handleError 之前就拦截
    Object.defineProperty(window, 'handleError', {
      get: function() {
        return function(error) {
          if (error && error.message && /ResizeObserver/i.test(error.message)) {
            return; // 静默忽略
          }
          // 如果没有原始的 handleError，使用 console.error
          if (typeof console !== 'undefined' && console.error) {
            console.error(error);
          }
        };
      },
      set: function(value) {
        // 如果设置了 handleError，包装它
        if (typeof value === 'function') {
          const originalHandleError = value;
          window._originalHandleError = originalHandleError;
          value = function(error) {
            if (error && error.message && /ResizeObserver/i.test(error.message)) {
              return; // 静默忽略
            }
            return originalHandleError.call(this, error);
          };
        }
        window._handleError = value;
      },
      configurable: true
    });
  }
})();

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

// 处理 ResizeObserver 错误（常见于 Element Plus）
// 这是一个已知的浏览器行为，不影响功能，只需要忽略这些错误

// 1. 拦截 console.error
const resizeObserverErrRe = /ResizeObserver/i
const originalError = console.error
console.error = (...args) => {
  if (args.length) {
    // 检查所有参数，查找 ResizeObserver 相关错误
    const hasResizeObserver = args.some(arg => {
      if (typeof arg === 'string') {
        return resizeObserverErrRe.test(arg)
      }
      if (arg && typeof arg === 'object') {
        // 检查错误对象的属性
        if (arg.message && resizeObserverErrRe.test(arg.message)) {
          return true
        }
        if (arg.stack && resizeObserverErrRe.test(arg.stack)) {
          return true
        }
      }
      return false
    })
    
    if (hasResizeObserver) {
      return // 静默忽略
    }
  }
  originalError.apply(console, args)
}

// 2. 拦截全局错误事件
window.addEventListener('error', (event) => {
  const errorMessage = event.message || (event.error && event.error.message) || ''
  const errorString = errorMessage.toString()
  
  if (resizeObserverErrRe.test(errorString) || 
      (event.error && event.error.name === 'Error' && resizeObserverErrRe.test(errorString))) {
    event.preventDefault()
    event.stopPropagation()
    return false
  }
}, true) // 使用捕获阶段

// 3. 拦截未处理的 Promise 拒绝
window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason
  if (reason) {
    const errorMessage = (reason.message || reason.toString() || '')
    if (resizeObserverErrRe.test(errorMessage)) {
      event.preventDefault()
      return false
    }
    
    // 检查错误堆栈
    if (reason.stack && resizeObserverErrRe.test(reason.stack)) {
      event.preventDefault()
      return false
    }
  }
}, true)

// 4. 拦截 console.warn 中的相关警告
const originalWarn = console.warn
console.warn = (...args) => {
  if (args.length) {
    const hasResizeObserver = args.some(arg => {
      if (typeof arg === 'string' && resizeObserverErrRe.test(arg)) {
        return true
      }
      return false
    })
    
    if (hasResizeObserver) {
      return // 静默忽略
    }
  }
  originalWarn.apply(console, args)
}

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')

