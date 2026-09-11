#!/bin/bash
# 文件同步守护进程启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 激活虚拟环境（如果使用虚拟环境）
# source venv/bin/activate

# 启动守护进程
python3 file_sync_daemon.py

