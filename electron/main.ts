import { app, BrowserWindow, Menu } from 'electron';
import path from 'path';
import { spawn } from 'child_process';
import isDev from 'electron-is-dev';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow: any = null;
let pythonProcess: any = null;

const createWindow = () => {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
        },
        icon: path.join(__dirname, '../assets/icon.png'),
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
};

const startPythonServer = async () => {
    return new Promise((resolve) => {
        if (isDev) {
            // 开发模式：Python 已通过 `npm run server` 启动
            setTimeout(() => resolve(true), 1000);
        } else {
            // 生产模式：启动打包的 Python 可执行文件
            const pythonPath = path.join(__dirname, '../dist/backend/backend.exe');
            pythonProcess = spawn(pythonPath, [], {
                detached: true,
                stdio: 'ignore',
            });
            pythonProcess.unref();
            setTimeout(() => resolve(true), 2000);
        }
    });
};

app.on('ready', async () => {
    await startPythonServer();
    createWindow();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (mainWindow === null) {
        createWindow();
    }
});

// 清理进程
app.on('quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

// 创建应用菜单
const template: any = [
    {
        label: '文件',
        submenu: [
            {
                label: '退出',
                accelerator: 'CmdOrCtrl+Q',
                click: () => {
                    app.quit();
                },
            },
        ],
    },
    {
        label: '查看',
        submenu: [
            { role: 'reload' },
            { role: 'forceReload' },
            { role: 'toggleDevTools' },
        ],
    },
    {
        label: '帮助',
        submenu: [
            {
                label: '关于',
                click: () => {
                    // 可以打开关于对话框
                },
            },
        ],
    },
];

Menu.setApplicationMenu(Menu.buildFromTemplate(template));
