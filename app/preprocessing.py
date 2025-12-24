
from typing import List, Dict
import numpy as np
import pandas as pd
from .schemas import PreprocessingConfig, PreprocessResponse, DistributionData

def calculate_histogram(data: List[float], bins: int = 20) -> DistributionData:
    if not data:
        return DistributionData(labels=[], counts=[])
    
    counts, bin_edges = np.histogram(data, bins=bins)
    # Use bin centers as labels
    labels = (bin_edges[:-1] + bin_edges[1:]) / 2
    return DistributionData(labels=labels.tolist(), counts=counts.tolist())

def preprocess_data(data: List[float], config: PreprocessingConfig) -> PreprocessResponse:
    df = pd.DataFrame(data, columns=['value'])
    original_data = df['value'].tolist()
    original_dist = calculate_histogram(original_data)
    
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
            std = df.std()
            if std['value'] > 0:
                z_scores = np.abs((df - df.mean()) / std)
                df = df[z_scores['value'] < config.outlier_threshold]
        elif config.outlier_method == 'iqr':
            Q1 = df.quantile(0.25)
            Q3 = df.quantile(0.75)
            IQR = Q3 - Q1
            df = df[~((df < (Q1 - 1.5 * IQR)) | (df > (Q3 + 1.5 * IQR))).any(axis=1)]

    # 3. Normalization
    if config.normalize and not df.empty:
        if config.normalization_method == 'minmax':
            min_val = df.min()
            max_val = df.max()
            if max_val['value'] > min_val['value']:
                df = (df - min_val) / (max_val - min_val)
        elif config.normalization_method == 'zscore':
            std = df.std()
            if std['value'] > 0:
                df = (df - df.mean()) / std

    processed_data = df['value'].tolist()
    processed_dist = calculate_histogram(processed_data)
    
    stats = {
        "original_count": len(original_data),
        "processed_count": len(processed_data),
        "mean": float(df['value'].mean()) if not df.empty else 0,
        "std": float(df['value'].std()) if not df.empty else 0
    }

    return PreprocessResponse(
        original_data=original_data,
        processed_data=processed_data,
        original_distribution=original_dist,
        processed_distribution=processed_dist,
        stats=stats
    )
