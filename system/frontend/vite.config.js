import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const backendTarget = 'http://localhost:6001'

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
      '/OSRI/api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true,
        rewrite: path => path.replace(/^\/OSRI\/api/, '/api')
      },
      '/OSRI/vis-api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true,
        rewrite: path => path.replace(/^\/OSRI\/vis-api/, '/vis-api')
      },
      '/OSRI/osri-vis': {
        target: backendTarget,
        changeOrigin: true,
        rewrite: path => path.replace(/^\/OSRI\/osri-vis/, '/osri-vis')
      },
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true
      },
      '/vis-api': {
        target: backendTarget,
        changeOrigin: true,
        ws: true
      },
      '/osri-vis': {
        target: backendTarget,
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
