# api_performance_prediction/orchestrator.py
import asyncio
from typing import List
import logging
from datetime import datetime, timedelta

from .collection.collector import MetricsCollector
from .prediction.preprocessor import DataPreprocessor
from .prediction.model import ModelServer
from .monitoring.monitor import ModelMonitor
from .domain.models import APIMetric, PredictionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionSystem:
    """Main orchestrator for the prediction system"""
    
    def __init__(self, 
                 endpoints: List[str],
                 model_path: str = None,
                 collection_interval: int = 300,  # 5 minutes
                 prediction_interval: int = 300):  # 5 minutes
        self.collector = MetricsCollector(endpoints, collection_interval)
        self.preprocessor = DataPreprocessor()
        self.model_server = ModelServer(model_path)
        self.monitor = ModelMonitor()
        self.prediction_interval = prediction_interval
        self._running = False
        
    async def start(self):
        """Start the prediction system"""
        self._running = True
        logger.info("Starting prediction system...")
        
        # Start collection and prediction loops
        await asyncio.gather(
            self._collection_loop(),
            self._prediction_loop()
        )
    
    async def stop(self):
        """Stop the prediction system"""
        self._running = False
        logger.info("Stopping prediction system...")
    
    async def _collection_loop(self):
        """Run the metrics collection loop"""
        await self.collector.start_collection()
    
    async def _prediction_loop(self):
        """Run the prediction and monitoring loop"""
        while self._running:
            try:
                # Get recent metrics
                recent_metrics = self.collector._metrics_buffer[-24:]  # Last 2 hours
                if not recent_metrics:
                    logger.warning("No metrics available for prediction")
                    continue
                
                # Preprocess data
                features = self.preprocessor.create_feature_vector(recent_metrics)
                
                # Generate predictions
                predictions = self.model_server.predict(features)
                
                # Monitor predictions
                monitoring_results = self.monitor.evaluate_predictions(
                    predictions[-1:],  # Latest prediction
                    recent_metrics[-1:]  # Latest actual
                )
                
                # Log monitoring results
                if monitoring_results.alerts_triggered:
                    logger.warning("Alerts triggered: %s", 
                                 monitoring_results.alerts_triggered)
                
                # Clear old metrics to prevent memory buildup
                if len(self.collector._metrics_buffer) > 1000:  # Keep last ~3 days
                    self.collector._metrics_buffer = self.collector._metrics_buffer[-1000:]
                
            except Exception as e:
                logger.error("Error in prediction loop: %s", e)
            
            await asyncio.sleep(self.prediction_interval)

# Example usage
async def main():
    endpoints = [
        "http://api1.example.com",
        "http://api2.example.com"
    ]
    
    system = PredictionSystem(endpoints)
    
    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())