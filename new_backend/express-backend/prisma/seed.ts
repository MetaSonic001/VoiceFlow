import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  // Create tenants
  const tenant1 = await prisma.tenant.upsert({
    where: { id: 'tenant-1' },
    update: {},
    create: {
      id: 'tenant-1',
      name: 'Acme Corp',
      domain: 'acme.com',
      apiKey: 'sk-acme-123',
      isActive: true
    }
  });

  const tenant2 = await prisma.tenant.upsert({
    where: { id: 'tenant-2' },
    update: {},
    create: {
      id: 'tenant-2',
      name: 'Beta Inc',
      domain: 'beta.com',
      apiKey: 'sk-beta-456',
      isActive: true
    }
  });

  // Create users
  const user1 = await prisma.user.upsert({
    where: { email: 'alice@acme.com' },
    update: {},
    create: {
      id: 'user-1',
      email: 'alice@acme.com',
      name: 'Alice',
      tenantId: tenant1.id
    }
  });

  const user2 = await prisma.user.upsert({
    where: { email: 'bob@beta.com' },
    update: {},
    create: {
      id: 'user-2',
      email: 'bob@beta.com',
      name: 'Bob',
      tenantId: tenant2.id
    }
  });

  // Create agents
  await prisma.agent.upsert({
    where: { id: 'agent-1' },
    update: {},
    create: {
      id: 'agent-1',
      name: 'Support Agent',
      systemPrompt: 'You are a helpful support agent.',
      voiceType: 'female',
      llmPreferences: { provider: 'groq', model: 'llama-3.1-70b' },
      tokenLimit: 4096,
      contextWindowStrategy: 'sliding',
      tenantId: tenant1.id,
      userId: user1.id
    }
  });

  await prisma.agent.upsert({
    where: { id: 'agent-2' },
    update: {},
    create: {
      id: 'agent-2',
      name: 'Sales Agent',
      systemPrompt: 'You are a helpful sales agent.',
      voiceType: 'male',
      llmPreferences: { provider: 'groq', model: 'llama-3.1-8b' },
      tokenLimit: 2048,
      contextWindowStrategy: 'summarize',
      tenantId: tenant2.id,
      userId: user2.id
    }
  });

  // Create sample documents
  await prisma.document.create({
    data: {
      id: 'doc-1',
      url: 'https://example.com/support-faq.pdf',
      s3Path: 'tenant-1/1234567890-support-faq.pdf',
      status: 'completed',
      content: 'Support FAQ content...',
      agentId: 'agent-1',
      tenantId: tenant1.id
    }
  });

  await prisma.document.create({
    data: {
      id: 'doc-2',
      url: 'https://example.com/sales-guide.pdf',
      s3Path: 'tenant-2/1234567890-sales-guide.pdf',
      status: 'completed',
      content: 'Sales guide content...',
      agentId: 'agent-2',
      tenantId: tenant2.id
    }
  });

  console.log('Database seeded successfully');
}

main()
  .catch((e) => {
    console.error(e);
    // Use globalThis to call process.exit at runtime without requiring @types/node
    (globalThis as any).process?.exit?.(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
