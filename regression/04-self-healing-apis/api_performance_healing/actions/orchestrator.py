import logging
from datetime import datetime
from typing import Dict, Optional

from ..domain.models import Action, ActionResult, ActionStatus, MetricSnapshot
from .scaling import AutoScaler
from .circuit_breaker import CircuitBreaker 
from .caching import CacheManager
from .load_balancer import LoadBalancer

logger = logging.getLogger(__name__)

class ActionOrchestrator:
    def __init__(self):
        self.auto_scaler = AutoScaler()
        self.circuit_breaker = CircuitBreaker()
        self.cache_manager = CacheManager()
        self.load_balancer = LoadBalancer()
        
        # Map action types to their handlers
        self.handlers = {
            "scale": self._handle_scaling,
            "circuit_break": self._handle_circuit_breaker,
            "adjust_cache": self._handle_cache_adjustment,
            "adjust_load_balancer": self._handle_load_balancer
        }
        
        # Track in-progress actions
        self.active_actions: Dict[str, Action] = {}
        
    async def execute_action(self, action: Action, 
                           current_metrics: MetricSnapshot) -> ActionResult:
        """
        Executes the given action and returns its result.
        Implements safety checks and rollback capabilities.
        """
        if action.id in self.active_actions:
            logger.warning(f"Action {action.id} already in progress")
            return self._create_failed_result(
                action, current_metrics, "Action already in progress"
            )
            
        self.active_actions[action.id] = action
        start_time = datetime.utcnow()
        
        try:
            # Update action status
            action.status = ActionStatus.IN_PROGRESS
            
            # Get appropriate handler
            handler = self.handlers.get(action.type.value)
            if not handler:
                raise ValueError(f"No handler for action type: {action.type}")
                
            # Execute the action
            metrics_after = await handler(action, current_metrics)
            
            # Mark as completed
            action.status = ActionStatus.COMPLETED
            action.completed_at = datetime.utcnow()
            
            duration_ms = (action.completed_at - start_time).total_seconds() * 1000
            
            return ActionResult(
                action=action,
                metrics_before=current_metrics,
                metrics_after=metrics_after,
                success=True,
                duration_ms=duration_ms,
                side_effects=[]
            )
            
        except Exception as e:
            logger.error(f"Action {action.id} failed: {str(e)}")
            action.status = ActionStatus.FAILED
            action.error_message = str(e)
            
            return self._create_failed_result(
                action, current_metrics, str(e)
            )
            
        finally:
            del self.active_actions[action.id]
            
    async def _handle_scaling(self, action: Action, 
                            metrics: MetricSnapshot) -> Optional[MetricSnapshot]:
        """Handles auto-scaling actions."""
        scale_factor = action.parameters.get("scale_factor", 1.5)
        await self.auto_scaler.scale(
            action.target_endpoint, scale_factor, metrics
        )
        return await self._get_updated_metrics(action.target_endpoint)
        
    async def _handle_circuit_breaker(self, action: Action,
                                    metrics: MetricSnapshot) -> Optional[MetricSnapshot]:
        """Handles circuit breaker actions."""
        timeout_ms = action.parameters.get("timeout_ms", 5000)
        error_threshold = action.parameters.get("error_threshold", 0.5)
        
        await self.circuit_breaker.configure(
            action.target_endpoint,
            timeout_ms=timeout_ms,
            error_threshold=error_threshold
        )
        return await self._get_updated_metrics(action.target_endpoint)
        
    async def _handle_cache_adjustment(self, action: Action,
                                     metrics: MetricSnapshot) -> Optional[MetricSnapshot]:
        """Handles cache adjustment actions."""
        ttl_seconds = action.parameters.get("ttl_seconds", 300)
        capacity = action.parameters.get("capacity", 1000)
        
        await self.cache_manager.adjust(
            action.target_endpoint,
            ttl_seconds=ttl_seconds,
            capacity=capacity
        )
        return await self._get_updated_metrics(action.target_endpoint)
        
    async def _handle_load_balancer(self, action: Action,
                                  metrics: MetricSnapshot) -> Optional[MetricSnapshot]:
        """Handles load balancer adjustment actions."""
        algorithm = action.parameters.get("algorithm", "round_robin")
        weights = action.parameters.get("weights", {})
        
        await self.load_balancer.adjust(
            action.target_endpoint,
            algorithm=algorithm,
            weights=weights
        )
        return await self._get_updated_metrics(action.target_endpoint)
        
    async def _get_updated_metrics(self, endpoint: str) -> Optional[MetricSnapshot]:
        """Gets fresh metrics after action execution."""
        # In real implementation, this would fetch from your metrics system
        pass
        
    def _create_failed_result(self, action: Action, metrics: MetricSnapshot,
                            error: str) -> ActionResult:
        """Creates an ActionResult for a failed action."""
        return ActionResult(
            action=action,
            metrics_before=metrics,
            metrics_after=None,
            success=False,
            duration_ms=0,
            side_effects=[f"Error: {error}"]
        )