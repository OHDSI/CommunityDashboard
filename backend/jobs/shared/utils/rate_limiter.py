"""
Rate limiting utility for API calls.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with burst support.
    """
    
    def __init__(self, 
                 rate: float = 1.0,
                 burst: int = 1,
                 window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            rate: Requests per second
            burst: Maximum burst size
            window: Time window in seconds for tracking
        """
        self.rate = rate
        self.burst = burst
        self.window = window
        self.tokens = burst
        self.last_update = time.time()
        self.request_history = deque()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'throttled_requests': 0,
            'total_wait_time': 0.0
        }
    
    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking if necessary.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        wait_time = 0.0
        current_time = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = current_time - self.last_update
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = current_time
        
        # Wait if not enough tokens
        if self.tokens < tokens:
            wait_time = (tokens - self.tokens) / self.rate
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
            self.tokens = 0
            self.stats['throttled_requests'] += 1
            self.stats['total_wait_time'] += wait_time
        else:
            self.tokens -= tokens
        
        # Track request
        self.request_history.append(time.time())
        self._cleanup_history()
        self.stats['total_requests'] += 1
        
        return wait_time
    
    def _cleanup_history(self):
        """Remove old entries from request history."""
        cutoff = time.time() - self.window
        while self.request_history and self.request_history[0] < cutoff:
            self.request_history.popleft()
    
    def get_current_rate(self) -> float:
        """Get current request rate."""
        self._cleanup_history()
        if not self.request_history:
            return 0.0
        
        time_span = time.time() - self.request_history[0]
        if time_span > 0:
            return len(self.request_history) / time_span
        return 0.0
    
    def reset(self):
        """Reset rate limiter."""
        self.tokens = self.burst
        self.last_update = time.time()
        self.request_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            **self.stats,
            'current_rate': self.get_current_rate(),
            'tokens_available': self.tokens,
            'throttle_rate': self.stats['throttled_requests'] / max(self.stats['total_requests'], 1)
        }


class MultiServiceRateLimiter:
    """
    Manages rate limiters for multiple services.
    """
    
    # Default rate limits per service
    DEFAULT_LIMITS = {
        'pubmed': {'rate': 3.0, 'burst': 10},      # 3 requests/sec
        'youtube': {'rate': 0.5, 'burst': 5},       # 30 requests/min
        'github': {'rate': 1.0, 'burst': 10},       # 60 requests/min (authenticated)
        'discourse': {'rate': 0.3, 'burst': 3},     # 20 requests/min
        'web': {'rate': 0.5, 'burst': 2}            # 30 requests/min
    }
    
    def __init__(self, custom_limits: Dict[str, Dict[str, Any]] = None):
        """
        Initialize multi-service rate limiter.
        
        Args:
            custom_limits: Custom rate limits per service
        """
        self.limiters = {}
        limits = {**self.DEFAULT_LIMITS, **(custom_limits or {})}
        
        for service, config in limits.items():
            self.limiters[service] = RateLimiter(
                rate=config.get('rate', 1.0),
                burst=config.get('burst', 1)
            )
    
    def acquire(self, service: str, tokens: int = 1) -> float:
        """
        Acquire tokens for a specific service.
        
        Args:
            service: Service name
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        if service not in self.limiters:
            # Create default limiter if not exists
            self.limiters[service] = RateLimiter()
        
        return self.limiters[service].acquire(tokens)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all services."""
        return {
            service: limiter.get_stats()
            for service, limiter in self.limiters.items()
        }
    
    def reset(self, service: Optional[str] = None):
        """Reset rate limiter(s)."""
        if service:
            if service in self.limiters:
                self.limiters[service].reset()
        else:
            for limiter in self.limiters.values():
                limiter.reset()