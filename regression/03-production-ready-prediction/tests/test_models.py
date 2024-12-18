import pytest
from datetime import datetime
from api_performance_prediction.domain.models import APIMetric, PredictionResult

class TestAPIMetric:
    def test_valid_metric_creation(self):
        """Test creating a valid APIMetric instance"""
        timestamp = datetime.now()
        metric = APIMetric(
            timestamp=timestamp,
            endpoint="http://api.example.com",
            latency_ms=150.5,
            status_code=200,
            cpu_usage=45.2,
            memory_usage=78.1,
            request_count=1000,
            error_count=5
        )
        
        assert metric.timestamp == timestamp
        assert metric.endpoint == "http://api.example.com"
        assert metric.latency_ms == 150.5
        assert metric.status_code == 200
        assert metric.cpu_usage == 45.2
        assert metric.memory_usage == 78.1
        assert metric.request_count == 1000
        assert metric.error_count == 5

    def test_metric_immutability(self):
        """Test that APIMetric instances are immutable"""
        metric = APIMetric(
            timestamp=datetime.now(),
            endpoint="http://api.example.com",
            latency_ms=150.5,
            status_code=200,
            cpu_usage=45.2,
            memory_usage=78.1,
            request_count=1000,
            error_count=5
        )
        
        with pytest.raises(AttributeError):
            metric.latency_ms = 200.0

class TestPredictionResult:
    def test_valid_prediction_creation(self):
        """Test creating a valid PredictionResult instance"""
        timestamp = datetime.now()
        prediction = PredictionResult(
            timestamp=timestamp,
            endpoint="http://api.example.com",
            predicted_latency=175.3,
            confidence_interval=(160.0, 190.0),
            features_used={"cpu_usage": 45.2, "request_count": 1000},
            model_version="20231217_001"
        )
        
        assert prediction.timestamp == timestamp
        assert prediction.endpoint == "http://api.example.com"
        assert prediction.predicted_latency == 175.3
        assert prediction.confidence_interval == (160.0, 190.0)
        assert prediction.features_used == {"cpu_usage": 45.2, "request_count": 1000}
        assert prediction.model_version == "20231217_001"

    def test_confidence_interval_validation(self):
        """Test that confidence intervals are correctly structured"""
        with pytest.raises(ValueError):
            PredictionResult(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                predicted_latency=175.3,
                confidence_interval=(190.0, 160.0),  # Invalid: upper < lower
                features_used={"cpu_usage": 45.2},
                model_version="20231217_001"
            )

    def test_features_used_validation(self):
        """Test that features_used dictionary contains valid types"""
        with pytest.raises(TypeError):
            PredictionResult(
                timestamp=datetime.now(),
                endpoint="http://api.example.com",
                predicted_latency=175.3,
                confidence_interval=(160.0, 190.0),
                features_used={"cpu_usage": "invalid"},  # Invalid: string instead of float
                model_version="20231217_001"
            )