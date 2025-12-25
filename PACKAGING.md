# 桌面应用打包指南

本项目使用 **Electron** 和 **Python FastAPI** 构建跨平台桌面应用。

## 🚀 快速开始

### 开发模式

同时运行前端和后端开发服务器：

```bash
# 方式1: 使用 npm/bun
bun run start-electron

# 方式2: 分别运行
# 终端1
bun run server          # 启动 FastAPI 服务

# 终端2
bun run dev             # 启动 Vite 开发服务

# 终端3
bun run dev-electron    # 启动 Electron 应用
```

### 生产打包

#### 步骤 1: 生成 Windows .exe 安装程序

**Windows 用户：**
```bash
cd scripts
./build.bat
```

**macOS/Linux 用户：**
```bash
bash scripts/build.sh
```

**或手动执行步骤：**
```bash
# 1. 构建前端
bun run build

# 2. 编译 Electron 主进程
bun run build-electron

# 3. 构建 Electron 应用
bun run electron-build
```

#### 步骤 2: 查看生成的文件

打包完成后，生成的文件位于 `release/` 目录：

```
release/
├── Reliability Prediction-0.0.0.exe      # 安装程序（NSIS）
└── Reliability Prediction-portable-0.0.0.exe  # 便携版本（无需安装）
```

## 📋 项目结构

```
project/
├── electron/              # Electron 主进程代码
│   ├── main.ts           # 主进程入口
│   └── preload.ts        # 预加载脚本
├── src/                   # Vue 前端代码
│   ├── main.ts
│   ├── App.vue
│   └── components/
├── app/                   # Python FastAPI 后端
│   ├── main.py
│   ├── schemas.py
│   ├── preprocessing.py
│   └── algorithms/
├── scripts/               # 打包脚本
│   ├── build.bat         # Windows 打包脚本
│   └── build.sh          # macOS/Linux 打包脚本
├── electron-builder.json # Electron 打包配置
├── vite.config.ts        # Vite 前端构建配置
└── package.json          # Node.js 依赖
```

## 🔧 npm/bun 脚本说明

| 脚本 | 说明 |
|------|------|
| `dev` | 启动 Vite 开发服务器 |
| `server` | 启动 FastAPI 开发服务器 |
| `start` | 同时启动前端和后端开发服务器 |
| `start-electron` | 启动完整的 Electron 开发环境 |
| `dev-electron` | 启动 Electron 应用（需要前端和后端已在运行） |
| `build` | 构建前端（生成 dist 目录） |
| `build-electron` | 编译 Electron 主进程并进行类型检查 |
| `electron-build` | 完整的 Electron 打包流程 |
| `preview` | 预览生产构建 |

## 🛠️ 配置说明

### electron-builder.json
配置 Electron 应用的打包参数：
- **appId**: 应用唯一标识
- **productName**: 应用显示名称
- **win**: Windows 打包配置
- **nsis**: Windows 安装程序配置
- **portable**: 便携版本配置

### vite.config.ts
前端构建配置：
- **base**: 设置为 `"./"` 用于 Electron
- **build.outDir**: 输出到 `dist` 目录
- **build.emptyOutDir**: 构建前清空输出目录

### package.json
- **main**: 指定 Electron 主进程入口 (`dist/electron/main.js`)
- **homepage**: 设置为 `"./"` 用于本地文件加载

## 📦 依赖项

### 核心依赖
- **electron**: 桌面应用框架
- **electron-builder**: 打包和分发工具
- **electron-is-dev**: 环境检测工具
- **wait-on**: 等待服务启动工具
- **vue**: 前端框架
- **fastapi**: 后端框架

### 构建依赖
- **vite**: 前端构建工具
- **typescript**: TypeScript 支持
- **vue-tsc**: Vue 类型检查

## 🐛 常见问题

### Q: 打包时提示找不到 Python？
A: 确保 Python 环境已配置到 PATH，或在生产模式下使用 PyInstaller 将 Python 后端打包为 .exe。

### Q: Electron 应用无法连接到 FastAPI？
A: 确保：
1. FastAPI 服务运行在 `http://localhost:8000`
2. 配置了 CORS 中间件（已在 app/main.py 中配置）
3. 前端 API 请求正确（检查 axios 配置）

### Q: 如何修改应用图标？
A: 将图标文件放在 `assets/icon.png`，然后重新构建。

### Q: 如何禁用开发工具？
A: 在生产模式中修改 `electron/main.ts`：
```typescript
// 注释掉这行
// mainWindow.webContents.openDevTools();
```

## 📝 开发流程

1. **本地开发**
   ```bash
   bun run start-electron
   ```

2. **测试打包**
   ```bash
   bun run electron-build
   ```

3. **分发安装程序**
   - 分发 `release/Reliability Prediction-0.0.0.exe`（安装版）
   - 或分发 `release/Reliability Prediction-portable-0.0.0.exe`（免安装版）

## 🔐 安全建议

1. ✅ 已启用 Context Isolation
2. ✅ 已禁用 Node Integration
3. ✅ 已配置 Sandbox
4. 📝 考虑使用 IPC 通信代替直接调用
5. 📝 定期更新依赖版本

## 📞 支持

如遇问题，请检查：
- 所有依赖是否正确安装
- Python 环境变量配置
- 防火墙是否阻止本地端口
- 日志输出中的错误信息
