#!/bin/bash

# OSRI前端部署脚本
# 使用方法: ./deploy.sh

echo "开始构建前端项目..."
npm run build

if [ $? -eq 0 ]; then
    echo "构建成功！"
    echo "构建文件位于 dist/ 目录"
    echo ""
    echo "部署步骤："
    echo "1. 将 dist/ 目录上传到服务器"
    echo "2. 配置 Nginx（参考 nginx.conf.example）"
    echo "3. 确保后端API已运行在 6001 端口"
    echo ""
    echo "本地测试："
    echo "  - 前端: npm run dev (端口 6002)"
    echo "  - 后端: python api.py (端口 6001)"
else
    echo "构建失败！"
    exit 1
fi
