import express, { Request, Response, Router } from 'express';
import jwt from 'jsonwebtoken';

const router: Router = express.Router();

// Extend Request interface (ensure modifiers/types match other declarations across the project)
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
    }
  }
}

// Helper to get prisma with relaxed typing so TypeScript doesn't fail on schema differences
function getPrisma(req: Request): any {
  return req.app.get('prisma') as any;
}

// Clerk sync endpoint - called by Next.js API route
router.post('/clerk_sync', async (req: Request, res: Response) => {
  try {
    const prisma = getPrisma(req);
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    // Find or create user (use relaxed typing)
    let user: any = await prisma.user.findUnique({
      where: { email },
      // don't rely on includes that may not exist in the generated client
    });

    if (!user) {
      // Create tenant
      const tenant = await prisma.tenant.create({
        data: {
          name: `${email.split('@')[0]}'s Organization`,
        },
      });

      // Create first brand under the tenant if the model exists
      let brand: any = null;
      if (prisma.brand && typeof prisma.brand.create === 'function') {
        brand = await prisma.brand.create({
          data: {
            tenantId: tenant.id,
            name: 'Default Brand',
          },
        });
      }

      // Create user linked to tenant and optionally brand
      const userCreateData: any = {
        email,
        tenantId: tenant.id,
        ...(brand ? { brandId: brand.id } : {}),
      };

      user = await prisma.user.create({
        data: userCreateData,
      });

      // attach tenant/brand to response object where available
      user.tenant = tenant;
      user.brand = brand;
      console.log(`Created new tenant ${tenant.id}${brand ? ` and brand ${brand.id}` : ''} for user ${email}`);
    }

    // Generate JWT token (assert user exists)
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId ?? user.tenant?.id,
        email: user.email,
      },
      process.env.JWT_SECRET || 'dev-secret',
      { expiresIn: '24h' }
    );

    res.json({
      access_token: token,
      user: {
        id: user.id,
        email: user.email,
        tenantId: user.tenantId ?? user.tenant?.id ?? null,
        brandId: user.brandId ?? user.brand?.id ?? null,
        tenant: user.tenant ?? null,
        brand: user.brand ?? null,
      },
    });
  } catch (error) {
    console.error('Error in clerk_sync:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Legacy auth endpoints for backward compatibility (if needed)
router.post('/login', async (req: Request, res: Response) => {
  try {
    const prisma = getPrisma(req);
    const { email } = req.body;

    const user: any = await prisma.user.findUnique({
      where: { email },
    });

    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // For now, accept any password in development
    // In production, you'd verify the hashed password and use secure flows
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId ?? user.tenant?.id,
        email: user.email,
      },
      process.env.JWT_SECRET || 'dev-secret',
      { expiresIn: '24h' }
    );

    res.json({
      access_token: token,
      user: {
        id: user.id,
        email: user.email,
        tenantId: user.tenantId ?? user.tenant?.id ?? null,
        brandId: user.brandId ?? user.brand?.id ?? null,
        tenant: user.tenant ?? null,
        brand: user.brand ?? null,
      },
    });
  } catch (error) {
    console.error('Error in login:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/signup', async (req: Request, res: Response) => {
  try {
    const prisma = getPrisma(req);
    const { email } = req.body;

    // Check if user already exists
    const existingUser = await prisma.user.findUnique({
      where: { email },
    });

    if (existingUser) {
      return res.status(400).json({ error: 'User already exists' });
    }

    // Create tenant
    const tenant = await prisma.tenant.create({
      data: {
        name: `${email.split('@')[0]}'s Organization`,
      },
    });

    // Create first brand under the tenant if available
    let brand: any = null;
    if (prisma.brand && typeof prisma.brand.create === 'function') {
      brand = await prisma.brand.create({
        data: {
          tenantId: tenant.id,
          name: 'Default Brand',
        },
      });
    }

    // Create user
    const userCreateData: any = {
      email,
      tenantId: tenant.id,
      ...(brand ? { brandId: brand.id } : {}),
    };

    const user = await prisma.user.create({
      data: userCreateData,
    });

    // attach tenant/brand for response
    user.tenant = tenant;
    user.brand = brand;

    // Generate JWT token
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId ?? tenant.id,
        email: user.email,
      },
      process.env.JWT_SECRET || 'dev-secret',
      { expiresIn: '24h' }
    );

    res.json({
      access_token: token,
      user: {
        id: user.id,
        email: user.email,
        tenantId: user.tenantId ?? tenant.id,
        brandId: user.brandId ?? brand?.id ?? null,
        tenant: user.tenant ?? tenant,
        brand: user.brand ?? brand,
      },
    });
  } catch (error) {
    console.error('Error in signup:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/guest', async (req: Request, res: Response) => {
  try {
    const prisma = getPrisma(req);

    // Create a guest user with a unique email
    const guestEmail = `guest_${Date.now()}@voiceflow.ai`;

    // Create tenant
    const tenant = await prisma.tenant.create({
      data: {
        name: 'Guest Organization',
      },
    });

    // Create first brand under the tenant if available
    let brand: any = null;
    if (prisma.brand && typeof prisma.brand.create === 'function') {
      brand = await prisma.brand.create({
        data: {
          tenantId: tenant.id,
          name: 'Default Brand',
        },
      });
    }

    // Create user
    const userCreateData: any = {
      email: guestEmail,
      tenantId: tenant.id,
      ...(brand ? { brandId: brand.id } : {}),
    };

    const user = await prisma.user.create({
      data: userCreateData,
    });

    user.tenant = tenant;
    user.brand = brand;

    // Generate JWT token
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId ?? tenant.id,
        email: user.email,
      },
      process.env.JWT_SECRET || 'dev-secret',
      { expiresIn: '24h' }
    );

    res.json({
      access_token: token,
      user: {
        id: user.id,
        email: user.email,
        tenantId: user.tenantId ?? tenant.id,
        brandId: user.brandId ?? brand?.id ?? null,
        tenant: user.tenant ?? tenant,
        brand: user.brand ?? brand,
      },
    });
  } catch (error) {
    console.error('Error in guest login:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/logout', async (_req: Request, res: Response) => {
  // For stateless JWT, logout is handled client-side
  res.json({ success: true });
});

router.get('/me', async (req: Request, res: Response) => {
  try {
    // This endpoint expects the user to be authenticated via middleware
    const prisma = getPrisma(req);

    const userId = req.userId;
    if (!userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const user: any = await prisma.user.findUnique({
      where: { id: userId },
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Attempt to load tenant/brand only if available
    const tenant = prisma.tenant ? await prisma.tenant.findUnique({ where: { id: user.tenantId } }).catch(() => null) : null;
    const brand = prisma.brand ? await prisma.brand.findUnique({ where: { id: user.brandId } }).catch(() => null) : null;

    user.tenant = user.tenant ?? tenant;
    user.brand = user.brand ?? brand;

    res.json({ user });
  } catch (error) {
    console.error('Error in /me:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;