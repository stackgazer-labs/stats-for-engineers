# api_performance_healing/config.py

import logging
from typing import List, Dict, Any

from .domain.models import Policy, ActionType

logger = logging.getLogger(__name__)

DEFAULT_POLICIES = [
    {
        "id": "high_latency_policy",
        "name": "High Latency Response",
        "description": "Responds to predicted high latency by scaling",
        "conditions": [
            {
                "metric": "predicted_latency",
                "operator": "gt",
                "threshold": 500  # ms
            },
            {
                "metric": "cpu_utilization",
                "operator": "gt",
                "threshold": 70  # percent
            }
        ],
        "actions": [
            {
                "type": ActionType.SCALE.value,
                "parameters": {
                    "scale_factor": 1.5,
                    "min_instances": 2
                }
            }
        ],
        "enabled": True,
        "priority": 100
    },
    {
        "id": "error_spike_policy",
        "name": "Error Rate Spike Response",
        "description": "Activates circuit breaker when error rates spike",
        "conditions": [
            {
                "metric": "error_rate",
                "operator": "gt",
                "threshold": 0.05  # 5%
            }
        ],
        "actions": [
            {
                "type": ActionType.CIRCUIT_BREAK.value,
                "parameters": {
                    "timeout_ms": 5000,
                    "error_threshold": 0.1
                }
            }
        ],
        "enabled": True,
        "priority": 90
    },
    {
        "id": "cache_optimization_policy",
        "name": "Cache Performance Optimization",
        "description": "Optimizes cache when hit rates drop",
        "conditions": [
            {
                "metric": "cache_hit_rate",
                "operator": "lt",
                "threshold": 0.80  # 80%
            }
        ],
        "actions": [
            {
                "type": ActionType.ADJUST_CACHE.value,
                "parameters": {
                    "ttl_seconds": 300,
                    "capacity": 1000
                }
            }
        ],
        "enabled": True,
        "priority": 80
    }
]

class Configuration:
    """Configuration manager for the self-healing system."""
    
    def __init__(self, config_dict: Dict[str, Any] = None):
        self.config = config_dict or {}
        
    @classmethod
    def from_file(cls, filepath: str) -> 'Configuration':
        """
        Creates configuration from a JSON or YAML file.
        
        Args:
            filepath: Path to configuration file
            
        Returns:
            Configuration instance
        """
        import json
        import yaml
        
        try:
            with open(filepath, 'r') as f:
                if filepath.endswith('.json'):
                    config = json.load(f)
                elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                    config = yaml.safe_load(f)
                else:
                    raise ValueError("Config file must be JSON or YAML")
                    
            return cls(config)
            
        except Exception as e:
            logger.error(f"Error loading configuration from {filepath}: {str(e)}")
            raise
            
    def get_policies(self) -> List[Policy]:
        """
        Gets healing policies from configuration.
        Falls back to default policies if none specified.
        
        Returns:
            List of Policy objects
        """
        try:
            policy_dicts = self.config.get('policies', DEFAULT_POLICIES)
            return [self._create_policy(p) for p in policy_dicts]
            
        except Exception as e:
            logger.error(f"Error creating policies: {str(e)}")
            raise
            
    def _create_policy(self, policy_dict: dict) -> Policy:
        """Creates a Policy object from dictionary configuration."""
        return Policy(
            id=policy_dict["id"],
            name=policy_dict["name"],
            description=policy_dict["description"],
            conditions=policy_dict["conditions"],
            actions=policy_dict["actions"],
            enabled=policy_dict["enabled"],
            priority=policy_dict["priority"]
        )