import { PrismaClient } from '@prisma/client';

/**
 * Retraining Pipeline Service — Task 25
 *
 * Processes flagged CallLog records into RetrainingExample rows.
 * The cron job calls `processFlaggedCallLogs()` nightly.
 * Approved examples are injected as few-shot context in prompt assembly.
 */

interface TranscriptTurn {
  role?: string;
  speaker?: string;
  content?: string;
  message?: string;
}

/**
 * Parse a transcript string or JSON into turn pairs.
 * Handles both `{role, content}` and `{speaker, message}` formats,
 * as well as plain-text "Caller: ... \nAgent: ..." format.
 */
function parseTranscript(raw: string): TranscriptTurn[] {
  // Try JSON format first
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map((t: any) => ({
        role: t.role || t.speaker || 'unknown',
        content: t.content || t.message || '',
      }));
    }
  } catch {
    // Not JSON — parse as plain text
  }

  // Plain text: "Caller: ...\nAgent: ..."
  const lines = raw.split('\n').filter((l) => l.trim());
  const turns: TranscriptTurn[] = [];
  for (const line of lines) {
    const match = line.match(/^(Caller|Agent|User|Assistant|Q|A):\s*(.*)/i);
    if (match) {
      const speaker = match[1].toLowerCase();
      const role =
        speaker === 'caller' || speaker === 'user' || speaker === 'q'
          ? 'user'
          : 'assistant';
      turns.push({ role, content: match[2].trim() });
    }
  }
  return turns;
}

/**
 * Extract user-query / bad-response pairs from a flagged conversation.
 * Strategy:
 *   - Walk turns pair-wise: (user, assistant)
 *   - The last complete pair is most likely the problematic exchange
 *   - Use ratingNotes as hint for what the ideal response should be
 */
function extractExamplePairs(
  transcript: string,
  ratingNotes: string | null,
): { userQuery: string; badResponse: string; idealHint: string }[] {
  const turns = parseTranscript(transcript);
  const pairs: { userQuery: string; badResponse: string; idealHint: string }[] = [];

  for (let i = 0; i < turns.length - 1; i++) {
    const current = turns[i];
    const next = turns[i + 1];
    if (current.role === 'user' && next.role === 'assistant') {
      pairs.push({
        userQuery: current.content || '',
        badResponse: next.content || '',
        idealHint: ratingNotes || 'Please provide the correct response.',
      });
    }
  }

  // If we have multiple pairs, only take the last one (most likely the bad one)
  // unless there's only one pair
  if (pairs.length > 1) {
    return [pairs[pairs.length - 1]];
  }
  return pairs;
}

/**
 * Nightly job: find all flagged-but-not-retrained CallLogs,
 * extract example pairs, and write RetrainingExample rows.
 */
export async function processFlaggedCallLogs(prisma: PrismaClient): Promise<number> {
  const flagged = await prisma.callLog.findMany({
    where: {
      flaggedForRetraining: true,
      retrained: false,
    },
    take: 200, // batch size
    orderBy: { createdAt: 'asc' },
  });

  if (flagged.length === 0) return 0;

  let created = 0;

  for (const log of flagged) {
    const pairs = extractExamplePairs(log.transcript, log.ratingNotes);

    for (const pair of pairs) {
      if (!pair.userQuery || !pair.badResponse) continue;

      await prisma.retrainingExample.create({
        data: {
          tenantId: log.tenantId,
          agentId: log.agentId,
          callLogId: log.id,
          userQuery: pair.userQuery,
          badResponse: pair.badResponse,
          idealResponse: pair.idealHint,
          status: 'pending',
        },
      });
      created++;
    }

    // Mark log as processed so it's not picked up again
    await prisma.callLog.update({
      where: { id: log.id },
      data: { retrained: true },
    });
  }

  console.log(`[retraining] Processed ${flagged.length} flagged logs → ${created} examples`);
  return created;
}

/**
 * Get approved few-shot examples for a given agent.
 * These are injected into the system prompt as in-context learning.
 */
export async function getApprovedExamples(
  prisma: PrismaClient,
  agentId: string,
  limit: number = 10,
): Promise<{ userQuery: string; idealResponse: string }[]> {
  const examples = await prisma.retrainingExample.findMany({
    where: {
      agentId,
      status: 'approved',
    },
    orderBy: { approvedAt: 'desc' },
    take: limit,
    select: {
      userQuery: true,
      idealResponse: true,
    },
  });

  return examples;
}
