# tests/test_model_server.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import tempfile
import os
from sklearn.ensemble import GradientBoostingRegressor

from api_performance_prediction.prediction.model import ModelServer

class TestModelServer:
    @pytest.fixture
    def sample_features(self):
        """Create sample features for testing predictions"""
        return pd.DataFrame({
            'timestamp': [datetime.now()],
            'endpoint': ['http://api.example.com'],
            'latency_ms': [150.0],
            'cpu_usage': [45.0],
            'memory_usage': [75.0],
            'request_count': [1000],
            'error_count': [5],
            'hour': [14],
            'day_of_week': [2],
            'latency_ms_rolling_mean': [145.0],
            'cpu_usage_rolling_mean': [44.0],
            'memory_usage_rolling_mean': [74.0],
            'request_count_rolling_mean': [980.0],
            'error_rate': [0.005]
        })

    @pytest.fixture
    def trained_model_path(self):
        """Create and save a trained model for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.joblib') as tmp:
            model = GradientBoostingRegressor(n_estimators=10)
            X = np.random.rand(100, 5)
            y = np.random.rand(100)
            model.fit(X, y)
            
            import joblib
            joblib.dump(model, tmp.name)
            
            yield tmp.name
            
        # Cleanup after tests
        os.unlink(tmp.name)

    def test_model_creation(self):
        """Test that model server creates a default model correctly"""
        server = ModelServer()
        assert server.model is not None
        assert isinstance(server.model, GradientBoostingRegressor)
        assert server.model_version is not None

    def test_model_loading(self, trained_model_path):
        """Test loading a saved model"""
        server = ModelServer(model_path=trained_model_path)
        assert server.model is not None
        assert isinstance(server.model, GradientBoostingRegressor)

    def test_prediction_format(self, sample_features):
        """Test that predictions have the correct format"""
        server = ModelServer()
        predictions = server.predict(sample_features)
        
        assert len(predictions) == len(sample_features)
        prediction = predictions[0]
        
        assert prediction.timestamp == sample_features['timestamp'].iloc[0]
        assert prediction.endpoint == sample_features['endpoint'].iloc[0]
        assert isinstance(prediction.predicted_latency, float)
        assert isinstance(prediction.confidence_interval, tuple)
        assert len(prediction.confidence_interval) == 2
        assert prediction.confidence_interval[0] <= prediction.confidence_interval[1]
        assert prediction.model_version == server.model_version

    def test_confidence_intervals(self, sample_features):
        """Test that confidence intervals are reasonable"""
        server = ModelServer()
        predictions = server.predict(sample_features)
        prediction = predictions[0]
        
        # Confidence interval should contain the predicted value
        assert (prediction.confidence_interval[0] <= prediction.predicted_latency <= 
                prediction.confidence_interval[1])
        
        # Interval width should be positive
        assert (prediction.confidence_interval[1] - prediction.confidence_interval[0]) > 0

    def test_model_saving(self):
        """Test saving and reloading a model"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.joblib') as tmp:
            server = ModelServer()
            server.save_model(tmp.name)
            
            # Try loading the saved model
            new_server = ModelServer(model_path=tmp.name)
            assert new_server.model is not None
            
            os.unlink(tmp.name)

    def test_feature_persistence(self, sample_features):
        """Test that features used are correctly stored in predictions"""
        server = ModelServer()
        predictions = server.predict(sample_features)
        prediction = predictions[0]
        
        # Check that all features are present in features_used
        for column in sample_features.columns:
            assert column in prediction.features_used
            
        # Check that feature values match
        for column in sample_features.columns:
            if isinstance(sample_features[column].iloc[0], (int, float)):
                assert prediction.features_used[column] == sample_features[column].iloc[0]