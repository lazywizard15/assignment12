import os
from datetime import timedelta
from typing import Optional

# CRITICAL FIX: Use the official, modern 'redis' library client for async operations
# The old 'aioredis' caused the TypeError: duplicate base class TimeoutError.
import redis.asyncio as redis 

# Configuration: We get the URL from settings, falling back to a default if necessary
from app.core.config import get_settings

settings = get_settings()

REDIS_CLIENT: Optional[redis.Redis] = None

async def get_redis_client() -> redis.Redis:
    """
    Initializes a session-scoped asynchronous Redis client connection 
    and performs a health check via PING.
    """
    global REDIS_CLIENT
    
    # Check if the client has already been initialized
    if REDIS_CLIENT is None:
        try:
            # Use the URL from settings, falling back to a standard localhost URL
            redis_url = settings.REDIS_URL or "redis://localhost:6379/0"

            # Decode responses ensures we get strings, not bytes, back
            REDIS_CLIENT = redis.from_url(redis_url, decode_responses=True)
            
            # Test the connection immediately
            await REDIS_CLIENT.ping() 
            print(f"INFO: Successfully connected to Redis at {redis_url}")
            
        except Exception as e:
            # This will cause the FastAPI app (and tests) to fail if Redis is critical
            print(f"CRITICAL: Failed to connect to Redis: {e}")
            raise RuntimeError("Redis connection failed during application initialization.") from e
            
    return REDIS_CLIENT

async def add_to_blacklist(jti: str, exp: int):
    """Adds a token's JTI to the blacklist set with an expiration time (TTL)."""
    client = await get_redis_client()
    # Use 'ex' (expire) argument for time-based blacklisting
    await client.set(f"blacklist:{jti}", "1", ex=exp)

async def is_blacklisted(jti: str) -> bool:
    """Check if a token's JTI is blacklisted by checking for existence."""
    client = await get_redis_client()
    # The return value of exists is 1 if key exists, 0 otherwise
    # We use await client.exists(...) which returns 0 or 1, and convert to bool
    return bool(await client.exists(f"blacklist:{jti}"))