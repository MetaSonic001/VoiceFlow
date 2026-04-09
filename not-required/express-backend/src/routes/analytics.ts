import express, { Request, Response, NextFunction, Router } from 'express';
import { PrismaClient } from '@prisma/client';

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

// Get analytics overview metrics
router.get('/overview', async (req: Request, res: Response) => {
  try {
    const { timeRange = '7d', agentId } = req.query;
    const prisma: PrismaClient = req.app.get('prisma');

    // Determine date window
    const now = new Date();
    const days = timeRange === '24h' ? 1 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 7;
    const since = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);

    const baseWhere: any = { tenantId: req.tenantId, startedAt: { gte: since } };
    if (agentId && typeof agentId === 'string' && agentId !== 'all') {
      baseWhere.agentId = agentId;
    }

    const [totalLogs, ratedLogs, durationAgg] = await Promise.all([
      prisma.callLog.count({ where: baseWhere }),
      prisma.callLog.count({ where: { ...baseWhere, rating: { not: null } } }),
      prisma.callLog.aggregate({
        where: { ...baseWhere, durationSeconds: { not: null } },
        _avg: { durationSeconds: true },
        _sum: { durationSeconds: true },
      }),
    ]);

    const thumbsUp = await prisma.callLog.count({ where: { ...baseWhere, rating: 1 } });
    const successRate = ratedLogs > 0 ? Math.round((thumbsUp / ratedLogs) * 1000) / 10 : null;
    const avgDurationSec = durationAgg._avg.durationSeconds ?? 0;

    // Calls per day for sparkline (last `days` days)
    const allLogs = await prisma.callLog.findMany({
      where: baseWhere,
      select: { startedAt: true },
    });

    const dayCounts: Record<string, number> = {};
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      dayCounts[d.toISOString().split('T')[0]] = 0;
    }
    for (const log of allLogs) {
      const key = log.startedAt.toISOString().split('T')[0];
      if (key in dayCounts) dayCounts[key]++;
    }
    const callsPerDay = Object.entries(dayCounts).map(([date, count]) => ({ date, count }));

    // Channel performance: phone vs chat
    const phoneLogs = allLogs.filter((l: any) => l.callerPhone);
    const chatLogs  = allLogs.filter((l: any) => !l.callerPhone);

    // Get durations for channel-level stats
    const phoneDurationLogs = await prisma.callLog.findMany({
      where: { ...baseWhere, callerPhone: { not: null }, durationSeconds: { not: null } },
      select: { durationSeconds: true },
    });
    const chatDurationLogs = await prisma.callLog.findMany({
      where: { ...baseWhere, callerPhone: null, durationSeconds: { not: null } },
      select: { durationSeconds: true },
    });

    const avgPhoneDur = phoneDurationLogs.length
      ? Math.round(phoneDurationLogs.reduce((s, l) => s + l.durationSeconds!, 0) / phoneDurationLogs.length)
      : 0;
    const avgChatDur = chatDurationLogs.length
      ? Math.round(chatDurationLogs.reduce((s, l) => s + l.durationSeconds!, 0) / chatDurationLogs.length)
      : 0;

    const fmtDur = (sec: number) => `${Math.floor(sec / 60)}m ${sec % 60}s`;

    res.json({
      totalInteractions: totalLogs,
      successRate,
      avgResponseTimeSec: Math.round(avgDurationSec * 10) / 10,
      callsPerDay,
      timeRange,
      channelPerformance: {
        phone: { count: phoneLogs.length, avgDuration: fmtDur(avgPhoneDur), successRate: successRate ?? 0 },
        chat:  { count: chatLogs.length,  avgDuration: fmtDur(avgChatDur),  successRate: successRate ?? 0 },
      },
    });
  } catch (error) {
    console.error('Error fetching analytics overview:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get call logs (real data from CallLog table — prefer /api/logs for full features)
router.get('/calls', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { page = 1, limit = 50, search, agentId } = req.query;

    const pageNum  = Math.max(1, parseInt(page.toString()));
    const limitNum = Math.min(200, Math.max(1, parseInt(limit.toString())));
    const skip     = (pageNum - 1) * limitNum;

    const where: any = { tenantId: req.tenantId };
    if (agentId && agentId !== 'all') {
      where.agentId = agentId as string;
    }
    if (search) {
      where.OR = [
        { transcript: { contains: search as string, mode: 'insensitive' } },
        { callerPhone: { contains: search as string } },
      ];
    }

    const [logs, total] = await Promise.all([
      prisma.callLog.findMany({
        where,
        skip,
        take: limitNum,
        orderBy: { startedAt: 'desc' },
        include: { agent: { select: { id: true, name: true } } },
      }),
      prisma.callLog.count({ where }),
    ]);

    // Map to the shape the frontend expects
    const mappedLogs = logs.map((l: any) => ({
      id: l.id,
      type: l.callerPhone ? 'phone' : 'chat',
      customerInfo: l.callerPhone || 'Web Chat',
      agentName: l.agent?.name ?? 'Unknown',
      agentId: l.agentId,
      startTime: l.startedAt.toISOString(),
      duration: l.durationSeconds ?? 0,
      status: l.endedAt ? 'completed' : 'in-progress',
      resolution: l.rating === 1 ? 'resolved' : l.rating === -1 ? 'escalated' : 'resolved',
      summary: l.analysis && typeof l.analysis === 'object' ? (l.analysis as any).summary || '' : '',
      sentiment: l.rating === 1 ? 'positive' : l.rating === -1 ? 'negative' : 'neutral',
      tags: [],
      transcript: l.transcript,
    }));

    res.json({
      logs: mappedLogs,
      total,
      page: pageNum,
      limit: limitNum,
      totalPages: Math.ceil(total / limitNum),
    });
  } catch (error) {
    console.error('Error fetching call logs:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get realtime metrics — derived from CallLog data in the last hour
router.get('/realtime', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenantId = req.tenantId;

    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    const today = new Date(); today.setHours(0, 0, 0, 0);

    const [recentCalls, recentChats, todayCalls, agents] = await Promise.all([
      // Phone calls in last hour (callerPhone is not null)
      prisma.callLog.count({ where: { tenantId, startedAt: { gte: oneHourAgo }, callerPhone: { not: null } } }),
      // Chat interactions in last hour (callerPhone is null)
      prisma.callLog.count({ where: { tenantId, startedAt: { gte: oneHourAgo }, callerPhone: null } }),
      // All interactions today
      prisma.callLog.count({ where: { tenantId, startedAt: { gte: today } } }),
      // Number of configured agents
      prisma.agent.count({ where: { tenantId } }),
    ]);

    res.json({
      active_calls: recentCalls,
      active_chats: recentChats,
      queued_interactions: 0,
      online_agents: agents,
      today_total: todayCalls,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Error fetching realtime metrics:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get metrics chart data — daily interaction counts from CallLog
router.get('/metrics-chart', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { timeRange = '7d', agentId } = req.query;
    const tenantId = req.tenantId;

    const now = new Date();
    const days = timeRange === '24h' ? 1 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const since = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);

    const where: any = { tenantId, startedAt: { gte: since } };
    if (agentId && agentId !== 'all') where.agentId = agentId as string;

    const logs = await prisma.callLog.findMany({
      where,
      select: { startedAt: true, callerPhone: true },
    });

    // Build date → {calls, chats} map
    const dayCounts: Record<string, { calls: number; chats: number }> = {};
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now); d.setDate(d.getDate() - i);
      dayCounts[d.toISOString().split('T')[0]] = { calls: 0, chats: 0 };
    }
    for (const log of logs) {
      const key = log.startedAt.toISOString().split('T')[0];
      if (key in dayCounts) {
        if (log.callerPhone) dayCounts[key].calls++;
        else dayCounts[key].chats++;
      }
    }

    const chartData = Object.entries(dayCounts).map(([date, v]) => ({
      date,
      calls: v.calls,
      chats: v.chats,
      total: v.calls + v.chats,
    }));

    res.json({ data: chartData });
  } catch (error) {
    console.error('Error fetching metrics chart data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get agent comparison data — real aggregation per agent
router.get('/agent-comparison', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const { timeRange = '7d' } = req.query;
    const tenantId = req.tenantId;

    const days = timeRange === '24h' ? 1 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 7;
    const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000);

    const agents = await prisma.agent.findMany({
      where: { tenantId },
      select: {
        id: true,
        name: true,
        callLogs: {
          where: { startedAt: { gte: since } },
          select: { rating: true, durationSeconds: true },
        },
      },
    });

    const comparisonData = agents.map((a) => {
      const logs = a.callLogs;
      const total = logs.length;
      const rated = logs.filter((l) => l.rating !== null);
      const thumbsUp = rated.filter((l) => l.rating === 1).length;
      const durations = logs.filter((l) => l.durationSeconds !== null).map((l) => l.durationSeconds!);
      const avgDuration = durations.length ? Math.round(durations.reduce((s, d) => s + d, 0) / durations.length * 10) / 10 : 0;

      return {
        agentId: a.id,
        agentName: a.name,
        totalInteractions: total,
        successRate: rated.length > 0 ? Math.round((thumbsUp / rated.length) * 1000) / 10 : null,
        avgResponseTime: avgDuration,
        customerSatisfaction: null, // Not applicable without surveys
      };
    });

    res.json({ agents: comparisonData });
  } catch (error) {
    console.error('Error fetching agent comparison data:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Usage summary for billing page — real counts from Postgres
router.get('/usage', async (req: Request, res: Response) => {
  try {
    const prisma: PrismaClient = req.app.get('prisma');
    const tenantId = req.tenantId;

    const [agents, callLogs, documents] = await Promise.all([
      prisma.agent.count({ where: { tenantId } }),
      prisma.callLog.count({ where: { tenantId } }),
      prisma.document.count({ where: { tenantId } }),
    ]);

    res.json({ agents, callLogs, documents });
  } catch (error) {
    console.error('Error fetching usage summary:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;