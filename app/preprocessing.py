
from typing import List, Dict
import numpy as np
import pandas as pd
from .schemas import PreprocessingConfig, PreprocessResponse, DistributionData


def calculate_histogram(data: List[float], bins: int = 20) -> DistributionData:
    """Calculate histogram distribution of data.

    Args:
        data: List of float values.
        bins: Number of bins for histogram. Defaults to 20.

    Returns:
        DistributionData with labels and counts.
    """
    if not data:
        return DistributionData(labels=[], counts=[])
    
    counts, bin_edges = np.histogram(data, bins=bins)
    # Use bin centers as labels
    labels: np.ndarray = (bin_edges[:-1] + bin_edges[1:]) / 2
    return DistributionData(labels=labels.tolist(), counts=counts.tolist())


def preprocess_data(
    data: List[float], config: PreprocessingConfig
) -> PreprocessResponse:
    """Preprocess reliability data with configurable options.

    Args:
        data: List of input float values (e.g., time between failures).
        config: Configuration for preprocessing steps.

    Returns:
        PreprocessResponse containing original and processed data with statistics.
    """
    df: pd.DataFrame = pd.DataFrame(data, columns=['value'])
    original_data: List[float] = df['value'].tolist()
    original_dist: DistributionData = calculate_histogram(original_data)
    
    # 1. Handle Missing
    if config.handle_missing:
        if config.missing_strategy == 'drop':
            df = df.dropna()
        elif config.missing_strategy == 'mean':
            df = df.fillna(df.mean())
        elif config.missing_strategy == 'median':
            df = df.fillna(df.median())
            
    # 2. Outlier Detection
    if config.detect_outliers and not df.empty:
        if config.outlier_method == 'zscore':
            std: pd.Series = df.std()
            if std['value'] > 0:
                z_scores: pd.DataFrame = np.abs((df - df.mean()) / std)
                df = df[z_scores['value'] < config.outlier_threshold]
        elif config.outlier_method == 'iqr':
            Q1: pd.Series = df.quantile(0.25)
            Q3: pd.Series = df.quantile(0.75)
            IQR: pd.Series = Q3 - Q1
            df = df[~((df < (Q1 - 1.5 * IQR)) | (df > (Q3 + 1.5 * IQR))).any(axis=1)]

    # 3. Normalization
    if config.normalize and not df.empty:
        if config.normalization_method == 'minmax':
            min_val: pd.Series = df.min()
            max_val: pd.Series = df.max()
            if max_val['value'] > min_val['value']:
                df = (df - min_val) / (max_val - min_val)
        elif config.normalization_method == 'zscore':
            std = df.std()
            if std['value'] > 0:
                df = (df - df.mean()) / std

    processed_data: List[float] = df['value'].tolist()
    processed_dist: DistributionData = calculate_histogram(processed_data)
    
    stats: Dict[str, float] = {
        "original_count": float(len(original_data)),
        "processed_count": float(len(processed_data)),
        "mean": float(df['value'].mean()) if not df.empty else 0.0,
        "std": float(df['value'].std()) if not df.empty else 0.0
        original_distribution=original_dist,
        processed_distribution=processed_dist,
        stats=stats
    )
