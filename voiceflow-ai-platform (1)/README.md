VoiceFlow Frontend (Next.js)

This folder contains the Next.js frontend for onboarding and managing agents. The onboarding flow has been wired to the backend APIs (FastAPI) to perform company creation, agent creation, knowledge upload, voice config, channel setup (Twilio number selection), and deploy/go-live.

What changed recently

- Onboarding components now persist intermediate state to `localStorage` and call the backend for each step.
- Channel setup will list Twilio incoming phone numbers (when configured) and return the selected `phone_number` to the backend.
- Go-live step uses the backend deploy endpoint which will attempt to update the Twilio incoming phone number webhook when Twilio env vars are present.

Environment (.env.example)

# Frontend – copy to `.env.local`
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_PUBLIC_BASE_URL=http://localhost:3000

Quick start (Windows cmd.exe)

1) Install Node deps:
   cd "voiceflow-ai-platform (1)"
   npm install

2) Run dev server:
   npm run dev

Notes

- You must run `npm install` before `npm run dev` or `npx tsc` will fail.
- If Twilio is not configured on the backend the Channel Setup step will still allow continuing but will not automatically rewire incoming number webhooks.
