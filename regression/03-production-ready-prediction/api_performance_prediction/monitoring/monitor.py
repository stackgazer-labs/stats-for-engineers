from dataclasses import dataclass
from datetime import datetime
import numpy as np
from typing import List, Optional
from ..domain.models import PredictionResult, APIMetric

@dataclass
class MonitoringMetrics:
    """Metrics for model monitoring"""
    timestamp: datetime
    mape: float  # Mean Absolute Percentage Error
    prediction_count: int
    drift_detected: bool
    alerts_triggered: List[str]

class ModelMonitor:
    """Monitors model performance and triggers alerts"""
    
    def __init__(self, 
                 mape_threshold: float = 15.0,  # 15% error threshold
                 drift_threshold: float = 2.0,   # 2 std deviations
                 window_size: int = 100):
        self.mape_threshold = mape_threshold
        self.drift_threshold = drift_threshold
        self.window_size = window_size
        self.historical_mapes: List[float] = []
        
    def evaluate_predictions(self, 
                           predictions: List[PredictionResult], 
                           actuals: List[APIMetric]) -> MonitoringMetrics:
        """Evaluate prediction quality and check for drift"""
        
        # Calculate MAPE
        mape = self._calculate_mape(predictions, actuals)
        self.historical_mapes.append(mape)
        
        # Check for drift
        drift_detected = self._check_drift()
        
        # Generate alerts
        alerts = self._generate_alerts(mape, drift_detected)
        
        return MonitoringMetrics(
            timestamp=datetime.now(),
            mape=mape,
            prediction_count=len(predictions),
            drift_detected=drift_detected,
            alerts_triggered=alerts
        )
    
    def _calculate_mape(self, 
                       predictions: List[PredictionResult], 
                       actuals: List[APIMetric]) -> float:
        """Calculate Mean Absolute Percentage Error"""
        errors = []
        for pred, actual in zip(predictions, actuals):
            if pred.endpoint == actual.endpoint:
                percentage_error = abs(
                    (pred.predicted_latency - actual.latency_ms) / actual.latency_ms
                ) * 100
                errors.append(percentage_error)
        
        return np.mean(errors) if errors else 0.0
    
    def _check_drift(self) -> bool:
        """Check for model drift using recent MAPEs"""
        if len(self.historical_mapes) < self.window_size:
            return False
            
        recent_mapes = self.historical_mapes[-self.window_size:]
        mean_mape = np.mean(recent_mapes)
        baseline_mape = np.mean(self.historical_mapes[:-self.window_size])  # Fix: Use earlier data as baseline
        std_mape = np.std(self.historical_mapes)
        
        return mean_mape > (baseline_mape + self.drift_threshold * std_mape)  # Fix: Compare to baseline

    def _generate_alerts(self, 
                        current_mape: float, 
                        drift_detected: bool) -> List[str]:
        """Generate alert messages based on monitoring metrics"""
        alerts = []
        
        if current_mape > self.mape_threshold:
            alerts.append(
                f"High prediction error: MAPE={current_mape:.2f}% > {self.mape_threshold}%"
            )
            
        if drift_detected:
            alerts.append("Model drift detected - retraining recommended")
            
        return alerts
