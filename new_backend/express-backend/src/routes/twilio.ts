import express, { Request, Response, NextFunction, Router } from 'express';

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

// Get Twilio numbers
router.get('/numbers', async (req: Request, res: Response) => {
  try {
    // Return mock Twilio numbers for now
    const mockNumbers = [
      {
        sid: 'PN1234567890abcdef',
        phone_number: '+1234567890',
        friendly_name: 'VoiceFlow Agent Line 1'
      },
      {
        sid: 'PN1234567890abcdef2',
        phone_number: '+1234567891',
        friendly_name: 'VoiceFlow Agent Line 2'
      }
    ];

    res.json({ numbers: mockNumbers });
  } catch (error) {
    console.error('Error getting Twilio numbers:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;