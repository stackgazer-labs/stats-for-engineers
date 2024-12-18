from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

@dataclass(frozen=True)
class APIMetric:
    """Domain model for API metrics"""
    timestamp: datetime
    endpoint: str
    latency_ms: float
    status_code: int
    cpu_usage: float
    memory_usage: float
    request_count: int
    error_count: int

@dataclass(frozen=True)
class PredictionResult:
    """Domain model for prediction results"""
    timestamp: datetime
    endpoint: str
    predicted_latency: float
    confidence_interval: tuple[float, float]
    features_used: Dict[str, float]
    model_version: str

    def __post_init__(self):
        if self.confidence_interval[0] > self.confidence_interval[1]:
            raise ValueError("Invalid confidence interval")
        if any(not isinstance(v, (int, float)) for v in self.features_used.values()):
            raise TypeError("Features must be numeric")