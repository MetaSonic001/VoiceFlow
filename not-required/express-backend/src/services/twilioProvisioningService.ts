import { PrismaClient } from '@prisma/client';
import { getTwilioClient } from './twilioClientService';

const WEBHOOK_BASE = () => process.env.TWILIO_WEBHOOK_BASE_URL || '';

/**
 * Provision a real Twilio phone number for an agent.
 *
 * 1. Searches for an available local number in the given country.
 * 2. Purchases the first result.
 * 3. Configures webhooks for voice incoming + status callbacks.
 * 4. Updates the Agent record with phoneNumber and twilioNumberSid.
 *
 * Returns the E.164 phone number string on success.
 * Throws a descriptive error on failure.
 */
export async function provisionAgentNumber(
  prisma: PrismaClient,
  agentId: string,
  tenantId: string,
  countryCode: string = 'US',
): Promise<string> {
  const base = WEBHOOK_BASE();
  if (!base) {
    throw new Error(
      'TWILIO_WEBHOOK_BASE_URL is not configured. Set it in your environment ' +
      'or wait for the server to auto-configure via ngrok.',
    );
  }

  // Get tenant's Twilio client
  const client = await getTwilioClient(prisma, tenantId);

  // Search for available local numbers
  let availableNumbers;
  try {
    availableNumbers = await client.availablePhoneNumbers(countryCode).local.list({
      limit: 5,
      voiceEnabled: true,
    });
  } catch (err: any) {
    if (err?.code === 21452 || err?.message?.includes('not available')) {
      throw new Error(
        `No phone numbers available in country "${countryCode}". ` +
        'Try a different country code (e.g. US, GB, CA).',
      );
    }
    throw new Error(`Failed to search for numbers: ${err?.message || err}`);
  }

  if (!availableNumbers || availableNumbers.length === 0) {
    throw new Error(
      `No available phone numbers found in "${countryCode}". ` +
      'Try a different country code or check your Twilio account balance.',
    );
  }

  // Purchase the first available number
  const selected = availableNumbers[0];
  let purchasedNumber;
  try {
    purchasedNumber = await client.incomingPhoneNumbers.create({
      phoneNumber: selected.phoneNumber,
      voiceUrl: `${base}/twilio/voice/incoming`,
      voiceMethod: 'POST',
      statusCallback: `${base}/twilio/voice/status`,
      statusCallbackMethod: 'POST',
      friendlyName: `VoiceFlow Agent ${agentId.slice(0, 8)}`,
    });
  } catch (err: any) {
    throw new Error(`Failed to purchase number: ${err?.message || err}`);
  }

  // Update the Agent record
  await prisma.agent.update({
    where: { id: agentId },
    data: {
      phoneNumber: purchasedNumber.phoneNumber,
      twilioNumberSid: purchasedNumber.sid,
    },
  });

  console.log(
    `[provisioning] Provisioned ${purchasedNumber.phoneNumber} (${purchasedNumber.sid}) for agent ${agentId}`,
  );

  return purchasedNumber.phoneNumber;
}

/**
 * Release a provisioned Twilio number and clear it from the Agent record.
 */
export async function deprovisionAgentNumber(
  prisma: PrismaClient,
  agentId: string,
): Promise<void> {
  const agent = await prisma.agent.findUnique({
    where: { id: agentId },
    select: { twilioNumberSid: true, tenantId: true },
  });

  if (!agent?.twilioNumberSid) {
    throw new Error('Agent has no provisioned Twilio number.');
  }

  const client = await getTwilioClient(prisma, agent.tenantId);

  try {
    await client.incomingPhoneNumbers(agent.twilioNumberSid).remove();
  } catch (err: any) {
    console.error(`[provisioning] Failed to release number: ${err?.message}`);
    // Continue to clear DB even if Twilio release fails
  }

  await prisma.agent.update({
    where: { id: agentId },
    data: { phoneNumber: null, twilioNumberSid: null },
  });

  console.log(`[provisioning] Deprovisioned number for agent ${agentId}`);
}

/**
 * Ensure an agent's Twilio number webhook URLs point to the current base URL.
 * Used during startup to fix stale ngrok URLs from a previous session.
 */
export async function syncAgentWebhookUrl(
  prisma: PrismaClient,
  agentId: string,
  tenantId: string,
  twilioNumberSid: string,
): Promise<void> {
  const base = WEBHOOK_BASE();
  if (!base || !twilioNumberSid) return;

  try {
    const client = await getTwilioClient(prisma, tenantId);
    const number = await client.incomingPhoneNumbers(twilioNumberSid).fetch();

    const expectedVoiceUrl = `${base}/twilio/voice/incoming`;
    const expectedStatusUrl = `${base}/twilio/voice/status`;

    if (number.voiceUrl !== expectedVoiceUrl || number.statusCallback !== expectedStatusUrl) {
      await client.incomingPhoneNumbers(twilioNumberSid).update({
        voiceUrl: expectedVoiceUrl,
        voiceMethod: 'POST',
        statusCallback: expectedStatusUrl,
        statusCallbackMethod: 'POST',
      });
      console.log(`[provisioning] Updated webhooks for agent ${agentId} → ${base}`);
    }
  } catch (err: any) {
    console.warn(`[provisioning] Could not sync webhooks for agent ${agentId}: ${err?.message}`);
  }
}
