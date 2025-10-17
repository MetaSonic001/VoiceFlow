import { Request, Response, NextFunction } from 'express';
import { verifyToken } from '@clerk/clerk-sdk-node';
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

export interface ClerkUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  imageUrl?: string;
  publicMetadata?: any;
  privateMetadata?: any;
}

export class ClerkAuth {
  private prisma: PrismaClient;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
  }

  // Middleware to verify Clerk JWT and set tenant context
  authenticate = async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Allow unauthenticated access to voice agent audio endpoint for demo
      if (req.path === '/api/runner/audio' && req.method === 'POST') {
        // Set default tenant and user for demo
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

      // Verify the JWT with Clerk
      const tokenPayload = await verifyToken(token, {
        secretKey: process.env.CLERK_SECRET_KEY!
      });

      if (!tokenPayload) {
        return res.status(401).json({
          error: 'Invalid authentication token',
          code: 'AUTHENTICATION_ERROR'
        });
      }

      // Extract user info from Clerk JWT
      const payload = tokenPayload as any; // Clerk JWT payload
      const clerkUser: ClerkUser = {
        id: payload.sub,
        email: (payload.email_addresses?.[0]?.email_address as string) || '',
        firstName: payload.first_name as string,
        lastName: payload.last_name as string,
        imageUrl: payload.image_url as string,
        publicMetadata: payload.public_metadata,
        privateMetadata: payload.private_metadata
      };

      // Get or create user in our database
      const user = await this.syncUserWithDatabase(clerkUser);

      // Set tenant context from user's tenant
      req.tenantId = user.tenantId;
      req.userId = user.id;
      req.user = user;

      next();
    } catch (error) {
      console.error('Clerk authentication error:', error);
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

  private async syncUserWithDatabase(clerkUser: ClerkUser) {
    // Try to find existing user
    let user = await this.prisma.user.findUnique({
      where: { id: clerkUser.id }
    });

    if (!user) {
      // Get default tenant or create one for new users
      let tenant = await this.prisma.tenant.findFirst({
        where: { isActive: true },
        orderBy: { createdAt: 'asc' }
      });

      if (!tenant) {
        // Create default tenant if none exists
        tenant = await this.prisma.tenant.create({
          data: {
            id: 'default-tenant',
            name: 'Default Organization',
            domain: 'default.com',
            apiKey: 'sk-default-' + Date.now(),
            isActive: true
          }
        });
      }

      // Create new user
      user = await this.prisma.user.create({
        data: {
          id: clerkUser.id,
          email: clerkUser.email,
          name: `${clerkUser.firstName || ''} ${clerkUser.lastName || ''}`.trim() || 'User',
          tenantId: tenant.id
        }
      });
    }

    return user;
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

// Factory function to create Clerk auth middleware
export const createClerkAuth = (prisma: PrismaClient) => {
  const clerkAuth = new ClerkAuth(prisma);
  return {
    authenticate: clerkAuth.authenticate,
    validateTenantAccess: clerkAuth.validateTenantAccess,
    getUserInfo: clerkAuth.getUserInfo.bind(clerkAuth)
  };
};