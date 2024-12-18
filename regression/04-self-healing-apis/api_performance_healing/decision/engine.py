import logging
from datetime import datetime
from typing import List, Optional

from ..domain.models import (
    Action, ActionType, ActionStatus, MetricSnapshot,
    PredictionResult, Policy
)

logger = logging.getLogger(__name__)

class DecisionEngine:
    def __init__(self, policies: List[Policy]):
        self.policies = sorted(policies, key=lambda p: p.priority, reverse=True)
        
    def evaluate(self, prediction: PredictionResult, 
                current_metrics: MetricSnapshot) -> Optional[Action]:
        """
        Evaluates prediction against policies to determine necessary actions.
        Returns highest priority action or None if no action needed.
        """
        for policy in self.policies:
            if not policy.enabled:
                continue
                
            if self._matches_conditions(prediction, current_metrics, policy):
                action = self._create_action(policy, prediction.endpoint)
                logger.info(f"Policy {policy.name} triggered action {action.type}")
                return action
                
        return None
    
    def _matches_conditions(self, prediction: PredictionResult,
                          metrics: MetricSnapshot, policy: Policy) -> bool:
        """Evaluates if current state matches policy conditions."""
        try:
            for condition in policy.conditions:
                if not self._evaluate_condition(condition, prediction, metrics):
                    return False
            return True
        except Exception as e:
            logger.error(f"Error evaluating policy {policy.name}: {str(e)}")
            return False
            
    def _evaluate_condition(self, condition: dict,
                          prediction: PredictionResult,
                          metrics: MetricSnapshot) -> bool:
        """Evaluates a single condition against current state."""
        metric_name = condition["metric"]
        operator = condition["operator"]
        threshold = condition["threshold"]
        
        current_value = self._get_metric_value(metric_name, prediction, metrics)
        
        if operator == "gt":
            return current_value > threshold
        elif operator == "lt":
            return current_value < threshold
        elif operator == "gte":
            return current_value >= threshold
        elif operator == "lte":
            return current_value <= threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")
            
    def _get_metric_value(self, metric_name: str,
                         prediction: PredictionResult,
                         metrics: MetricSnapshot) -> float:
        """Gets value for named metric from prediction or current metrics."""
        if metric_name == "predicted_latency":
            return prediction.predicted_latency
        elif metric_name == "risk_level":
            return prediction.risk_level
        elif metric_name == "current_latency":
            return metrics.latency_ms
        elif metric_name == "error_rate":
            return metrics.error_rate
        elif metric_name == "cpu_utilization":
            return metrics.cpu_utilization
        elif metric_name == "memory_utilization":
            return metrics.memory_utilization
        elif metric_name == "cache_hit_rate":
            return metrics.cache_hit_rate or 0.0
        else:
            raise ValueError(f"Unknown metric: {metric_name}")
            
    def _create_action(self, policy: dict, endpoint: str) -> Action:
        """Creates an Action instance from policy definition."""
        return Action(
            id=f"action_{datetime.utcnow().timestamp()}",
            type=ActionType(policy.actions[0]["type"]),
            target_endpoint=endpoint,
            parameters=policy.actions[0].get("parameters", {}),
            status=ActionStatus.PENDING,
            created_at=datetime.utcnow()
        )