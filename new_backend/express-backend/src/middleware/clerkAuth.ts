import { Request, Response, NextFunction } from "express";
import { createClerkClient } from "@clerk/express";
import { PrismaClient } from "@prisma/client";

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

export class ClerkAuth {
  private prisma: PrismaClient;
  private clerkClient;

  constructor(prisma: PrismaClient) {
    this.prisma = prisma;
    this.clerkClient = createClerkClient({
      secretKey: process.env.CLERK_SECRET_KEY!,
      publishableKey: process.env.CLERK_PUBLISHABLE_KEY!, // ✅ REQUIRED
    });
  }

  authenticate = async (req: Request, res: Response, next: NextFunction) => {
    try {
      // 🔥 Dev bypass (safe)
      if (
        process.env.NODE_ENV !== "production" &&
        req.path === "/api/runner/audio" &&
        req.method === "POST"
      ) {
        req.tenantId = "default-tenant";
        req.userId = "demo-user";
        req.user = { id: "demo-user", tenantId: "default-tenant" };
        return next();
      }

      const webRequest = new Request(
        `${req.protocol}://${req.get("host")}${req.originalUrl}`,
        {
          method: req.method,
          headers: req.headers as any,
          body:
            req.method !== "GET" && req.method !== "HEAD"
              ? JSON.stringify(req.body)
              : undefined,
        },
      );

      const { isAuthenticated, toAuth } =
        await this.clerkClient.authenticateRequest(webRequest, {
          authorizedParties: [
            process.env.FRONTEND_URL || "http://localhost:3000",
          ],
          jwtKey: process.env.CLERK_JWT_KEY,
        });

      if (!isAuthenticated) {
        return res.status(401).json({
          error: "Unauthenticated",
          code: "AUTHENTICATION_ERROR",
        });
      }

      const auth = toAuth();

      // 🔥 Handle only user tokens (ignore M2M/API tokens)
      if (!("userId" in auth) || !auth.userId) {
        return res.status(401).json({
          error: "Invalid token type (no user)",
          code: "AUTHENTICATION_ERROR",
        });
      }

      const clerkUserId = auth.userId;

      // ✅ Fast lookup
      let user = await this.prisma.user.findUnique({
        where: { id: clerkUserId },
      });

      // ✅ Lazy create
      if (!user) {
        let tenant = await this.prisma.tenant.findFirst({
          where: { isActive: true },
          orderBy: { createdAt: "asc" },
        });

        if (!tenant) {
          tenant = await this.prisma.tenant.create({
            data: {
              id: "default-tenant",
              name: "Default Organization",
              domain: "default.com",
              apiKey: "sk-default-" + Date.now(),
              isActive: true,
            },
          });
        }

        user = await this.prisma.user.create({
          data: {
            id: clerkUserId,
            email: "",
            name: "User",
            tenantId: tenant.id,
          },
        });
      }

      // ✅ Attach to request
      req.userId = user.id;
      req.tenantId = user.tenantId;
      req.user = user;

      next();
    } catch (error) {
      console.error("Clerk authentication error:", error);
      return res.status(401).json({
        error: "Authentication failed",
        code: "AUTHENTICATION_ERROR",
      });
    }
  };

  validateTenantAccess = async (
    req: Request,
    res: Response,
    next: NextFunction,
  ) => {
    try {
      const tenantId = (req.headers["x-tenant-id"] as string) || req.tenantId;

      if (!tenantId) {
        return res.status(400).json({
          error: "Tenant ID required",
          code: "VALIDATION_ERROR",
        });
      }

      const tenant = await this.prisma.tenant.findUnique({
        where: { id: tenantId, isActive: true },
      });

      if (!tenant) {
        return res.status(403).json({
          error: "Invalid or inactive tenant",
          code: "AUTHORIZATION_ERROR",
        });
      }

      if (req.user && req.user.tenantId !== tenantId) {
        return res.status(403).json({
          error: "Access denied: tenant mismatch",
          code: "AUTHORIZATION_ERROR",
        });
      }

      req.tenantId = tenantId;
      next();
    } catch (error) {
      console.error("Tenant validation error:", error);
      return res.status(500).json({
        error: "Tenant validation failed",
        code: "INTERNAL_ERROR",
      });
    }
  };

  async getUserInfo(userId: string) {
    return this.prisma.user.findUnique({
      where: { id: userId },
      include: { tenant: true },
    });
  }
}

// Factory
export const createClerkAuth = (prisma: PrismaClient) => {
  const clerkAuth = new ClerkAuth(prisma);
  return {
    authenticate: clerkAuth.authenticate,
    validateTenantAccess: clerkAuth.validateTenantAccess,
    getUserInfo: clerkAuth.getUserInfo.bind(clerkAuth),
  };
};
