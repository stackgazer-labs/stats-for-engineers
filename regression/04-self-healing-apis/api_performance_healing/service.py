# api_performance_healing/service.py

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from .domain.models import (
    Action, ActionResult, MetricSnapshot, PredictionResult, Policy
)
from .decision.engine import DecisionEngine
from .actions.orchestrator import ActionOrchestrator
from .feedback.action_tracker import ActionTracker

logger = logging.getLogger(__name__)

class SelfHealingService:
    """
    Main service class that coordinates all self-healing components.
    Provides a high-level interface for autonomous API performance management.
    """
    
    def __init__(self, policies: List[Policy]):
        """
        Initializes the self-healing service with specified policies.
        
        Args:
            policies: List of policies that define when and how to take action
        """
        self.decision_engine = DecisionEngine(policies)
        self.action_orchestrator = ActionOrchestrator()
        self.action_tracker = ActionTracker()
        
        # Track active healing operations
        self.active_operations: Dict[str, datetime] = {}
        
    async def handle_prediction(self, prediction: PredictionResult,
                              current_metrics: MetricSnapshot) -> Optional[ActionResult]:
        """
        Handles a new prediction by evaluating it and taking appropriate action.
        
        Args:
            prediction: The prediction result to evaluate
            current_metrics: Current system metrics
            
        Returns:
            ActionResult if action was taken, None otherwise
        """
        try:
            # Check if healing is already in progress
            if self._is_healing_in_progress(prediction.endpoint):
                logger.info(f"Healing already in progress for {prediction.endpoint}")
                return None
                
            # Determine if action is needed
            action = await self.decision_engine.evaluate(
                prediction, current_metrics
            )
            
            if not action:
                logger.debug(f"No action needed for {prediction.endpoint}")
                return None
                
            # Check if this type of action has been effective
            if not self.action_tracker.should_try_action(
                prediction.endpoint, action.type
            ):
                logger.warning(
                    f"Skipping {action.type} for {prediction.endpoint} "
                    "due to poor historical effectiveness"
                )
                return None
                
            # Execute the action
            logger.info(f"Executing {action.type} for {prediction.endpoint}")
            self.active_operations[prediction.endpoint] = datetime.utcnow()
            
            result = await self.action_orchestrator.execute_action(
                action, current_metrics
            )
            
            # Record the result
            await self.action_tracker.record_action_result(result)
            
            # Clean up tracking
            if prediction.endpoint in self.active_operations:
                del self.active_operations[prediction.endpoint]
                
            return result
            
        except Exception as e:
            logger.error(f"Error handling prediction: {str(e)}")
            if prediction.endpoint in self.active_operations:
                del self.active_operations[prediction.endpoint]
            raise
            
    async def get_healing_status(self, endpoint: str) -> dict:
        """
        Gets current healing status and historical effectiveness for an endpoint.
        
        Args:
            endpoint: The API endpoint to check
            
        Returns:
            Dict containing status and effectiveness metrics
        """
        try:
            # Get active status
            is_active = self._is_healing_in_progress(endpoint)
            start_time = self.active_operations.get(endpoint)
            
            # Get historical effectiveness
            trends = await self.action_tracker.analyze_trends(endpoint)
            best_action = self.action_tracker.get_best_action_type(endpoint)
            
            return {
                "active_healing": is_active,
                "healing_start_time": start_time,
                "historical_trends": trends,
                "most_effective_action": best_action.value if best_action else None
            }
            
        except Exception as e:
            logger.error(f"Error getting healing status: {str(e)}")
            raise
            
    def _is_healing_in_progress(self, endpoint: str) -> bool:
        """
        Checks if healing is currently in progress for an endpoint.
        
        Args:
            endpoint: The API endpoint to check
            
        Returns:
            bool indicating if healing is in progress
        """
        return endpoint in self.active_operations
        
    async def initialize(self) -> None:
        """
        Initializes all components and starts background tasks.
        Should be called before using the service.
        """
        try:
            # Initialize components that need it
            await self.action_orchestrator.initialize()
            
            logger.info("Self-healing service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize self-healing service: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """
        Cleanly shuts down the service and all its components.
        Should be called before application exit.
        """
        try:
            # Wait for active operations to complete
            while self.active_operations:
                logger.info("Waiting for active healing operations to complete...")
                await asyncio.sleep(1)
                
            # Shutdown components
            await self.action_orchestrator.shutdown()
            
            logger.info("Self-healing service shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {str(e)}")
            raise