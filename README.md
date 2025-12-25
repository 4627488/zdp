# Zero-Defect Prediction (ZDP)

一个基于 Python 科学计算生态 + PySide6 桌面界面的可靠性/缺陷相关分析工具集（含数据导入、模型拟合、可视化与报告导出）。

## 快速开始（uv）
1. 安装依赖：
   - `uv sync --all-extras`
2. 启动桌面端：
   - `uv run zdp`
   - 或：`python -m zdp`
3. 运行测试：
   - `uv run pytest`

## 命令行（CLI）
- 基本用法：`uv run zdp-cli data.csv --time-column t --value-column failures`
- 仅运行部分模型：`uv run zdp-cli data.csv --model jm --model go`
- 导出 PDF 报告：`uv run zdp-cli data.csv --report zdp-report.pdf`

## 代码入口
- 数据加载与类型：[src/zdp/data/__init__.py](src/zdp/data/__init__.py)
- 模型注册与实现：[src/zdp/models/__init__.py](src/zdp/models/__init__.py)
- 分析编排服务：[src/zdp/services/analysis.py](src/zdp/services/analysis.py)
- 命令行入口：[src/zdp/cli.py](src/zdp/cli.py)
- 桌面端入口：[src/zdp/app.py](src/zdp/app.py)

## 目录结构（简版）
```
.
├── pyproject.toml
├── README.md
├── data/                 # 示例数据
├── scripts/              # 辅助脚本
├── src/
│   └── zdp/              # 主包
└── tests/
```
