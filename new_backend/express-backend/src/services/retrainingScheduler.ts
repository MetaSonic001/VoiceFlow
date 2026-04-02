import { PrismaClient } from '@prisma/client';
import { processFlaggedCallLogs } from './retrainingService';

/**
 * Lightweight scheduler that runs the retraining pipeline daily at 2 AM.
 *
 * Uses setInterval instead of node-cron to avoid adding a dependency.
 * The interval checks every hour; the callback only fires if the current
 * hour matches the target hour and it hasn't already run today.
 */

let lastRunDate: string | null = null;
let intervalHandle: ReturnType<typeof setInterval> | null = null;

const TARGET_HOUR = 2; // 2 AM local time

export function startRetrainingScheduler(prisma: PrismaClient): void {
  // Run check every hour
  intervalHandle = setInterval(async () => {
    const now = new Date();
    const todayKey = now.toISOString().slice(0, 10); // YYYY-MM-DD

    if (now.getHours() === TARGET_HOUR && lastRunDate !== todayKey) {
      lastRunDate = todayKey;
      console.log(`[scheduler] Running nightly retraining pipeline — ${todayKey}`);
      try {
        const count = await processFlaggedCallLogs(prisma);
        console.log(`[scheduler] Retraining pipeline complete — ${count} examples created`);
      } catch (err) {
        console.error('[scheduler] Retraining pipeline failed:', err);
      }
    }
  }, 60 * 60 * 1000); // every hour

  console.log('[scheduler] Retraining scheduler started (runs daily at 2 AM)');
}

export function stopRetrainingScheduler(): void {
  if (intervalHandle) {
    clearInterval(intervalHandle);
    intervalHandle = null;
  }
}
