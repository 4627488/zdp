
from typing import List, Dict, Optional
import numpy as np
from .schemas import AlgorithmResult

class ReliabilityAnalysis:
    def __init__(self, tbf_data: List[float], train_time: List[float], results: List[AlgorithmResult]):
        self.tbf = np.array(tbf_data)
        self.cumulative_time = np.cumsum(self.tbf)
        self.train_time = np.array(train_time)
        self.results = results
        self.n = len(self.tbf)

    def calculate_laplace_factor(self) -> float:
        # Laplace Trend Test
        # U = (sum(Ti) - (n-1)Tn/2) / (Tn * sqrt((n-1)/12))
        # Ti are cumulative times of failures 1 to n-1
        # Tn is cumulative time of failure n
        
        if self.n <= 1:
            return 0.0
            
        T = self.cumulative_time
        Tn = T[-1]
        sum_Ti = np.sum(T[:-1])
        
        numerator = sum_Ti - (self.n - 1) * Tn / 2
        denominator = Tn * np.sqrt((self.n - 1) / 12)
        
        if denominator == 0:
            return 0.0
            
        return float(numerator / denominator)

    def get_failure_intensity(self, window: int = 5) -> Dict[str, List[float]]:
        # Failure Intensity ~ 1 / TBF
        # Smoothed with moving average
        intensity = 1.0 / np.where(self.tbf <= 0, 1e-6, self.tbf)
        
        if len(intensity) < window:
            smoothed = intensity
        else:
            kernel = np.ones(window) / window
            smoothed = np.convolve(intensity, kernel, mode='same')
            
        return {
            "raw": intensity.tolist(),
            "smoothed": smoothed.tolist()
        }

    def get_mttf_trend(self) -> List[float]:
        # Cumulative Average TBF (simple MTTF estimator over time)
        # or instantaneous TBF
        return self.tbf.tolist()

    def analyze(self) -> Dict:
        laplace = self.calculate_laplace_factor()
        intensity = self.get_failure_intensity()
        
        # Determine trend
        if laplace < -1.96:
            trend = "Significant Reliability Growth (Improving)"
            trend_color = "success"
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
        best_model = "N/A"
        best_rmse = float('inf')
        
        for res in self.results:
            if res.metrics.rmse is not None and res.metrics.rmse < best_rmse:
                best_rmse = res.metrics.rmse
                best_model = res.name

        return {
            "laplace_factor": laplace,
            "trend_assessment": trend,
            "trend_color": trend_color,
            "failure_intensity": intensity,
            "tbf_trend": self.tbf.tolist(),
            "best_model": best_model,
            "best_rmse": best_rmse if best_rmse != float('inf') else None,
            "total_failures": int(self.n),
            "total_time": float(self.cumulative_time[-1]) if self.n > 0 else 0
        }
