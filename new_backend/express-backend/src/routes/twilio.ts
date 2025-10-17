import express, { Request, Response, NextFunction, Router } from 'express';
import RagService from '../services/ragService';
import VoiceService from '../services/voiceService';
import { TwilioMediaService, TwilioMediaConfig } from '../services/twilioMediaService';

const router: Router = express.Router();

// Initialize services (these should be injected properly in production)
const ragService = RagService;
const voiceService = VoiceService;

const twilioConfig: TwilioMediaConfig = {
  accountSid: process.env.TWILIO_ACCOUNT_SID!,
  authToken: process.env.TWILIO_AUTH_TOKEN!,
  phoneNumber: process.env.TWILIO_PHONE_NUMBER!,
  voskModelPath: process.env.VOSK_MODEL_PATH || './models/vosk-model',
};

const twilioMediaService = new TwilioMediaService(twilioConfig, ragService, voiceService);

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

// Voice webhook endpoint - handles incoming calls
router.post('/voice', async (req: Request, res: Response) => {
  try {
    console.log('Incoming voice call:', req.body);

    // Generate TwiML response for voice handling
    const twiml = twilioMediaService.generateVoiceResponse();

    res.type('text/xml');
    res.send(twiml);
  } catch (error) {
    console.error('Error handling voice webhook:', error);
    res.status(500).send('Internal server error');
  }
});

// Make outbound call endpoint
router.post('/call', async (req: Request, res: Response) => {
  try {
    const { to, agentId } = req.body;

    if (!to) {
      return res.status(400).json({ error: 'Phone number is required' });
    }

    const callSid = await twilioMediaService.makeOutboundCall(to);

    res.json({
      success: true,
      callSid,
      message: 'Call initiated successfully'
    });
  } catch (error) {
    console.error('Error making outbound call:', error);
    res.status(500).json({ error: 'Failed to initiate call' });
  }
});

// Get call status
router.get('/call/:callSid', async (req: Request, res: Response) => {
  try {
    const { callSid } = req.params;
    const callStatus = await twilioMediaService.getCallStatus(callSid);

    res.json(callStatus);
  } catch (error) {
    console.error('Error getting call status:', error);
    res.status(500).json({ error: 'Failed to get call status' });
  }
});

export default router;