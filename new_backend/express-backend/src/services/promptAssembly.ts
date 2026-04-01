import { PrismaClient } from '@prisma/client';

/**
 * Assembles a dynamic system prompt for an agent by combining:
 *   1. The agent template's base system prompt (with placeholders)
 *   2. The tenant's company information
 *   3. The agent's configuration (name, custom instructions, etc.)
 *
 * Placeholders replaced:
 *   {{company_name}}        — from tenant settings
 *   {{agent_name}}          — from agent record
 *   {{capabilities}}        — from template.defaultCapabilities, formatted as bullet list
 *   {{custom_instructions}} — from agentConfiguration.customInstructions (user-editable)
 */
export async function assembleSystemPrompt(
  prisma: PrismaClient,
  agentId: string,
  tenantId: string,
): Promise<string> {
  // Load agent with template and configuration in one query
  const agent = await prisma.agent.findUnique({
    where: { id: agentId },
    include: {
      template: true,
      configuration: true,
      tenant: true,
    },
  });

  if (!agent) {
    return 'You are a helpful assistant.';
  }

  // If agent has a hardcoded systemPrompt and no template, use it as-is (backwards compat)
  if (!agent.template && agent.systemPrompt) {
    return agent.systemPrompt;
  }

  // If no template at all, fall back to generic + any description
  if (!agent.template) {
    const desc = agent.description || agent.configuration?.agentDescription || '';
    return desc
      ? `You are ${agent.name}, an AI assistant. ${desc}`
      : 'You are a helpful assistant.';
  }

  // ── Build the dynamic prompt ────────────────────────────────────────────
  const template = agent.template;
  const config = agent.configuration;
  const tenantSettings = (agent.tenant?.settings as Record<string, any>) || {};

  const companyName =
    config?.companyName ||
    tenantSettings.companyName ||
    agent.tenant?.name ||
    'the company';

  const agentName = config?.agentName || agent.name || 'the assistant';

  // Format capabilities as a bullet list
  const capabilities = Array.isArray(template.defaultCapabilities)
    ? (template.defaultCapabilities as string[]).map((c) => `• ${c}`).join('\n')
    : '';

  // Custom instructions from the agent configuration
  const customInstructions = config?.customInstructions?.trim()
    ? `\nADDITIONAL INSTRUCTIONS\n${config.customInstructions.trim()}`
    : '';

  // Replace placeholders
  let prompt = template.baseSystemPrompt;
  prompt = prompt.replace(/\{\{company_name\}\}/g, companyName);
  prompt = prompt.replace(/\{\{agent_name\}\}/g, agentName);
  prompt = prompt.replace(/\{\{capabilities\}\}/g, capabilities);
  prompt = prompt.replace(/\{\{custom_instructions\}\}/g, customInstructions);

  // Append company context from tenant settings (industry, use case, etc.)
  const contextParts: string[] = [];
  if (tenantSettings.industry) contextParts.push(`Industry: ${tenantSettings.industry}`);
  if (tenantSettings.useCase) contextParts.push(`Primary use case: ${tenantSettings.useCase}`);
  if (tenantSettings.websiteUrl) contextParts.push(`Company website: ${tenantSettings.websiteUrl}`);
  if (tenantSettings.description) contextParts.push(`Company description: ${tenantSettings.description}`);

  if (contextParts.length > 0) {
    prompt += `\n\nCOMPANY CONTEXT\n${contextParts.join('\n')}`;
  }

  // Append personality/tone from configuration
  if (config?.responseTone) {
    prompt += `\n\nResponse tone: ${config.responseTone}`;
  }

  return prompt;
}
