import asyncio
from datetime import datetime
from typing import List, Dict
import aiohttp
from ..domain.models import APIMetric

class MetricsCollector:
    """Collects metrics from various API endpoints"""
    
    def __init__(self, endpoints: List[str], collection_interval: int = 60):
        self.endpoints = endpoints
        self.collection_interval = collection_interval
        self._running = False
        self._metrics_buffer: List[APIMetric] = []
        
    async def start_collection(self):
        """Start the metrics collection process"""
        self._running = True
        while self._running:
            metrics = await self._collect_current_metrics()
            self._metrics_buffer.extend(metrics)
            await asyncio.sleep(self.collection_interval)
    
    async def _collect_current_metrics(self) -> List[APIMetric]:
        """Collect current metrics from all endpoints"""
        async with aiohttp.ClientSession() as session:
            tasks = [self._collect_endpoint_metrics(session, endpoint) 
                    for endpoint in self.endpoints]
            return await asyncio.gather(*tasks)
        
    async def _collect_endpoint_metrics(self, 
                                     session: aiohttp.ClientSession, 
                                     endpoint: str) -> APIMetric:
        """Collect metrics for a single endpoint"""
        try:
            async with session.get(f"{endpoint}/metrics") as response:
                data = await response.json()
                return APIMetric(
                    timestamp=datetime.now(),
                    endpoint=endpoint,
                    latency_ms=data["latency_ms"],
                    status_code=response.status,
                    cpu_usage=data["cpu_usage"],
                    memory_usage=data["memory_usage"],
                    request_count=data["request_count"],
                    error_count=data["error_count"]
                )
        except Exception as e:
            # In production, we'd want proper error handling and logging
            print(f"Error collecting metrics for {endpoint}: {e}")
            return None