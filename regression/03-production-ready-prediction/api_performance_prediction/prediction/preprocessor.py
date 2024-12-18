import pandas as pd
from typing import List
from ..domain.models import APIMetric

class DataPreprocessor:
    """Preprocesses raw metrics for model input"""
    
    def __init__(self, window_size: int = 12):  # 1-hour window with 5-min intervals
        self.window_size = window_size
    
    def create_feature_vector(self, metrics: List[APIMetric]) -> pd.DataFrame:
        """Convert raw metrics into feature vectors"""
        df = pd.DataFrame([self._metric_to_dict(m) for m in metrics])

        # Calculate error rate directly from raw counts
        df['error_rate'] = df['error_count'] / df['request_count']
        
        # Sort by timestamp
        df.sort_values('timestamp', inplace=True)
        
        # Create time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        # Add rolling means with min_periods=1
        for col in ['latency_ms', 'cpu_usage', 'memory_usage', 'request_count']:
            df[f'{col}_rolling_mean'] = df[col].rolling(
            window=self.window_size, 
            min_periods=1
            ).mean()
        
        return df
    
    def _metric_to_dict(self, metric: APIMetric) -> dict:
        """Convert APIMetric to dictionary"""
        return {
            'timestamp': metric.timestamp,
            'endpoint': metric.endpoint,
            'latency_ms': metric.latency_ms,
            'status_code': metric.status_code,
            'cpu_usage': metric.cpu_usage,
            'memory_usage': metric.memory_usage,
            'request_count': metric.request_count,
            'error_count': metric.error_count
        }