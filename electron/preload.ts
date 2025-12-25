// 预加载脚本 - 为了安全性，Electron 应用中推荐使用预加载脚本
// 当前配置中没有使用，但这是最佳实践

import { contextBridge } from 'electron';

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
    // 例如：可以添加获取应用版本等功能
});
