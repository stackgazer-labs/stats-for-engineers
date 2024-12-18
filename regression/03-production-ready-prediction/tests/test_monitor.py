import pytest
from datetime import datetime
import numpy as np
from api_performance_prediction.monitoring.monitor import ModelMonitor
from api_performance_prediction.domain.models import PredictionResult, APIMetric

class TestModelMonitor:
    @pytest.fixture
    def monitor(self):
        """Create a monitor instance with default settings"""
        return ModelMonitor(
            mape_threshold=15.0,
            drift_threshold=2.0,
            window_size=5
        )

    @pytest.fixture
    def sample_predictions(self):
        """Create sample predictions for testing"""
        timestamp = datetime.now()
        return [
            PredictionResult(
                timestamp=timestamp,
                endpoint="http://api.example.com",
                predicted_latency=150.0,
                confidence_interval=(140.0, 160.0),
                features_used={"cpu_usage": 45.0},
                model_version="20231217_001"
            )
        ]

    @pytest.fixture
    def sample_actuals(self):
        """Create sample actual metrics for testing"""
        timestamp = datetime.now()
        return [
            APIMetric(
                timestamp=timestamp,
                endpoint="http://api.example.com",
                latency_ms=155.0,
                status_code=200,
                cpu_usage=45.0,
                memory_usage=75.0,
                request_count=1000,
                error_count=5
            )
        ]

    def test_mape_calculation(self, monitor, sample_predictions, sample_actuals):
        """Test MAPE calculation accuracy"""
        metrics = monitor.evaluate_predictions(sample_predictions, sample_actuals)
        
        # Calculate expected MAPE manually
        expected_mape = abs(
            (sample_predictions[0].predicted_latency - sample_actuals[0].latency_ms) 
            / sample_actuals[0].latency_ms
        ) * 100
        
        assert np.isclose(metrics.mape, expected_mape, rtol=1e-10)

    def test_drift_detection_insufficient_data(self, monitor):
        """Test drift detection with insufficient historical data"""
        metrics = monitor.evaluate_predictions(
            [PredictionResult(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                predicted_latency=150.0,
                confidence_interval=(140.0, 160.0),
                features_used={"cpu_usage": 45.0},
                model_version="20231217_001"
            )],
            [APIMetric(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                latency_ms=155.0,
                status_code=200,
                cpu_usage=45.0,
                memory_usage=75.0,
                request_count=1000,
                error_count=5
            )]
        )
        
        # Should not detect drift with insufficient data
        assert not metrics.drift_detected

    def test_drift_detection_with_drift(self, monitor):
        """Test drift detection when drift is present"""
        # Fill historical data with low MAPEs
        for _ in range(monitor.window_size):
            monitor.historical_mapes.append(5.0)
        
        # Create predictions with high error to trigger drift
        predictions = [
            PredictionResult(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                predicted_latency=200.0,  # High prediction
                confidence_interval=(190.0, 210.0),
                features_used={"cpu_usage": 45.0},
                model_version="20231217_001"
            )
        ]
        
        actuals = [
            APIMetric(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                latency_ms=100.0,  # Actual value much lower
                status_code=200,
                cpu_usage=45.0,
                memory_usage=75.0,
                request_count=1000,
                error_count=5
            )
        ]
        
        metrics = monitor.evaluate_predictions(predictions, actuals)
        assert metrics.drift_detected

    def test_alert_generation(self, monitor):
        """Test alert generation for different scenarios"""
        # Create predictions with high error to trigger alerts
        predictions = [
            PredictionResult(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                predicted_latency=200.0,
                confidence_interval=(190.0, 210.0),
                features_used={"cpu_usage": 45.0},
                model_version="20231217_001"
            )
        ]
        
        actuals = [
            APIMetric(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                latency_ms=100.0,
                status_code=200,
                cpu_usage=45.0,
                memory_usage=75.0,
                request_count=1000,
                error_count=5
            )
        ]
        
        metrics = monitor.evaluate_predictions(predictions, actuals)
        
        # Should have high MAPE alert
        assert any("High prediction error" in alert 
                  for alert in metrics.alerts_triggered)

    def test_endpoint_matching(self, monitor):
        """Test that predictions and actuals are correctly matched by endpoint"""
        predictions = [
            PredictionResult(
                timestamp=datetime.now(),
                endpoint="http://api1.example.com",
                predicted_latency=150.0,
                confidence_interval=(140.0, 160.0),
                features_used={"cpu_usage": 45.0},
                model_version="20231217_001"
            )
        ]
        
        actuals = [
            APIMetric(
                timestamp=datetime.now(),
                endpoint="http://api2.example.com",  # Different endpoint
                latency_ms=155.0,
                status_code=200,
                cpu_usage=45.0,
                memory_usage=75.0,
                request_count=1000,
                error_count=5
            )
        ]
        
        metrics = monitor.evaluate_predictions(predictions, actuals)
        # Should have zero MAPE as no endpoints match
        assert metrics.mape == 0.0