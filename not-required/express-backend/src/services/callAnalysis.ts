import axios from 'axios';

interface CallAnalysisResult {
  callerType: string;
  primaryTopic: string;
  satisfactionSignal: string;
  needsFollowup: boolean;
  urgencyLevel: string;
  summary: string;
  keyTopics: string[];
}

const FALLBACK: CallAnalysisResult = {
  callerType: 'unknown',
  primaryTopic: 'unknown',
  satisfactionSignal: 'unknown',
  needsFollowup: false,
  urgencyLevel: 'low',
  summary: 'Analysis could not be completed.',
  keyTopics: [],
};

/**
 * Post-call LLM analysis of a phone conversation.
 * Uses Groq (Llama 3.1) to extract structured metadata from the transcript.
 * Designed to run non-blocking after the call has ended.
 */
export async function analyzeCall(
  conversation: { role: string; content: string }[],
): Promise<CallAnalysisResult> {
  if (!conversation.length) {
    return { ...FALLBACK, summary: 'No conversation recorded.' };
  }

  const groqKey = process.env.GROQ_API_KEY;
  if (!groqKey) {
    console.warn('GROQ_API_KEY not set — skipping call analysis');
    return FALLBACK;
  }

  const formatted = conversation
    .map((m) => `${m.role === 'user' ? 'Caller' : 'Agent'}: ${m.content}`)
    .join('\n');

  const prompt = `Analyze this phone call transcript and extract structured information.

TRANSCRIPT:
${formatted}

Return a JSON object with EXACTLY these fields:
{
  "callerType": "customer|prospect|employee|vendor|unknown",
  "primaryTopic": "one short phrase describing the main topic",
  "satisfactionSignal": "satisfied|neutral|frustrated|unknown",
  "needsFollowup": true or false,
  "urgencyLevel": "low|medium|high",
  "summary": "2-3 sentence summary of the call",
  "keyTopics": ["array", "of", "topics", "discussed"]
}

Return ONLY the JSON object, nothing else.`;

  try {
    const response = await axios.post(
      'https://api.groq.com/openai/v1/chat/completions',
      {
        model: 'llama-3.1-8b-instant',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.1,
        max_tokens: 500,
      },
      {
        headers: {
          Authorization: `Bearer ${groqKey}`,
          'Content-Type': 'application/json',
        },
        timeout: 15000,
      },
    );

    const text = response.data.choices?.[0]?.message?.content || '';
    const cleaned = text.replace(/```json?\n?/g, '').replace(/```\n?/g, '').trim();
    return JSON.parse(cleaned);
  } catch (error) {
    console.error('Call analysis LLM error:', error);
    return FALLBACK;
  }
}
