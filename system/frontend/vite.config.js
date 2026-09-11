import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 关键：确保打包后的路径以 /OSRI/ 开头（用于部署到子路径）
  base: '/OSRI/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 6002,
    host: '0.0.0.0', // 允许内网访问
    proxy: {
      '/api': {
        target: 'http://localhost:6001',
        changeOrigin: true,
        ws: true
      },
      '/vis-api': {
        target: 'http://localhost:6001',
        changeOrigin: true,
        ws: true
      },
      '/osri-vis': {
        target: 'http://localhost:6001',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'static',
    sourcemap: true
  },
  // 忽略 ResizeObserver 相关的警告（在开发环境中）
  logLevel: 'warn'
})
