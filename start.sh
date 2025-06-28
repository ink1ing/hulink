#!/bin/bash

# Hulink 启动脚本
# 自动激活虚拟环境并运行程序

echo "正在启动 Hulink 代理节点订阅链接转换工具..."
echo "========================================"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    python3 -m venv venv
    echo "虚拟环境创建完成"
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖是否已安装
if ! python -c "import requests, yaml, rich" 2>/dev/null; then
    echo "正在安装依赖包..."
    pip install -r requirements.txt
    echo "依赖包安装完成"
fi

# 运行主程序
echo "启动程序..."
echo ""
python3 main.py

# 程序结束后的提示
echo ""
echo "程序已退出，感谢使用 Hulink!"
