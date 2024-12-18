import pytest
import asyncio
from datetime import datetime
import aiohttp
from aiohttp import web
import numpy as np

from api_performance_prediction.orchestrator import PredictionSystem

class TestPredictionSystem:
    @pytest.fixture
    async def metrics_server(self):
        """Create a mock metrics server for testing"""
        async def metrics_handler(request):
            return web.json_response({
                "latency_ms": 150.0 + np.random.normal(0, 10),
                "cpu_usage": 45.0 + np.random.normal(0, 5),
                "memory_usage": 75.0 + np.random.normal(0, 3),
                "request_count": 1000,
                "error_count": 5
            })

        app = web.Application()
        app.router.add_get('/metrics', metrics_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        
        yield 'http://localhost:8080'
        
        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_end_to_end_prediction(self, metrics_server):
        """Test the entire prediction pipeline"""
        # Initialize prediction system
        system = PredictionSystem(
            endpoints=[metrics_server],
            collection_interval=1,  # 1 second for testing
            prediction_interval=2    # 2 seconds for testing
        )
        
        # Start the system
        task = asyncio.create_task(system.start())
        
        # Wait for some data collection and predictions
        await asyncio.sleep(10)
        
        # Stop the system
        await system.stop()
        await task
        
        # Verify that metrics were collected
        assert len(system.collector._metrics_buffer) > 0
        
        # Verify that predictions were made
        latest_metrics = system.collector._metrics_buffer[-1]
        assert latest_metrics is not None
        assert latest_metrics.latency_ms > 0
        assert latest_metrics.cpu_usage > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, metrics_server):
        """Test system resilience to errors"""
        # Initialize system with invalid endpoint
        system = PredictionSystem(
            endpoints=[metrics_server, "http://invalid-endpoint:9999"],
            collection_interval=1,
            prediction_interval=2
        )
        
        # Start the system
        task = asyncio.create_task(system.start())
        
        # Wait for some processing
        await asyncio.sleep(5)
        
        # Stop the system
        await system.stop()
        await task
        
        # System should continue running despite errors
        assert len(system.collector._metrics_buffer) > 0

    @pytest.mark.asyncio
    async def test_monitoring_integration(self, metrics_server):
        """Test that monitoring is properly integrated"""
        system = PredictionSystem(
            endpoints=[metrics_server],
            collection_interval=1,
            prediction_interval=2
        )
        
        # Start the system
        task = asyncio.create_task(system.start())
        
        # Wait for data collection and monitoring
        await asyncio.sleep(10)
        
        # Stop the system
        await system.stop()
        await task
        
        # Verify that monitoring is active
        assert hasattr(system.monitor, 'historical_mapes')
        assert len(system.monitor.historical_mapes) > 0

    @pytest.mark.asyncio
    async def test_memory_management(self, metrics_server):
        """Test that the system properly manages memory"""
        system = PredictionSystem(
            endpoints=[metrics_server],
            collection_interval=1,
            prediction_interval=2
        )
        
        # Start the system
        task = asyncio.create_task(system.start())
        
        # Wait for substantial data collection
        await asyncio.sleep(15)
        
        # Stop the system
        await system.stop()
        await task
        
        # Verify that buffer size is managed
        assert len(system.collector._metrics_buffer) <= 1000