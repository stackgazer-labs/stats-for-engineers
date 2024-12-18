from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

class ActionType(Enum):
    SCALE = "scale"
    CIRCUIT_BREAK = "circuit_break"
    ADJUST_CACHE = "adjust_cache"
    ADJUST_LOAD_BALANCER = "adjust_load_balancer"

class ActionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class MetricSnapshot:
    timestamp: datetime
    endpoint: str
    request_count: int
    latency_ms: float
    error_rate: float
    cpu_utilization: float
    memory_utilization: float
    cache_hit_rate: Optional[float] = None

@dataclass
class PredictionResult:
    timestamp: datetime
    endpoint: str
    predicted_latency: float
    confidence_interval: tuple[float, float]
    risk_level: float

@dataclass
class Action:
    id: str
    type: ActionType
    target_endpoint: str
    parameters: Dict[str, any]
    status: ActionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@dataclass
class Policy:
    id: str
    name: str
    description: str
    conditions: List[Dict]
    actions: List[Dict]
    enabled: bool
    priority: int

@dataclass
class ActionResult:
    action: Action
    metrics_before: MetricSnapshot
    metrics_after: Optional[MetricSnapshot]
    success: bool
    duration_ms: float
    side_effects: List[str]