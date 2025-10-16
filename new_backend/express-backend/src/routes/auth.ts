import express, { Request, Response, NextFunction, Router } from 'express';
import { PrismaClient } from '@prisma/client';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';

const router: Router = express.Router();

// Extend Request interface
declare global {
  namespace Express {
    interface Request {
      tenantId: string;
      userId: string;
    }
  }
}

// Clerk sync endpoint - called by Next.js API route
router.post('/clerk_sync', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    // Find or create user
    let user = await prisma.user.findUnique({
      where: { email },
      include: {
        tenant: true,
        brand: true,
      },
    });

    if (!user) {
      // Create tenant
      const tenant = await prisma.tenant.create({
        data: {
          name: `${email.split('@')[0]}'s Organization`,
        },
      });

      // Create first brand under the tenant
      const brand = await prisma.brand.create({
        data: {
          tenantId: tenant.id,
          name: 'Default Brand',
        },
      });

      // Create user linked to tenant and brand
      user = await prisma.user.create({
        data: {
          email,
          tenantId: tenant.id,
          brandId: brand.id,
        },
        include: {
          tenant: true,
          brand: true,
        },
      });

      console.log(`Created new tenant ${tenant.id} and brand ${brand.id} for user ${email}`);
    }

    // Generate JWT token
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId,
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
        tenantId: user.tenantId,
        brandId: user.brandId,
        tenant: user.tenant,
        brand: user.brand,
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
    const prisma: PrismaClient = req.app.get('prisma');
    const { email, password } = req.body;

    const user = await prisma.user.findUnique({
      where: { email },
      include: {
        tenant: true,
        brand: true,
      },
    });

    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // For now, accept any password in development
    // In production, you'd verify the hashed password
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId,
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
        tenantId: user.tenantId,
        brandId: user.brandId,
        tenant: user.tenant,
        brand: user.brand,
      },
    });
  } catch (error) {
    console.error('Error in login:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/signup', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { email, password } = req.body;

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

    // Create first brand under the tenant
    const brand = await prisma.brand.create({
      data: {
        tenantId: tenant.id,
        name: 'Default Brand',
      },
    });

    // Create user
    const user = await prisma.user.create({
      data: {
        email,
        tenantId: tenant.id,
        brandId: brand.id,
      },
      include: {
        tenant: true,
        brand: true,
      },
    });

    // Generate JWT token
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId,
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
        tenantId: user.tenantId,
        brandId: user.brandId,
        tenant: user.tenant,
        brand: user.brand,
      },
    });
  } catch (error) {
    console.error('Error in signup:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/guest', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    // Create a guest user with a unique email
    const guestEmail = `guest_${Date.now()}@voiceflow.ai`;

    // Create tenant
    const tenant = await prisma.tenant.create({
      data: {
        name: 'Guest Organization',
      },
    });

    // Create first brand under the tenant
    const brand = await prisma.brand.create({
      data: {
        tenantId: tenant.id,
        name: 'Default Brand',
      },
    });

    // Create user
    const user = await prisma.user.create({
      data: {
        email: guestEmail,
        tenantId: tenant.id,
        brandId: brand.id,
      },
      include: {
        tenant: true,
        brand: true,
      },
    });

    // Generate JWT token
    const token = jwt.sign(
      {
        userId: user.id,
        tenantId: user.tenantId,
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
        tenantId: user.tenantId,
        brandId: user.brandId,
        tenant: user.tenant,
        brand: user.brand,
      },
    });
  } catch (error) {
    console.error('Error in guest login:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/logout', async (req: Request, res: Response) => {
  // For stateless JWT, logout is handled client-side
  res.json({ success: true });
});

router.get('/me', async (req: Request, res: Response) => {
  try {
    // This endpoint expects the user to be authenticated via middleware
    const prisma: PrismaClient = req.app.get('prisma');

    const user = await prisma.user.findUnique({
      where: { id: req.userId },
      include: {
        tenant: true,
        brand: true,
      },
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({ user });
  } catch (error) {
    console.error('Error in /me:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;</content>
<parameter name="filePath">c:\VoiceFlow\new_backend\express-backend\src\routes\auth.ts