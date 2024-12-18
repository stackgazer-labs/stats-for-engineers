import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

from ..domain.models import Action, ActionResult, ActionType, MetricSnapshot

logger = logging.getLogger(__name__)

class ActionEffectiveness:
    def __init__(self, action_type: ActionType):
        self.action_type = action_type
        self.total_attempts = 0
        self.successful_attempts = 0
        self.average_improvement = 0.0
        self.average_duration_ms = 0.0
        self.side_effects = []
        self.last_updated = datetime.utcnow()

class ActionTracker:
    def __init__(self):
        # Track effectiveness per endpoint and action type
        self.effectiveness: Dict[str, Dict[ActionType, ActionEffectiveness]] = {}
        
        # Store recent action results for trend analysis
        self.recent_results: Dict[str, List[ActionResult]] = {}
        
        # Time window for recent results (24 hours)
        self.history_window = timedelta(hours=24)
        
        # Thresholds for effectiveness
        self.min_success_rate = 0.7
        self.min_improvement = 0.2
        
    async def record_action_result(self, result: ActionResult) -> None:
        """
        Records and analyzes the result of a healing action.
        Updates effectiveness metrics and identifies patterns.
        """
        try:
            endpoint = result.action.target_endpoint
            action_type = result.action.type
            
            # Initialize tracking if needed
            if endpoint not in self.effectiveness:
                self.effectiveness[endpoint] = {}
            if action_type not in self.effectiveness[endpoint]:
                self.effectiveness[endpoint][action_type] = ActionEffectiveness(action_type)
                
            # Update effectiveness metrics
            effectiveness = self.effectiveness[endpoint][action_type]
            effectiveness.total_attempts += 1
            if result.success:
                effectiveness.successful_attempts += 1
                
            # Calculate metric improvement
            improvement = self._calculate_improvement(result)
            if improvement is not None:
                # Update running average
                effectiveness.average_improvement = (
                    (effectiveness.average_improvement * (effectiveness.total_attempts - 1) +
                     improvement) / effectiveness.total_attempts
                )
                
            # Update duration average
            effectiveness.average_duration_ms = (
                (effectiveness.average_duration_ms * (effectiveness.total_attempts - 1) +
                 result.duration_ms) / effectiveness.total_attempts
            )
                
            # Record side effects
            if result.side_effects:
                effectiveness.side_effects.extend(result.side_effects)
                
            effectiveness.last_updated = datetime.utcnow()
            
            # Store result for trend analysis
            if endpoint not in self.recent_results:
                self.recent_results[endpoint] = []
            self.recent_results[endpoint].append(result)
            
            # Clean up old results
            self._cleanup_old_results(endpoint)
            
            # Log insights
            await self._log_insights(endpoint, action_type)
            
        except Exception as e:
            logger.error(f"Error recording action result: {str(e)}")

    def get_effectiveness(self, endpoint: str,
                        action_type: ActionType) -> Optional[ActionEffectiveness]:
        """
        Returns effectiveness metrics for a specific endpoint and action type.
        """
        return self.effectiveness.get(endpoint, {}).get(action_type)

    def should_try_action(self, endpoint: str,
                         action_type: ActionType) -> bool:
        """
        Determines if an action type should be attempted based on past effectiveness.
        """
        effectiveness = self.get_effectiveness(endpoint, action_type)
        if not effectiveness:
            return True  # No history, worth trying
            
        # Check success rate
        success_rate = (
            effectiveness.successful_attempts / effectiveness.total_attempts
            if effectiveness.total_attempts > 0 else 0
        )
        
        # Check average improvement
        if success_rate < self.min_success_rate:
            logger.warning(
                f"Action {action_type.value} has low success rate for {endpoint}: "
                f"{success_rate:.2f}"
            )
            return False
            
        if effectiveness.average_improvement < self.min_improvement:
            logger.warning(
                f"Action {action_type.value} shows minimal improvement for {endpoint}: "
                f"{effectiveness.average_improvement:.2f}"
            )
            return False
            
        return True

    def get_best_action_type(self, endpoint: str) -> Optional[ActionType]:
        """
        Returns the historically most effective action type for an endpoint.
        """
        if endpoint not in self.effectiveness:
            return None
            
        best_type = None
        best_improvement = -1
        
        for action_type, effectiveness in self.effectiveness[endpoint].items():
            if effectiveness.average_improvement > best_improvement:
                best_improvement = effectiveness.average_improvement
                best_type = action_type
                
        return best_type

    async def analyze_trends(self, endpoint: str) -> dict:
        """
        Analyzes trends in action effectiveness over time.
        """
        if endpoint not in self.recent_results:
            return {}
            
        results = self.recent_results[endpoint]
        if not results:
            return {}
            
        # Calculate success rate over time
        success_rates = []
        window_size = 5
        for i in range(0, len(results), window_size):
            window = results[i:i + window_size]
            success_rate = sum(1 for r in window if r.success) / len(window)
            success_rates.append(success_rate)
            
        # Calculate improvement trends
        improvements = [
            self._calculate_improvement(r) 
            for r in results 
            if self._calculate_improvement(r) is not None
        ]
        
        # Calculate duration trends
        durations = [r.duration_ms for r in results]
        
        return {
            "success_rate_trend": success_rates,
            "average_improvement_trend": self._calculate_trend(improvements),
            "duration_trend": self._calculate_trend(durations),
            "common_side_effects": self._analyze_side_effects(results)
        }

    def _calculate_improvement(self, result: ActionResult) -> Optional[float]:
        """
        Calculates the improvement in metrics after an action.
        Returns improvement as a percentage or None if not calculable.
        """
        if not result.metrics_before or not result.metrics_after:
            return None
            
        # Calculate improvement based on action type
        if result.action.type == ActionType.SCALE:
            # For scaling, look at latency improvement
            before_latency = result.metrics_before.latency_ms
            after_latency = result.metrics_after.latency_ms
            if before_latency > 0:
                return (before_latency - after_latency) / before_latency
                
        elif result.action.type == ActionType.CIRCUIT_BREAK:
            # For circuit breaking, look at error rate reduction
            before_errors = result.metrics_before.error_rate
            after_errors = result.metrics_after.error_rate
            if before_errors > 0:
                return (before_errors - after_errors) / before_errors
                
        elif result.action.type == ActionType.ADJUST_CACHE:
            # For cache adjustments, look at latency and hit rate
            before_latency = result.metrics_before.latency_ms
            after_latency = result.metrics_after.latency_ms
            if before_latency > 0:
                return (before_latency - after_latency) / before_latency
                
        elif result.action.type == ActionType.ADJUST_LOAD_BALANCER:
            # For load balancing, look at overall latency improvement
            before_latency = result.metrics_before.latency_ms
            after_latency = result.metrics_after.latency_ms
            if before_latency > 0:
                return (before_latency - after_latency) / before_latency
                
        return None

    def _calculate_trend(self, values: List[float]) -> dict:
        """
        Calculates trend statistics for a series of values.
        """
        if not values:
            return {
                "trend": 0,
                "volatility": 0
            }
            
        # Calculate linear trend
        x = np.arange(len(values))
        z = np.polyfit(x, values, 1)
        trend = z[0]  # Slope indicates trend direction and magnitude
        
        # Calculate volatility
        volatility = np.std(values) if len(values) > 1 else 0
        
        return {
            "trend": float(trend),
            "volatility": float(volatility)
        }

    def _analyze_side_effects(self, results: List[ActionResult]) -> List[dict]:
        """
        Analyzes common side effects and their frequency.
        """
        side_effect_counts = {}
        
        for result in results:
            for effect in result.side_effects:
                if effect in side_effect_counts:
                    side_effect_counts[effect] += 1
                else:
                    side_effect_counts[effect] = 1
                    
        # Sort by frequency
        sorted_effects = sorted(
            side_effect_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"effect": effect, "frequency": count}
            for effect, count in sorted_effects
        ]

    def _cleanup_old_results(self, endpoint: str) -> None:
        """
        Removes results outside the history window.
        """
        if endpoint not in self.recent_results:
            return
            
        cutoff_time = datetime.utcnow() - self.history_window
        self.recent_results[endpoint] = [
            r for r in self.recent_results[endpoint]
            if r.action.created_at > cutoff_time
        ]

    async def _log_insights(self, endpoint: str, action_type: ActionType) -> None:
        """
        Logs insights about action effectiveness.
        """
        effectiveness = self.get_effectiveness(endpoint, action_type)
        if not effectiveness:
            return
            
        success_rate = (
            effectiveness.successful_attempts / effectiveness.total_attempts
            if effectiveness.total_attempts > 0 else 0
        )
        
        logger.info(
            f"Action effectiveness for {endpoint} - {action_type.value}:\n"
            f"Success rate: {success_rate:.2f}\n"
            f"Average improvement: {effectiveness.average_improvement:.2f}\n"
            f"Average duration: {effectiveness.average_duration_ms:.0f}ms"
        )