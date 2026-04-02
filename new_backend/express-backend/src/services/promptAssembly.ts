import { PrismaClient } from '@prisma/client';
import { AssembledContext, PolicyRule, FewShotExample } from './contextInjector';

// ─────────────────────────────────────────────────────────────────────────────
// Dynamic Prompt Assembly — Task 18
//
// Consumes the full 5-layer AssembledContext (from ContextInjector) and
// produces the final system prompt string fed into the LLM.
//
// Prompt structure (in order):
//   1. Global safety rules (immutable)
//   2. Tenant context + tenant policies
//   3. Brand voice + brand topic constraints
//   4. Agent persona + base template + custom instructions + agent policies
//   5. Few-shot examples from retraining pipeline (in-context learning)
//   6. Escalation rules (if any)
//   7. Policy summary (merged, human-readable)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Build the final system prompt from a fully assembled context.
 * This is the primary entry point used by the query pipeline.
 */
export function buildSystemPrompt(ctx: AssembledContext): string {
  const sections: string[] = [];

  // ── Section 1: Global safety rules ──────────────────────────────────────
  sections.push(ctx.globalRules);

  // ── Section 2: Tenant context ───────────────────────────────────────────
  {
    const parts: string[] = [];
    parts.push(`ORGANISATION: ${ctx.tenantName}`);
    if (ctx.tenantIndustry) parts.push(`Industry: ${ctx.tenantIndustry}`);
    if (ctx.tenantPolicySummary) parts.push(ctx.tenantPolicySummary);
    sections.push(`TENANT CONTEXT\n${parts.join('\n')}`);
  }

  // ── Section 3: Brand voice ──────────────────────────────────────────────
  if (ctx.brandId) {
    const parts: string[] = [];
    if (ctx.brandName) parts.push(`Brand: ${ctx.brandName}`);
    if (ctx.brandVoice) parts.push(`Voice & tone guidelines:\n${ctx.brandVoice}`);
    if (ctx.brandAllowedTopics.length)
      parts.push(`Allowed topics: ${ctx.brandAllowedTopics.join(', ')}`);
    if (ctx.brandRestrictedTopics.length)
      parts.push(`Restricted topics (do NOT discuss): ${ctx.brandRestrictedTopics.join(', ')}`);
    sections.push(`BRAND GUIDELINES\n${parts.join('\n')}`);
  }

  // ── Section 4: Agent persona + template + instructions ──────────────────
  {
    const parts: string[] = [];
    parts.push(`You are ${ctx.agentName}.`);
    if (ctx.agentPersona) parts.push(ctx.agentPersona);

    // Base system prompt from template (with placeholder replacement)
    if (ctx.agentBasePrompt) {
      let base = ctx.agentBasePrompt;
      base = base.replace(/\{\{company_name\}\}/g, ctx.tenantName);
      base = base.replace(/\{\{agent_name\}\}/g, ctx.agentName);
      base = base.replace(
        /\{\{capabilities\}\}/g,
        ctx.agentCapabilities.map((c) => `• ${c}`).join('\n'),
      );
      base = base.replace(
        /\{\{custom_instructions\}\}/g,
        ctx.agentCustomInstructions ? `\n${ctx.agentCustomInstructions}` : '',
      );
      parts.push(base);
    }

    if (ctx.agentCustomInstructions && !ctx.agentBasePrompt) {
      parts.push(`ADDITIONAL INSTRUCTIONS\n${ctx.agentCustomInstructions}`);
    }

    sections.push(`AGENT CONFIGURATION\n${parts.join('\n')}`);
  }

  // ── Section 5: Few-shot examples from retraining ────────────────────────
  if (ctx.fewShotExamples?.length) {
    const examples = ctx.fewShotExamples
      .map(
        (ex: FewShotExample, i: number) =>
          `Example ${i + 1}:\n  User: "${ex.userQuery}"\n  You: "${ex.idealResponse}"`,
      )
      .join('\n\n');
    sections.push(
      `LEARNED EXAMPLES (respond similarly for equivalent queries):\n${examples}`,
    );
  }

  // ── Section 6: Escalation rules ─────────────────────────────────────────
  if (ctx.agentEscalationRules?.length) {
    const escalation = ctx.agentEscalationRules
      .map(
        (r: any, i: number) =>
          `${i + 1}. ${r.trigger || r.condition || 'Unknown trigger'} → ${r.action || 'escalate'}`,
      )
      .join('\n');
    sections.push(`ESCALATION RULES\n${escalation}`);
  }

  // ── Section 7: Merged policy summary ────────────────────────────────────
  const policyBlock = buildPolicySummaryBlock(ctx.mergedPolicyRules);
  if (policyBlock) sections.push(policyBlock);

  return sections.join('\n\n---\n\n');
}

