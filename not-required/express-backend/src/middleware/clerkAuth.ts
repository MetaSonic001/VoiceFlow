import { Request, Response, NextFunction } from "express";
import { PrismaClient } from "@prisma/client";

const DEMO_TENANT = "demo-tenant";
const DEMO_USER = "demo-user";

// Extend Express Request
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
      user?: any;
    }
  }
}

/**
 * No-auth passthrough middleware for the demo branch.
 * Reads x-tenant-id / x-user-id from headers (set by the Next.js proxy),
 * falls back to hardcoded demo values, and attaches them to the request.
 */
export class ClerkAuth {
  private prisma: PrismaClient;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
  }

  authenticate = async (req: Request, _res: Response, next: NextFunction) => {
    const tenantId = (req.headers["x-tenant-id"] as string) || DEMO_TENANT;
    const userId = (req.headers["x-user-id"] as string) || DEMO_USER;

    req.tenantId = tenantId;
    req.userId = userId;
    req.user = { id: userId, tenantId };

    next();
  };

  validateTenantAccess = async (
    req: Request,
    _res: Response,
    next: NextFunction,
  ) => {
    // Always allow — demo mode
    req.tenantId = (req.headers["x-tenant-id"] as string) || req.tenantId || DEMO_TENANT;
    next();
  };

  async getUserInfo(userId: string) {
    return this.prisma.user.findUnique({
      where: { id: userId },
      include: { tenant: true },
    });
  }
}

// Factory — same export shape so nothing else needs to change
export const createClerkAuth = (prisma: PrismaClient) => {
  const clerkAuth = new ClerkAuth(prisma);
  return {
    authenticate: clerkAuth.authenticate,
    validateTenantAccess: clerkAuth.validateTenantAccess,
    getUserInfo: clerkAuth.getUserInfo.bind(clerkAuth),
  };
};
