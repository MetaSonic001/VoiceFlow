import express, { Request, Response, Router } from 'express';
import { PrismaClient } from '@prisma/client';

const router: Router = express.Router();

// Get real provisioned Twilio numbers for the authenticated tenant
router.get('/numbers', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');

    // Return agents that have a provisioned phone number for this tenant
    const agents = await prisma.agent.findMany({
      where: {
        tenantId: req.tenantId,
        phoneNumber: { not: null },
      },
      select: {
        id: true,
        name: true,
        phoneNumber: true,
        twilioNumberSid: true,
        status: true,
      },
    });

    const numbers = agents.map((a) => ({
      sid: a.twilioNumberSid || '',
      phone_number: a.phoneNumber,
      friendly_name: a.name || 'Agent',
      agent_id: a.id,
      status: a.status,
    }));

    res.json({ numbers });
  } catch (error) {
    console.error('Error getting Twilio numbers:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;