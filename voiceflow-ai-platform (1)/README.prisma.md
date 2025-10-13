Prisma setup and Clerk server-side verification

This Next.js app includes a Prisma schema at `prisma/schema.prisma` which mirrors a subset of the backend models (User, Tenant, Agent, OnboardingProgress).

Environment variables required:
- DATABASE_URL - PostgreSQL connection string used by Prisma
- BACKEND_URL - URL of the Python backend (e.g. http://localhost:8000)
- BACKEND_API_KEY - API key for server-to-server calls to the Python backend
- CLERK_API_KEY - (optional) Clerk server API key if you want to fetch user details server-side

Setup steps (from project root `voiceflow-ai-platform (1)`):

```bash
# install JS deps
npm install

# install Prisma tooling
npx prisma generate
# create DB tables from Prisma schema (for auth models)
npx prisma db push
```

Notes:
- This project now routes client Clerk sync through `POST /api/auth/clerk_sync` which verifies the Clerk session using `@clerk/nextjs/server` and then forwards the verified email to the Python backend `/auth/clerk_sync` using BACKEND_API_KEY. The backend will create or upsert the user and issue the backend JWT.
- For production, ensure BACKEND_API_KEY is a strong secret and communicated only server-to-server.
