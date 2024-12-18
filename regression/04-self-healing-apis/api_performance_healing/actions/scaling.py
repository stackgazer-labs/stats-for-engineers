import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..domain.models import MetricSnapshot

logger = logging.getLogger(__name__)

class AutoScaler:
    def __init__(self):
        self.min_instances = 2
        self.max_instances = 10
        self.cooldown_minutes = 5
        self.last_scale_operations: Dict[str, datetime] = {}
        
    async def scale(self, endpoint: str, scale_factor: float, 
                   current_metrics: MetricSnapshot) -> None:
        """
        Scales the service running the endpoint by the given factor.
        Includes safety checks and gradual scaling.
        """
        try:
            # Check cooldown period
            if not self._can_scale(endpoint):
                logger.info(f"Scaling for {endpoint} in cooldown period")
                return

            # Get current instance count
            current_instances = await self._get_instance_count(endpoint)
            if not current_instances:
                raise ValueError(f"Could not determine instance count for {endpoint}")

            # Calculate target instances
            target_instances = max(
                self.min_instances,
                min(
                    self.max_instances,
                    round(current_instances * scale_factor)
                )
            )

            if target_instances == current_instances:
                logger.info(f"No scaling needed for {endpoint}")
                return

            logger.info(
                f"Scaling {endpoint} from {current_instances} to {target_instances} instances"
            )

            # Scale gradually if increasing by more than 2x
            if target_instances > current_instances * 2:
                await self._gradual_scale_up(endpoint, current_instances, target_instances)
            else:
                await self._scale_to(endpoint, target_instances)

            # Record scaling operation
            self.last_scale_operations[endpoint] = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error scaling {endpoint}: {str(e)}")
            raise

    async def _gradual_scale_up(self, endpoint: str, 
                               current: int, target: int) -> None:
        """
        Gradually scales up service to avoid overwhelming the system.
        """
        step_size = max(1, (target - current) // 3)
        current_step = current

        while current_step < target:
            next_step = min(target, current_step + step_size)
            await self._scale_to(endpoint, next_step)
            
            # Wait for instances to be ready
            await self._wait_for_healthy_instances(endpoint, next_step)
            current_step = next_step

    async def _scale_to(self, endpoint: str, instance_count: int) -> None:
        """
        Scales the service to the specified instance count.
        In real implementation, this would use cloud provider's API.
        """
        try:
            # Example: AWS Auto Scaling API call
            # await boto3.client('application-autoscaling').update_target(...)
            
            # Example: Kubernetes scaling
            # await kubernetes.client.AppsV1Api().patch_namespaced_deployment_scale(...)
            
            # Simulated delay for demonstration
            await asyncio.sleep(2)
            
            logger.info(f"Scaled {endpoint} to {instance_count} instances")
        except Exception as e:
            logger.error(f"Failed to scale {endpoint}: {str(e)}")
            raise

    async def _get_instance_count(self, endpoint: str) -> Optional[int]:
        """
        Gets current instance count for the service.
        In real implementation, this would query your infrastructure.
        """
        # Simulated instance count
        return 2

    async def _wait_for_healthy_instances(self, endpoint: str, 
                                        target_count: int) -> None:
        """
        Waits for instances to be healthy before continuing scaling.
        """
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            healthy_count = await self._get_healthy_instance_count(endpoint)
            if healthy_count >= target_count:
                logger.info(f"{endpoint} scaled successfully")
                return
                
            attempt += 1
            await asyncio.sleep(10)
            
        raise TimeoutError(f"Timeout waiting for {endpoint} instances to be healthy")

    async def _get_healthy_instance_count(self, endpoint: str) -> int:
        """
        Gets count of healthy instances.
        In real implementation, this would check health endpoints.
        """
        # Simulated health check
        return 2

    def _can_scale(self, endpoint: str) -> bool:
        """
        Checks if endpoint can be scaled based on cooldown period.
        """
        last_scale = self.last_scale_operations.get(endpoint)
        if not last_scale:
            return True
            
        cooldown_end = last_scale + timedelta(minutes=self.cooldown_minutes)
        return datetime.utcnow() >= cooldown_end