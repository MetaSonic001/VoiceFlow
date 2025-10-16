import rateLimit from 'express-rate-limit';
import { Request, Response, NextFunction } from 'express';
import Redis from 'ioredis';

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
    }
  }
}

// In-memory store for rate limiting (fallback)
class MemoryStore {
  private store: Map<string, { count: number; resetTime: number }> = new Map();

  increment(key: string): { count: number; resetTime: number } {
    const now = Date.now();
    const windowMs = 15 * 60 * 1000; // 15 minutes
    const existing = this.store.get(key);

    if (!existing || now > existing.resetTime) {
      this.store.set(key, { count: 1, resetTime: now + windowMs });
      return { count: 1, resetTime: now + windowMs };
    }

    existing.count++;
    return existing;
  }

  resetKey(key: string): void {
    this.store.delete(key);
  }
}

// Redis-based rate limiter for tenant-specific limits
export class TenantRateLimiter {
  private redis: Redis | null = null;
  private memoryStore = new MemoryStore();

  constructor(redis?: Redis) {
    this.redis = redis || null;
  }

  createTenantLimiter(options: {
    windowMs?: number;
    maxRequests?: number;
    tenantLimits?: { [tenantId: string]: number };
    skipSuccessfulRequests?: boolean;
    skipFailedRequests?: boolean;
  } = {}) {
    const {
      windowMs = 15 * 60 * 1000, // 15 minutes
      maxRequests = 100,
      tenantLimits = {},
      skipSuccessfulRequests = false,
      skipFailedRequests = false
    } = options;

    return async (req: Request, res: Response, next: NextFunction) => {
      const tenantId = req.tenantId || req.headers['x-tenant-id'] as string || 'default';

      // Get tenant-specific limit, fallback to default
      const limit = tenantLimits[tenantId] || maxRequests;

      const key = `ratelimit:${tenantId}:${req.ip}`;

      try {
        let currentCount: number;
        let resetTime: number;

        if (this.redis) {
          // Use Redis for distributed rate limiting
          const now = Date.now();
          const windowStart = Math.floor(now / windowMs) * windowMs;

          const redisKey = `${key}:${windowStart}`;
          currentCount = await this.redis.incr(redisKey);

          if (currentCount === 1) {
            await this.redis.pexpire(redisKey, windowMs);
          }

          resetTime = windowStart + windowMs;
        } else {
          // Fallback to memory store
          const result = this.memoryStore.increment(key);
          currentCount = result.count;
          resetTime = result.resetTime;
        }

        // Set rate limit headers
        res.set({
          'X-RateLimit-Limit': limit.toString(),
          'X-RateLimit-Remaining': Math.max(0, limit - currentCount).toString(),
          'X-RateLimit-Reset': resetTime.toString(),
          'X-RateLimit-Tenant': tenantId
        });

        if (currentCount > limit) {
          res.status(429).json({
            error: 'Too many requests',
            message: `Rate limit exceeded for tenant ${tenantId}. Try again later.`,
            retryAfter: Math.ceil((resetTime - Date.now()) / 1000)
          });
          return;
        }

        // Add rate limit info to request for logging
        (req as any).rateLimit = {
          tenantId,
          current: currentCount,
          limit,
          remaining: Math.max(0, limit - currentCount),
          resetTime
        };

        next();
      } catch (error) {
        console.error('Rate limiting error:', error);
        // On error, allow the request to proceed
        next();
      }
    };
  }
}

// Create default tenant rate limiter
export const createTenantRateLimit = (redis?: Redis) => {
  const limiter = new TenantRateLimiter(redis);

  // Default tenant-specific limits
  const tenantLimits: { [key: string]: number } = {
    // Premium tenants get higher limits
    'premium-tenant-1': 1000,
    'premium-tenant-2': 1000,
    // Standard tenants
    'default': 100
  };

  return limiter.createTenantLimiter({
    windowMs: 15 * 60 * 1000, // 15 minutes
    maxRequests: 100,
    tenantLimits,
    skipSuccessfulRequests: false,
    skipFailedRequests: false
  });
};

// Specialized rate limiters for different endpoints
export const createStrictTenantRateLimit = (redis?: Redis) => {
  const limiter = new TenantRateLimiter(redis);
  return limiter.createTenantLimiter({
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 10, // Very strict for sensitive operations
    tenantLimits: {
      'premium-tenant-1': 50,
      'premium-tenant-2': 50,
      'default': 10
    }
  });
};

export const createGenerousTenantRateLimit = (redis?: Redis) => {
  const limiter = new TenantRateLimiter(redis);
  return limiter.createTenantLimiter({
    windowMs: 60 * 1000, // 1 minute
    maxRequests: 60, // More generous for read operations
    tenantLimits: {
      'premium-tenant-1': 300,
      'premium-tenant-2': 300,
      'default': 60
    }
  });
};