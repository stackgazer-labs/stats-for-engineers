import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitConfiguration:
    def __init__(self, timeout_ms: int, error_threshold: float,
                 reset_timeout_seconds: int = 60):
        self.timeout_ms = timeout_ms
        self.error_threshold = error_threshold
        self.reset_timeout_seconds = reset_timeout_seconds

class CircuitBreaker:
    def __init__(self):
        self.configs: Dict[str, CircuitConfiguration] = {}
        self.states: Dict[str, CircuitState] = {}
        self.error_counts: Dict[str, int] = {}
        self.request_counts: Dict[str, int] = {}
        self.last_state_change: Dict[str, datetime] = {}
        
    async def configure(self, endpoint: str, timeout_ms: int,
                       error_threshold: float) -> None:
        """
        Configures circuit breaker parameters for an endpoint.
        """
        try:
            logger.info(
                f"Configuring circuit breaker for {endpoint}: "
                f"timeout={timeout_ms}ms, error_threshold={error_threshold}"
            )
            
            self.configs[endpoint] = CircuitConfiguration(
                timeout_ms=timeout_ms,
                error_threshold=error_threshold
            )
            
            if endpoint not in self.states:
                self.states[endpoint] = CircuitState.CLOSED
                self.error_counts[endpoint] = 0
                self.request_counts[endpoint] = 0
                self.last_state_change[endpoint] = datetime.utcnow()
                
            # Start background monitoring if not already running
            asyncio.create_task(self._monitor_circuit(endpoint))
            
        except Exception as e:
            logger.error(f"Error configuring circuit breaker for {endpoint}: {str(e)}")
            raise

    async def should_allow_request(self, endpoint: str) -> bool:
        """
        Determines if a request should be allowed through.
        """
        if endpoint not in self.states:
            return True
            
        state = self.states[endpoint]
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            # Allow a limited number of requests through
            return self.request_counts[endpoint] < 5

    async def record_result(self, endpoint: str, success: bool,
                          latency_ms: float) -> None:
        """
        Records the result of a request for circuit breaker logic.
        """
        if endpoint not in self.states:
            return
            
        config = self.configs[endpoint]
        self.request_counts[endpoint] += 1
        
        if not success or latency_ms > config.timeout_ms:
            self.error_counts[endpoint] += 1
            
        # Check if we need to open the circuit
        if self.states[endpoint] == CircuitState.CLOSED:
            error_rate = self.error_counts[endpoint] / max(1, self.request_counts[endpoint])
            if error_rate >= config.error_threshold:
                await self._open_circuit(endpoint)

    async def _monitor_circuit(self, endpoint: str) -> None:
        """
        Background task to monitor circuit state and attempt recovery.
        """
        while True:
            try:
                if endpoint not in self.states:
                    return
                    
                config = self.configs[endpoint]
                state = self.states[endpoint]
                
                if state == CircuitState.OPEN:
                    # Check if we should try recovery
                    time_in_state = datetime.utcnow() - self.last_state_change[endpoint]
                    if time_in_state.total_seconds() >= config.reset_timeout_seconds:
                        await self._half_open_circuit(endpoint)
                        
                elif state == CircuitState.HALF_OPEN:
                    # Check if recovery is successful
                    if self.request_counts[endpoint] >= 5:
                        error_rate = (
                            self.error_counts[endpoint] / self.request_counts[endpoint]
                        )
                        if error_rate < config.error_threshold:
                            await self._close_circuit(endpoint)
                        else:
                            await self._open_circuit(endpoint)
                            
            except Exception as e:
                logger.error(f"Error monitoring circuit for {endpoint}: {str(e)}")
                
            await asyncio.sleep(5)

    async def _open_circuit(self, endpoint: str) -> None:
        """
        Opens the circuit, preventing requests from going through.
        """
        logger.warning(f"Opening circuit for {endpoint}")
        self.states[endpoint] = CircuitState.OPEN
        self.last_state_change[endpoint] = datetime.utcnow()
        self._reset_counters(endpoint)

    async def _half_open_circuit(self, endpoint: str) -> None:
        """
        Sets circuit to half-open to test recovery.
        """
        logger.info(f"Setting circuit half-open for {endpoint}")
        self.states[endpoint] = CircuitState.HALF_OPEN
        self.last_state_change[endpoint] = datetime.utcnow()
        self._reset_counters(endpoint)

    async def _close_circuit(self, endpoint: str) -> None:
        """
        Closes the circuit, allowing normal operation.
        """
        logger.info(f"Closing circuit for {endpoint}")
        self.states[endpoint] = CircuitState.CLOSED
        self.last_state_change[endpoint] = datetime.utcnow()
        self._reset_counters(endpoint)

    def _reset_counters(self, endpoint: str) -> None:
        """
        Resets error and request counters for an endpoint.
        """
        self.error_counts[endpoint] = 0
        self.request_counts[endpoint] = 0