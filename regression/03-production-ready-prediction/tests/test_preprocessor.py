import pytest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from api_performance_prediction.prediction.preprocessor import DataPreprocessor
from api_performance_prediction.domain.models import APIMetric

class TestDataPreprocessor:
    @pytest.fixture
    def preprocessor(self):
        """Create a preprocessor instance with default settings"""
        return DataPreprocessor(window_size=3)
    
    @pytest.fixture
    def sample_metrics(self):
        """Create a sample list of metrics for testing"""
        base_time = datetime.now()
        metrics = []
        
        for i in range(5):
            metrics.append(APIMetric(
                timestamp=base_time + timedelta(minutes=5*i),
                endpoint="http://api.example.com",
                latency_ms=100 + i*10,
                status_code=200,
                cpu_usage=40 + i*5,
                memory_usage=70 + i*2,
                request_count=1000 + i*100,
                error_count=5 + i
            ))
        
        return metrics

    def test_feature_vector_creation(self, preprocessor, sample_metrics):
        """Test that feature vectors are created correctly"""
        df = preprocessor.create_feature_vector(sample_metrics)
        
        # Check that all expected columns are present
        expected_columns = {
            'timestamp', 'endpoint', 'latency_ms', 'cpu_usage', 'memory_usage',
            'request_count', 'error_count', 'hour', 'day_of_week',
            'latency_ms_rolling_mean', 'cpu_usage_rolling_mean',
            'memory_usage_rolling_mean', 'request_count_rolling_mean',
            'error_rate'
        }
        assert all(col in df.columns for col in expected_columns)
        
        # Check that rolling means are calculated correctly
        assert not df['latency_ms_rolling_mean'].isna().all()
        assert len(df) == len(sample_metrics)

    def test_rolling_statistics(self, preprocessor, sample_metrics):
        """Test that rolling statistics are calculated correctly"""
        df = preprocessor.create_feature_vector(sample_metrics)
        
        # Check last row instead of fixed index
        assert pd.notna(df['latency_ms_rolling_mean'].iloc[-1])
        
        # Calculate expected mean for last 3 points
        expected_latency_mean = np.mean([
            m.latency_ms for m in sample_metrics[-3:]
        ])
        assert np.isclose(
            df['latency_ms_rolling_mean'].iloc[-1],
            expected_latency_mean,
            rtol=1e-10
        )

    def test_error_rate_calculation(self, preprocessor, sample_metrics):
        """Test that error rates are calculated correctly"""
        df = preprocessor.create_feature_vector(sample_metrics)
        
        # Calculate expected error rate for the first row
        expected_error_rate = sample_metrics[0].error_count / sample_metrics[0].request_count
        assert np.isclose(df['error_rate'].iloc[0], expected_error_rate, rtol=1e-10)

    def test_time_based_features(self, preprocessor, sample_metrics):
        """Test that time-based features are created correctly"""
        df = preprocessor.create_feature_vector(sample_metrics)
        
        # Check hour is in range 0-23
        assert all(0 <= hour <= 23 for hour in df['hour'])
        
        # Check day_of_week is in range 0-6
        assert all(0 <= dow <= 6 for dow in df['day_of_week'])
        
        # Check that the hour matches the input timestamp
        assert df['hour'].iloc[0] == sample_metrics[0].timestamp.hour