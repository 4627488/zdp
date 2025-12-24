
export default {
    app: {
        title: "软件可靠性预测系统",
        tabs: {
            preprocess: "数据预处理",
            predict: "模型预测",
            analysis: "高级分析"
        }
    },
    common: {
        loading: "加载中...",
        success: "成功",
        error: "错误",
        na: "N/A"
    },
    preprocess: {
        title: "数据与配置",
        uploadLabel: "上传数据 (CSV)",
        uploadHint: "必需列: 'tbf' 或 'TBF'",
        loadedRecords: "已加载 {n} 条记录。",
        optionsTitle: "预处理选项",
        handleMissing: "处理缺失值",
        strategy: "策略",
        detectOutliers: "检测异常值",
        method: "方法",
        normalization: "归一化",
        runBtn: "运行预处理",
        statsTitle: "统计信息",
        stats: {
            originalCount: "原始数量",
            processedCount: "处理后数量",
            mean: "均值",
            stdDev: "标准差"
        },
        distTitle: "分布分析",
        distPlaceholder: "运行预处理以查看分布变化"
    },
    predict: {
        configTitle: "模型配置",
        usingProcessed: "使用处理后的数据 ({n} 样本)",
        usingRaw: "使用原始数据 ({n} 样本)。建议先进行预处理。",
        trainRatio: "训练比例",
        selectAlgo: "选择算法",
        trainBtn: "训练与预测",
        metricsTitle: "指标",
        exportBtn: "导出结果 (CSV)",
        columns: {
            model: "模型",
            rmse: "均方根误差 (RMSE)",
            mae: "平均绝对误差 (MAE)"
        },
        tooltips: {
            rmse: "均方根误差",
            mae: "平均绝对误差"
        },
        resultsTitle: "预测结果",
        placeholder: "运行预测以查看结果"
    },
    analysis: {
        noDataTitle: "暂无分析数据",
        noDataDesc: "请先运行预测以生成洞察报告。",
        cards: {
            trend: {
                title: "可靠性趋势",
                subtitle: "Laplace 因子: {n}"
            },
            bestModel: {
                title: "最佳模型",
                subtitle: "最低 RMSE"
            },
            failures: {
                title: "总故障数",
                subtitle: "观测到的事件"
            },
            time: {
                title: "总时间",
                subtitle: "累计执行时间"
            }
        },
        charts: {
            intensity: {
                title: "故障强度 (发生率)",
                subtitle: "平滑后的 1/TBF - 指示故障是否变得不频繁",
                smoothed: "平滑强度",
                raw: "原始强度"
            },
            tbf: {
                title: "故障间隔时间 (TBF) 趋势",
                subtitle: "原始间隔时间 - 上升趋势 = 可靠性增长",
                label: "故障间隔时间"
            }
        },
        insights: {
            title: "自动化可靠性洞察",
            trend: {
                title: "趋势分析",
                desc: "Laplace 趋势测试得分为 {score}。低于 -1.96 的值表示显著的可靠性增长（95% 置信度）。高于 1.96 的值表示可靠性衰退。当前状态：{status}。"
            },
            performance: {
                title: "模型性能",
                desc: "在评估的模型中，{model} 表现最佳，RMSE 为 {rmse}。这表明它最准确地捕捉了该数据集的潜在故障过程。"
            }
        }
    },
    charts: {
        trainData: "训练数据",
        actualTest: "实际测试数据",
        originalDist: "原始分布",
        processedDist: "处理后分布",
        failureNum: "故障序号",
        cumulativeTime: "累计时间",
        distribution: "数据分布"
    },
    export: {
        index: "索引",
        trainTest: "训练/测试",
        actualTime: "实际累计时间",
        prediction: "{model} 预测",
        train: "训练",
        test: "测试"
    }
}
