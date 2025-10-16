import { Request, Response, NextFunction } from 'express';
import { Prisma } from '@prisma/client';

// Custom error types
export class AppError extends Error {
  public statusCode: number;
  public isOperational: boolean;
  public code?: string;

  constructor(message: string, statusCode: number = 500, code?: string) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    this.code = code;

    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 400, 'VALIDATION_ERROR');
  }
}

export class AuthenticationError extends AppError {
  constructor(message: string = 'Authentication required') {
    super(message, 401, 'AUTHENTICATION_ERROR');
  }
}

export class AuthorizationError extends AppError {
  constructor(message: string = 'Access denied') {
    super(message, 403, 'AUTHORIZATION_ERROR');
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string = 'Resource') {
    super(`${resource} not found`, 404, 'NOT_FOUND_ERROR');
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 409, 'CONFLICT_ERROR');
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'Too many requests') {
    super(message, 429, 'RATE_LIMIT_ERROR');
  }
}

// Error logging utility
export class ErrorLogger {
  static log(error: Error, req?: Request, context?: any) {
    const timestamp = new Date().toISOString();
    const errorInfo = {
      timestamp,
      message: error.message,
      stack: error.stack,
      name: error.name,
      ...(req && {
        method: req.method,
        url: req.url,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        tenantId: (req as any).tenantId,
        body: this.sanitizeBody(req.body),
        query: req.query,
        params: req.params
      }),
      ...context
    };

    // Log to console with different levels
    if (error instanceof AppError && error.isOperational) {
      console.warn('Operational Error:', JSON.stringify(errorInfo, null, 2));
    } else {
      console.error('Unexpected Error:', JSON.stringify(errorInfo, null, 2));
    }

    // TODO: Send to external logging service (e.g., Winston, DataDog, etc.)
  }

  private static sanitizeBody(body: any): any {
    if (!body) return body;

    const sensitiveFields = ['password', 'token', 'secret', 'key', 'ssn', 'creditCard'];
    const sanitized = { ...body };

    sensitiveFields.forEach(field => {
      if (sanitized[field]) {
        sanitized[field] = '[REDACTED]';
      }
    });

    return sanitized;
  }
}

// Error response formatter
export class ErrorResponse {
  static format(error: Error, includeStack: boolean = false): any {
    const baseResponse: any = {
      success: false,
      error: {
        message: error.message,
        code: (error as AppError).code || 'INTERNAL_ERROR',
        timestamp: new Date().toISOString()
      }
    };

    // Include stack trace in development
    if (includeStack && process.env.NODE_ENV === 'development') {
      baseResponse.error.stack = error.stack;
    }

    return baseResponse;
  }

  static validation(errors: any[]): any {
    return {
      success: false,
      error: {
        message: 'Validation failed',
        code: 'VALIDATION_ERROR',
        details: errors,
        timestamp: new Date().toISOString()
      }
    };
  }
}

// Global error handler middleware
export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  let statusCode = 500;
  let message = 'Internal server error';

  // Handle known error types
  if (error instanceof AppError) {
    statusCode = error.statusCode;
    message = error.message;
  } else if (error instanceof Prisma.PrismaClientKnownRequestError) {
    // Handle Prisma known errors
    switch (error.code) {
      case 'P2002':
        statusCode = 409;
        message = 'A record with this information already exists';
        break;
      case 'P2025':
        statusCode = 404;
        message = 'Record not found';
        break;
      default:
        statusCode = 400;
        message = 'Database operation failed';
    }
  } else if (error instanceof Prisma.PrismaClientValidationError) {
    statusCode = 400;
    message = 'Invalid data provided';
  } else if (error.name === 'ValidationError') {
    statusCode = 400;
    message = 'Validation failed';
  }

  // Log the error
  ErrorLogger.log(error, req, { statusCode });

  // Send error response
  const includeStack = process.env.NODE_ENV === 'development';
  res.status(statusCode).json(ErrorResponse.format(error, includeStack));
};

// Async error wrapper
export const asyncHandler = (fn: Function) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

// Request logging middleware
export const requestLogger = (req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    const logData = {
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration: `${duration}ms`,
      ip: req.ip,
      tenantId: (req as any).tenantId,
      userAgent: req.get('User-Agent')
    };

    if (res.statusCode >= 400) {
      console.warn('Request Error:', JSON.stringify(logData));
    } else {
      console.log('Request:', JSON.stringify(logData));
    }
  });

  next();
};

// Health check error handler
export const healthCheckErrorHandler = (error: Error, req: Request, res: Response, next: NextFunction) => {
  if (req.url === '/health') {
    // For health checks, return a simple response
    res.status(503).json({
      status: 'error',
      message: 'Service unhealthy',
      timestamp: new Date().toISOString()
    });
  } else {
    next(error);
  }
};