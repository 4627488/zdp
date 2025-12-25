
export default {
    app: {
        title: "Software Reliability Prediction System",
        tabs: {
            preprocess: "Data Preprocessing",
            predict: "Model Prediction",
            analysis: "Advanced Analysis"
        }
    },
    common: {
        loading: "Loading...",
        success: "Success",
        error: "Error",
        na: "N/A"
    },
    preprocess: {
        title: "Data & Configuration",
        uploadLabel: "Upload Data (CSV)",
        uploadHint: "Required column: 'tbf' or 'TBF'",
        loadedRecords: "Loaded {n} records.",
        optionsTitle: "Preprocessing Options",
        handleMissing: "Handle Missing Values",
        strategy: "Strategy",
        detectOutliers: "Detect Outliers",
        method: "Method",
        normalization: "Normalization",
        runBtn: "Run Preprocessing",
        statsTitle: "Statistics",
        stats: {
            originalCount: "Original Count",
            processedCount: "Processed Count",
            mean: "Mean",
            stdDev: "Std Dev"
        },
        distTitle: "Distribution Analysis",
        distPlaceholder: "Run preprocessing to view distribution changes"
    },
    predict: {
        configTitle: "Model Configuration",
        usingProcessed: "Using processed data ({n} samples)",
        usingRaw: "Using raw data ({n} samples). Recommend preprocessing first.",
        trainRatio: "Training Ratio",
        selectAlgo: "Select Algorithms",
        trainBtn: "Train & Predict",
        metricsTitle: "Metrics",
        exportBtn: "Export Results (CSV)",
        columns: {
            model: "Model",
            rmse: "RMSE",
            mae: "MAE"
        },
        tooltips: {
            rmse: "Root Mean Square Error",
            mae: "Mean Absolute Error"
        },
        resultsTitle: "Prediction Results",
        placeholder: "Run prediction to see results"
    },
    analysis: {
        noDataTitle: "No Analysis Data Available",
        noDataDesc: "Please run a prediction first to generate insights.",
        cards: {
            trend: {
                title: "Reliability Trend",
                subtitle: "Laplace Factor: {n}"
            },
            bestModel: {
                title: "Best Model",
                subtitle: "Lowest RMSE"
            },
            failures: {
                title: "Total Failures",
                subtitle: "Observed Events"
            },
            time: {
                title: "Total Time",
                subtitle: "Cumulative Execution Time"
            }
        },
        charts: {
            intensity: {
                title: "Failure Intensity (Rate of Occurrence)",
                subtitle: "Smoothed 1/TBF - Indicates if failures are becoming less frequent",
                smoothed: "Smoothed Intensity",
                raw: "Raw Intensity"
            },
            tbf: {
                title: "Time Between Failures (TBF) Trend",
                subtitle: "Raw interval times - Increasing trend = Reliability Growth",
                label: "Time Between Failures"
            },
            rocof: {
                title: "Rate of Occurrence of Failures (ROCOF)",
                label: "ROCOF"
            },
            cumulative: {
                title: "Cumulative Failures (S-Curve)",
                label: "Cumulative Failures"
            },
            reliability: {
                title: "Reliability Curve (Survival Probability)",
                label: "Survival Probability P(T > t)"
            },
            distribution: {
                title: "Failure Distribution (Histogram)",
                label: "Frequency"
            }
        },
        deepseek: {
            title: "AI Reliability Analysis Report (DeepSeek)",
            placeholder: "Click 'Generate Report' to get a detailed AI analysis.",
            loading: {
                init: "Initializing analysis...",
                analyzing: "Analyzing statistical patterns...",
                connecting: "Connecting to DeepSeek AI...",
                generating: "Generating bilingual report..."
            }
        },
        report: {
            subtitle: "Comprehensive Reliability Analysis Report",
            generatedOn: "Generated on"
        },
        actions: {
            downloadPdf: "Download PDF Report",
            generateReport: "Generate AI Report"
        },
        insights: {
            title: "Automated Reliability Insights",
            trend: {
                title: "Trend Analysis",
                desc: "The Laplace Trend Test score is {score}. Values below -1.96 indicate significant reliability growth (95% confidence). Values above 1.96 indicate reliability decay. Current status: {status}."
            },
            performance: {
                title: "Model Performance",
                desc: "Among the evaluated models, {model} performed best with an RMSE of {rmse}. This suggests it captures the underlying failure process most accurately for this dataset."
            }
        }
    },
    charts: {
        trainData: "Training Data",
        actualTest: "Actual Test Data",
        originalDist: "Original Distribution",
        processedDist: "Processed Distribution",
        failureNum: "Failure Number",
        cumulativeTime: "Cumulative Time",
        distribution: "Data Distribution"
    },
    export: {
        index: "Index",
        trainTest: "Train/Test",
        actualTime: "Actual Cumulative Time",
        prediction: "{model} Prediction",
        train: "Train",
        test: "Test"
    }
}
