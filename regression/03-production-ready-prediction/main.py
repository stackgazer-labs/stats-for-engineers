import asyncio
from api_performance_prediction.orchestrator import PredictionSystem

async def main():
    # Define your API endpoints
    endpoints = [
        "http://your-api1.com/metrics",
        "http://your-api2.com/metrics"
    ]
    
    # Create and start the prediction system
    system = PredictionSystem(endpoints)
    
    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()

if __name__ == "__main__":
    asyncio.run(main())