import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { PrismaClient } from '@prisma/client';

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
      user?: any;
    }
  }
}

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

export class SimpleAuth {
  private prisma: PrismaClient;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
  }

  // Middleware to verify JWT and set tenant context
  authenticate = async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Allow unauthenticated access to voice agent audio endpoint for demo
      if (req.path === '/api/runner/audio' && req.method === 'POST') {
        req.tenantId = 'default-tenant';
        req.userId = 'demo-user';
        req.user = { id: 'demo-user', tenantId: 'default-tenant' };
        return next();
      }

      const token = this.extractTokenFromHeader(req);

      if (!token) {
        return res.status(401).json({
          error: 'No authentication token provided',
          code: 'AUTHENTICATION_ERROR'
        });
      }

      // Verify the JWT
      let payload: any;
      try {
        payload = jwt.verify(token, JWT_SECRET);
      } catch {
        return res.status(401).json({
          error: 'Invalid authentication token',
          code: 'AUTHENTICATION_ERROR'
        });
      }

      // Look up user in DB
      const user = await this.prisma.user.findUnique({
        where: { id: payload.userId }
      });

      if (!user) {
        return res.status(401).json({
          error: 'User not found',
          code: 'AUTHENTICATION_ERROR'
        });
      }

      // Set tenant context from user
      req.tenantId = user.tenantId;
      req.userId = user.id;
      req.user = user;

      next();
    } catch (error) {
      console.error('Authentication error:', error);
      return res.status(401).json({
        error: 'Authentication failed',
        code: 'AUTHENTICATION_ERROR'
      });
    }
  };

  // Optional middleware for tenant validation (after authentication)
  validateTenantAccess = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const tenantId = req.headers['x-tenant-id'] as string || req.tenantId;

      if (!tenantId) {
        return res.status(400).json({
          error: 'Tenant ID required',
          code: 'VALIDATION_ERROR'
        });
      }

      // Verify tenant exists and is active
      const tenant = await this.prisma.tenant.findUnique({
        where: { id: tenantId, isActive: true }
      });

      if (!tenant) {
        return res.status(403).json({
          error: 'Invalid or inactive tenant',
          code: 'AUTHORIZATION_ERROR'
        });
      }

      // Ensure user belongs to the tenant
      if (req.user && req.user.tenantId !== tenantId) {
        return res.status(403).json({
          error: 'Access denied: User does not belong to this tenant',
          code: 'AUTHORIZATION_ERROR'
        });
      }

      req.tenantId = tenantId;
      next();
    } catch (error) {
      console.error('Tenant validation error:', error);
      return res.status(500).json({
        error: 'Tenant validation failed',
        code: 'INTERNAL_ERROR'
      });
    }
  };

  private extractTokenFromHeader(req: Request): string | null {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return null;
    }
    return authHeader.substring(7);
  }

  // Helper method to get user info
  async getUserInfo(userId: string) {
    return await this.prisma.user.findUnique({
      where: { id: userId },
      include: {
        tenant: true
      }
    });
  }
}

// Factory function to create auth middleware
export const createClerkAuth = (prisma: PrismaClient) => {
  const auth = new SimpleAuth(prisma);
  return {
    authenticate: auth.authenticate,
    validateTenantAccess: auth.validateTenantAccess,
    getUserInfo: auth.getUserInfo.bind(auth)
  };
};