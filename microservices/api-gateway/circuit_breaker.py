from enum import Enum
from datetime import datetime, timedelta
import logging
from typing import Optional, Callable, Any, Dict
import asyncio

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Service considered down
    HALF_OPEN = "HALF_OPEN"  # Testing if service is back

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_timeout = half_open_timeout
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.services: Dict[str, CircuitState] = {}
        
    def get_service_state(self, service_name: str) -> CircuitState:
        """Get the current state of a service."""
        return self.services.get(service_name, CircuitState.CLOSED)
        
    async def call_service(
        self,
        service_name: str,
        func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Execute a service call with circuit breaker logic."""
        current_state = self.get_service_state(service_name)
        
        if current_state == CircuitState.OPEN:
            if self._should_attempt_recovery(service_name):
                self._set_service_state(service_name, CircuitState.HALF_OPEN)
            else:
                raise Exception(f"Circuit breaker is OPEN for service: {service_name}")
                
        try:
            result = await func(*args, **kwargs)
            if current_state == CircuitState.HALF_OPEN:
                self._set_service_state(service_name, CircuitState.CLOSED)
            return result
            
        except Exception as e:
            self._handle_failure(service_name)
            raise e
            
    def _handle_failure(self, service_name: str) -> None:
        """Handle a service failure."""
        current_state = self.get_service_state(service_name)
        
        if current_state == CircuitState.CLOSED:
            self.failures += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failures >= self.failure_threshold:
                self._set_service_state(service_name, CircuitState.OPEN)
                logger.warning(f"Circuit breaker OPENED for service: {service_name}")
                
        elif current_state == CircuitState.HALF_OPEN:
            self._set_service_state(service_name, CircuitState.OPEN)
            self.last_failure_time = datetime.utcnow()
            logger.warning(f"Service {service_name} failed in HALF-OPEN state, returning to OPEN")
            
    def _should_attempt_recovery(self, service_name: str) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if not self.last_failure_time:
            return True
            
        recovery_time = datetime.utcnow() - self.last_failure_time
        return recovery_time.total_seconds() >= self.recovery_timeout
        
    def _set_service_state(self, service_name: str, state: CircuitState) -> None:
        """Update the state of a service."""
        self.services[service_name] = state
        if state == CircuitState.CLOSED:
            self.failures = 0
            self.last_failure_time = None
        logger.info(f"Service {service_name} state changed to: {state.value}")

# Create a global circuit breaker instance
circuit_breaker = CircuitBreaker() 