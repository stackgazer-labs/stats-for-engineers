# examples/self_healing_example.py

import asyncio
import logging
from datetime import datetime

from api_performance_healing.config import Configuration
from api_performance_healing.service import SelfHealingService
from api_performance_healing.domain.models import (
    MetricSnapshot,
    PredictionResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Initialize configuration
        config = Configuration()
        policies = config.get_policies()
        
        # Create and initialize service
        service = SelfHealingService(policies)
        await service.initialize()
        
        # Example prediction and metrics
        prediction = PredictionResult(
            timestamp=datetime.utcnow(),
            endpoint="/api/v1/checkout",
            predicted_latency=600.0,  # High latency prediction
            confidence_interval=(550.0, 650.0),
            risk_level=0.8
        )
        
        current_metrics = MetricSnapshot(
            timestamp=datetime.utcnow(),
            endpoint="/api/v1/checkout",
            request_count=1000,
            latency_ms=550.0,
            error_rate=0.02,
            cpu_utilization=75.0,
            memory_utilization=60.0,
            cache_hit_rate=0.85
        )
        
        # Handle prediction
        logger.info("Handling prediction...")
        result = await service.handle_prediction(prediction, current_metrics)
        
        if result:
            logger.info(f"Action taken: {result.action.type}")
            logger.info(f"Action successful: {result.success}")
            if result.metrics_after:
                logger.info(
                    f"Latency improvement: "
                    f"{result.metrics_before.latency_ms - result.metrics_after.latency_ms}ms"
                )
        else:
            logger.info("No action needed")
            
        # Get healing status
        status = await service.get_healing_status("/api/v1/checkout")
        logger.info(f"Healing status: {status}")
        
        # Proper shutdown
        await service.shutdown()
        
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())