#!/bin/bash
# Electron 应用完整打包脚本

set -e

echo "=== 开始打包 Reliability Prediction 应用 ==="

# 1. 安装依赖
echo ""
echo "步骤 1: 安装依赖..."
bun install

# 2. 构建前端
echo ""
echo "步骤 2: 构建前端应用..."
bun run build

# 3. 编译 Electron 主进程
echo ""
echo "步骤 3: 编译 Electron 主进程..."
bun run build-electron

# 4. 构建 Python 后端（可选，生产模式）
# echo ""
# echo "步骤 4: 构建 Python 后端..."
# python scripts/build-backend.py

# 5. 打包 Electron 应用
echo ""
echo "步骤 5: 打包 Electron 应用..."
electron-builder

echo ""
echo "=== 打包完成！==="
echo ""
echo "生成的文件位置："
ls -la release/
