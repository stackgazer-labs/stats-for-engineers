import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class LoadBalancingAlgorithm(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RESPONSE_TIME = "response_time"

class ServerHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class BackendServer:
    def __init__(self, id: str, address: str):
        self.id = id
        self.address = address
        self.health = ServerHealth.HEALTHY
        self.active_connections = 0
        self.response_time_ms = 0.0
        self.weight = 1.0
        self.last_health_check = datetime.utcnow()

class LoadBalancer:
    def __init__(self):
        self.servers: Dict[str, List[BackendServer]] = {}
        self.algorithms: Dict[str, LoadBalancingAlgorithm] = {}
        self.health_check_interval = 30  # seconds
        
    async def adjust(self, endpoint: str, algorithm: str,
                    weights: Optional[Dict[str, float]] = None) -> None:
        """
        Adjusts load balancing strategy for an endpoint.
        """
        try:
            logger.info(
                f"Adjusting load balancer for {endpoint}: "
                f"algorithm={algorithm}, weights={weights}"
            )
            
            # Validate and set algorithm
            try:
                self.algorithms[endpoint] = LoadBalancingAlgorithm(algorithm)
            except ValueError:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
                
            # Update server weights if provided
            if weights and endpoint in self.servers:
                await self._update_weights(endpoint, weights)
                
            # Apply new configuration
            await self._apply_load_balancer_config(endpoint)
            
            # Start health checks if not already running
            asyncio.create_task(self._health_check_loop(endpoint))
            
        except Exception as e:
            logger.error(f"Error adjusting load balancer for {endpoint}: {str(e)}")
            raise

    async def _update_weights(self, endpoint: str,
                            weights: Dict[str, float]) -> None:
        """
        Updates weights for backend servers.
        """
        for server in self.servers[endpoint]:
            if server.id in weights:
                server.weight = max(0.0, min(1.0, weights[server.id]))
                logger.info(f"Updated weight for {server.id} to {server.weight}")

    async def _apply_load_balancer_config(self, endpoint: str) -> None:
        """
        Applies load balancer configuration to the actual infrastructure.
        In real implementation, this would update your load balancer service.
        """
        try:
            algorithm = self.algorithms[endpoint]
            
            # Example: Update NGINX configuration
            # await self._update_nginx_config(endpoint, algorithm)
            
            # Example: Update cloud load balancer
            # await self._update_cloud_load_balancer(endpoint, algorithm)
            
            # Simulate configuration delay
            await asyncio.sleep(2)
            
            logger.info(
                f"Applied load balancer configuration for {endpoint}: {algorithm.value}"
            )
            
        except Exception as e:
            logger.error(f"Failed to apply load balancer config: {str(e)}")
            raise

    async def _health_check_loop(self, endpoint: str) -> None:
        """
        Continuously monitors backend server health.
        """
        while True:
            try:
                if endpoint not in self.servers:
                    return
                    
                for server in self.servers[endpoint]:
                    health = await self._check_server_health(server)
                    
                    if health != server.health:
                        logger.info(
                            f"Health status change for {server.id}: "
                            f"{server.health.value} -> {health.value}"
                        )
                        server.health = health
                        
                        # Adjust load balancing if server health changed
                        if health == ServerHealth.UNHEALTHY:
                            await self._handle_unhealthy_server(endpoint, server)
                            
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                
            await asyncio.sleep(self.health_check_interval)

    async def _check_server_health(self, server: BackendServer) -> ServerHealth:
        """
        Checks health of a backend server.
        In real implementation, this would make actual health check requests.
        """
        try:
            # Example: Make health check request
            # response = await self._make_health_check_request(server.address)
            # return self._evaluate_health(response)
            
            # Simulate health check
            return ServerHealth.HEALTHY
            
        except Exception as e:
            logger.error(f"Health check failed for {server.id}: {str(e)}")
            return ServerHealth.UNHEALTHY

    async def _handle_unhealthy_server(self, endpoint: str,
                                     server: BackendServer) -> None:
        """
        Handles an unhealthy server by adjusting load balancing.
        """
        try:
            # Remove server from rotation
            server.weight = 0.0
            
            # Redistribute weight to healthy servers
            healthy_servers = [
                s for s in self.servers[endpoint]
                if s.health == ServerHealth.HEALTHY and s.id != server.id
            ]
            
            if healthy_servers:
                redistributed_weight = 1.0 / len(healthy_servers)
                for healthy_server in healthy_servers:
                    healthy_server.weight = redistributed_weight
                    
            # Apply updated configuration
            await self._apply_load_balancer_config(endpoint)
            
        except Exception as e:
            logger.error(
                f"Failed to handle unhealthy server {server.id}: {str(e)}"
            )
            
    async def get_metrics(self, endpoint: str) -> dict:
        """
        Returns current load balancer metrics.
        In real implementation, this would query your load balancer service.
        """
        return {
            "total_requests": 1000,
            "active_connections": 50,
            "healthy_backends": 3,
            "average_response_time_ms": 150
        }