import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    stmts = [
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "telephonyProvider" TEXT DEFAULT \'twilio-gather\'',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "contextBreakdown" JSONB',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "welcomeMessage" TEXT',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "postCallActions" JSONB',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "languageConfig" JSONB',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "callerPersonas" JSONB',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "simulationSuite" JSONB',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "deploymentReadinessScore" INTEGER',
        'ALTER TABLE agents ADD COLUMN IF NOT EXISTS "versionNumber" INTEGER DEFAULT 1',
    ]
    async with engine.begin() as conn:
        for s in stmts:
            print('Executing:', s)
            await conn.execute(text(s))
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
