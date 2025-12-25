@echo off
REM Electron 应用完整打包脚本 (Windows)

setlocal enabledelayedexpansion

echo === 开始打包 Reliability Prediction 应用 ===

REM 1. 安装依赖
echo.
echo 步骤 1: 安装依赖...
call bun install

REM 2. 构建前端
echo.
echo 步骤 2: 构建前端应用...
call bun run build

REM 3. 编译 Electron 主进程
echo.
echo 步骤 3: 编译 Electron 主进程...
call bun run build-electron

REM 4. 打包 Electron 应用
echo.
echo 步骤 4: 打包 Electron 应用...
cd ..
call npx electron-builder
cd scripts

echo.
echo === 打包完成！===
echo.
echo 生成的文件位置：
dir release\

pause