function buildPolicySummaryBlock(rules: PolicyRule[]): string | null {
  if (!rules.length) return null;
  const restrict = rules.filter((r) => r.type === 'restrict');
  const require_ = rules.filter((r) => r.type === 'require');

  const parts: string[] = ['ACTIVE POLICY RULES'];
  if (restrict.length)
    parts.push(
      'Restricted:\n' + restrict.map((r) => `• [${r.target}] ${r.value}`).join('\n'),
    );
  if (require_.length)
    parts.push(
      'Required (prioritise these):\n' +
        require_.map((r) => `• [${r.target}] ${r.value}`).join('\n'),
    );

  return parts.join('\n');
}

// ─────────────────────────────────────────────────────────────────────────────
// Legacy function — kept for backwards compatibility with existing callers
// that have not migrated to ContextInjector yet.
// ─────────────────────────────────────────────────────────────────────────────
export async function assembleSystemPrompt(
  prisma: PrismaClient,
  agentId: string,
  tenantId: string,
): Promise<string> {
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

  if (!agent.template && agent.systemPrompt) {
    return agent.systemPrompt;
  }

  if (!agent.template) {
    const desc = agent.description || agent.configuration?.agentDescription || '';
    return desc
      ? `You are ${agent.name}, an AI assistant. ${desc}`
      : 'You are a helpful assistant.';
  }

  const template = agent.template;
  const config = agent.configuration;
  const tenantSettings = (agent.tenant?.settings as Record<string, any>) || {};

  const companyName =
    config?.companyName ||
    tenantSettings.companyName ||
    agent.tenant?.name ||
    'the company';

  const agentName = config?.agentName || agent.name || 'the assistant';

  const capabilities = Array.isArray(template.defaultCapabilities)
    ? (template.defaultCapabilities as string[]).map((c) => `• ${c}`).join('\n')
    : '';

  const customInstructions = config?.customInstructions?.trim()
    ? `\nADDITIONAL INSTRUCTIONS\n${config.customInstructions.trim()}`
    : '';

  let prompt = template.baseSystemPrompt;
  prompt = prompt.replace(/\{\{company_name\}\}/g, companyName);
  prompt = prompt.replace(/\{\{agent_name\}\}/g, agentName);
  prompt = prompt.replace(/\{\{capabilities\}\}/g, capabilities);
  prompt = prompt.replace(/\{\{custom_instructions\}\}/g, customInstructions);

  const contextParts: string[] = [];
  if (tenantSettings.industry) contextParts.push(`Industry: ${tenantSettings.industry}`);
  if (tenantSettings.useCase) contextParts.push(`Primary use case: ${tenantSettings.useCase}`);
  if (tenantSettings.websiteUrl) contextParts.push(`Company website: ${tenantSettings.websiteUrl}`);
  if (tenantSettings.description) contextParts.push(`Company description: ${tenantSettings.description}`);

  if (contextParts.length > 0) {
    prompt += `\n\nCOMPANY CONTEXT\n${contextParts.join('\n')}`;
  }

  if (config?.responseTone) {
    prompt += `\n\nResponse tone: ${config.responseTone}`;
  }

  return prompt;
}
