"""
Python 应用打包脚本
使用 PyInstaller 将 FastAPI 应用打包成独立的可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_python_backend():
    """构建 Python 后端可执行文件"""
    
    project_root = Path(__file__).parent
    dist_backend = project_root / "dist" / "backend"
    
    # 创建输出目录
    dist_backend.mkdir(parents=True, exist_ok=True)
    
    print("开始打包 Python 后端...")
    
    # PyInstaller 命令
    pyinstaller_args = [
        "pyinstaller",
        "--onefile",  # 打包为单个文件
        "--name", "backend",
        "--distpath", str(dist_backend / "dist"),
        "--buildpath", str(project_root / "build"),
        "--specpath", str(project_root),
        "--add-data", f"app:app",  # 包含 app 目录
        "--hidden-import=fastapi",
        "--hidden-import=uvicorn",
        "--hidden-import=sklearn",
        "--hidden-import=numpy",
        "--hidden-import=pandas",
        "--hidden-import=scipy",
        "--hidden-import=pydantic",
        "--hidden-import=openai",
        str(project_root / "main.py")
    ]
    
    # 如果是 Windows，添加 Windows 特定选项
    if sys.platform == "win32":
        pyinstaller_args.extend([
            "--windowed",  # 不显示控制台窗口
            "--icon=assets/icon.ico",  # 应用图标（如果存在）
        ])
    
    try:
        subprocess.run(pyinstaller_args, check=True)
        print("✓ Python 后端打包成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Python 后端打包失败: {e}")
        return False

def cleanup():
    """清理临时文件"""
    project_root = Path(__file__).parent
    
    # 删除 PyInstaller 生成的临时文件
    build_dir = project_root / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print("✓ 已清理临时文件")

if __name__ == "__main__":
    success = build_python_backend()
    cleanup()
    
    if not success:
        sys.exit(1)
    
    print("\n✓ 打包完成！")
