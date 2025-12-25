import os
from typing import Dict, List, Optional, Any

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from .schemas import AlgorithmResult

load_dotenv()


class ReliabilityAnalysis:
    """Reliability analysis and trend analysis for system failure data."""

    tbf: np.ndarray
    cumulative_time: np.ndarray
    train_time: np.ndarray
    results: List[AlgorithmResult]
    n: int
    api_key: Optional[str]
    client: Optional[OpenAI]

    def __init__(
        self,
        tbf_data: List[float],
        train_time: List[float],
        results: List[AlgorithmResult],
    ) -> None:
        """Initialize reliability analysis.

        Args:
            tbf_data: List of time between failures.
            train_time: List of training time points.
            results: List of algorithm results.
        """
        self.tbf: np.ndarray = np.array(tbf_data)
        self.cumulative_time: np.ndarray = np.cumsum(self.tbf)
        self.train_time: np.ndarray = np.array(train_time)
        self.results: List[AlgorithmResult] = results
        self.n: int = len(self.tbf)

        self.api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.client: Optional[OpenAI] = None
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key, base_url="https://api.deepseek.com"
                )
            except Exception as e:
                print(f"Failed to initialize OpenAI client in Analysis: {e}")

    def calculate_laplace_factor(self) -> float:
        """Calculate the Laplace Trend Test factor.

        Laplace Trend Test:
        U = (sum(Ti) - (n-1)Tn/2) / (Tn * sqrt((n-1)/12))
        Ti are cumulative times of failures 1 to n-1
        Tn is cumulative time of failure n

        Returns:
            The Laplace factor value.
        """
        if self.n <= 1:
            return 0.0

        T: np.ndarray = self.cumulative_time
        Tn: np.floating[Any] = T[-1]
        sum_Ti: np.floating[Any] = np.sum(T[:-1])

        numerator: np.floating[Any] = sum_Ti - (self.n - 1) * Tn / 2
        denominator: np.floating[Any] = Tn * np.sqrt((self.n - 1) / 12)

        if denominator == 0:
            return 0.0

        return float(numerator / denominator)

    def get_failure_intensity(self, window: int = 5) -> Dict[str, List[float]]:
        """Get failure intensity with smoothing.

        Failure Intensity ~ 1 / TBF
        Smoothed with moving average.

        Args:
            window: Window size for moving average. Defaults to 5.

        Returns:
            Dictionary with 'raw' and 'smoothed' intensity lists.
        """
        intensity: np.ndarray = 1.0 / np.where(self.tbf <= 0, 1e-6, self.tbf)

        if len(intensity) < window:
            smoothed: np.ndarray = intensity
        else:
            kernel: np.ndarray = np.ones(window) / window
            smoothed = np.convolve(intensity, kernel, mode="same")

        return {"raw": intensity.tolist(), "smoothed": smoothed.tolist()}

    def get_mttf_trend(self) -> List[float]:
        """Get Mean Time To Failure (MTTF) trend.

        Returns:
            List of TBF values representing MTTF trend.
        """
        return self.tbf.tolist()

    def calculate_rocof(self) -> List[float]:
        """Calculate Rate of Occurrence of Failures (ROCOF).

        ROCOF = cumulative failures / cumulative time

        Returns:
            List of ROCOF values.
        """
        with np.errstate(divide="ignore", invalid="ignore"):
            rocof: np.ndarray = np.arange(1, self.n + 1) / self.cumulative_time
            rocof = np.nan_to_num(rocof)
        return rocof.tolist()

    def calculate_reliability_curve(self) -> Dict[str, List[float]]:
        """Calculate empirical reliability function.

        Estimate Reliability Function R(t) = P(T > t)
        Provides empirical survival function of TBFs.

        Returns:
            Dictionary with 'time_points' and 'probability' lists.
        """
        sorted_tbf: np.ndarray = np.sort(self.tbf)
        p_survival: np.ndarray = 1.0 - (np.arange(self.n) / self.n)

        return {"time_points": sorted_tbf.tolist(), "probability": p_survival.tolist()}

    def calculate_failure_distribution(self) -> Dict[str, List[float]]:
        """Calculate failure distribution histogram.

        Returns:
            Dictionary with 'bins' and 'counts' lists.
        """
        counts, bin_edges = np.histogram(self.tbf, bins="auto")
        return {"bins": bin_edges.tolist(), "counts": counts.tolist()}

    def generate_deepseek_report(self, stats: Dict[str, Any]) -> str:
        """Generate comprehensive reliability analysis report using DeepSeek API.

        Args:
            stats: Dictionary of statistics for the report.

        Returns:
            Markdown formatted report or error message.
        """
        if not self.client:
            return "DeepSeek API key not configured. Cannot generate advanced report."

        prompt: str = f"""
        You are a Senior Reliability Engineer generating a comprehensive reliability analysis report.
        Based on the following system data and analysis metrics, please generate a detailed report (Markdown format).
        The report should be extensive, suitable for a formal engineering document (aiming for high detail).

        **IMPORTANT: The report must be BILINGUAL (English and Chinese).**
        For each section, provide the English text first, followed immediately by the Chinese translation.

        **System Data & Metrics:**
        - Total Failures: {stats["total_failures"]}
        - Total Operating Time: {stats["total_time"]:.2f}
        - Laplace Trend Factor: {stats["laplace_factor"]:.4f} (Interpretation: {stats["trend_assessment"]})
        - Best Performing Model: {stats["best_model"]} (RMSE: {stats["best_rmse"]})
        - Recent Failure Intensity (last 5): {stats["failure_intensity"]["raw"][-5:] if len(stats["failure_intensity"]["raw"]) > 5 else stats["failure_intensity"]["raw"]}

        **Report Structure:**
        1.  **Executive Summary (执行摘要)**: High-level overview of system health and key findings.
        2.  **Data Quality & Exploratory Analysis (数据质量与探索性分析)**: Comments on the failure distribution, outliers, and data sufficiency.
        3.  **Trend Analysis (趋势分析)**: Detailed interpretation of the Laplace factor and failure intensity trends. Is the system improving (reliability growth) or degrading?
        4.  **Model Evaluation (模型评估)**: Why the best model ({stats["best_model"]}) might be performing best. What does this imply about the failure process?
        5.  **Reliability Projections (可靠性预测)**: Based on the trends, what can be expected for the next operational period?
        6.  **Maintenance & Testing Recommendations (维护与测试建议)**: Specific actions for the engineering team (e.g., continue testing, release, code review focus).
        7.  **Risk Assessment (风险评估)**: Potential risks if the system is released in its current state.

        Please use professional engineering terminology. Use bullet points, bold text, and clear sections.
        Expand on each point to provide depth.
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Reliability Engineer. You provide reports in both English and Chinese.",
                    },
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating report: {e}"

    def analyze(self, include_llm: bool = False) -> Dict[str, Any]:
        """Perform comprehensive reliability analysis.

        Args:
            include_llm: Whether to include LLM-generated report. Defaults to False.

        Returns:
            Dictionary containing all analysis results.
        """
        laplace: float = self.calculate_laplace_factor()
        intensity: Dict[str, List[float]] = self.get_failure_intensity()

        # Determine trend
        if laplace < -1.96:
            trend: str = "Significant Reliability Growth (Improving)"
            trend_color: str = "success"
        elif laplace > 1.96:
            trend = "Significant Reliability Decay (Worsening)"
            trend_color = "error"
        elif laplace < 0:
            trend = "Slight Reliability Growth"
            trend_color = "info"
        else:
            trend = "Stable or Slight Decay"
            trend_color = "warning"

        # Best Model
        best_model: str = "N/A"
        best_rmse: float = float("inf")

        for res in self.results:
            if res.metrics.rmse is not None and res.metrics.rmse < best_rmse:
                best_rmse = res.metrics.rmse
                best_model = res.name

        # Basic stats for the report
        basic_stats: Dict[str, Any] = {
            "laplace_factor": laplace,
            "trend_assessment": trend,
            "trend_color": trend_color,
            "failure_intensity": intensity,
            "tbf_trend": self.tbf.tolist(),
            "best_model": best_model,
            "best_rmse": best_rmse if best_rmse != float("inf") else None,
            "total_failures": int(self.n),
            "total_time": float(self.cumulative_time[-1]) if self.n > 0 else 0.0,
        }

        # Advanced calculations
        rocof: List[float] = self.calculate_rocof()
        reliability_curve: Dict[str, List[float]] = self.calculate_reliability_curve()
        failure_distribution: Dict[str, List[float]] = self.calculate_failure_distribution()
        cumulative_failures: List[int] = np.arange(1, self.n + 1).tolist()

        # Generate DeepSeek Report
        deepseek_report: Optional[str] = None
        if include_llm:
            deepseek_report = self.generate_deepseek_report(basic_stats)

        return {
            **basic_stats,
            "rocof": rocof,
            "reliability_curve": reliability_curve,
            "failure_distribution": failure_distribution,
            "cumulative_failures": cumulative_failures,
            "deepseek_report": deepseek_report,
        }
