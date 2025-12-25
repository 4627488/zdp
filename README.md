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
- 仅运行部分模型：`uv run zdp-cli data.csv --model jm --model go --model gm`
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

## 模型显示与图表说明
- 预测曲线：现已展示所有运行成功的模型，不再仅限排名前 3（早期版本因 `plot_prediction_overview(max_models=3)` 导致部分模型未显示）。
- 残差分析 / U 图 / Y 图：界面新增“图表模型”下拉选择，可切换对应模型的曲线（早期版本始终使用最佳模型）。
- 数据类型限制：`BP` 与 `SVR` 仅支持“累计故障数”数据。如果导入的是“故障间隔（TBF）”数据，这两类模型将被自动跳过，因此不会在图表或表格中出现。
 - GM 说明：现已提供独立 `GM(1,1)` 模型（累计故障数），并可在 GUI/CLI 中选择；同时“EMD-SVR/GM 混合”模型仍包含 GM 平滑能力。

