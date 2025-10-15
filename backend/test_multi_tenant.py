#!/usr/bin/env python3
"""
Test script to verify multi-tenant logic implementation
"""
import asyncio
import os
from backend.backend.db import get_session
from backend.backend.models import User, Tenant, Brand, Agent
from sqlalchemy import text

async def test_multi_tenant_setup():
    """Test the multi-tenant setup by simulating user creation flow"""

    print("Testing Multi-Tenant Setup...")

    # Test data
    test_email = "test@example.com"

    async with get_session() as session:
        try:
            # Clean up any existing test data
            await session.execute(text('DELETE FROM users WHERE email = :email'), {'email': test_email})
            await session.commit()

            # Simulate the clerk_sync logic
            print("1. Checking if user exists...")
            res = await session.execute(text('SELECT id, email, tenant_id, brand_id FROM users WHERE email = :email'), {'email': test_email})
            row = res.fetchone()

            if not row:
                print("2. User doesn't exist, creating tenant and brand...")

                # Create tenant
                tenant_name = f"{test_email.split('@')[0]}'s Organization"
                tenant = Tenant(name=tenant_name)
                session.add(tenant)
                await session.flush()

                print(f"   Created tenant: {tenant.id} - {tenant.name}")

                # Create first brand under the tenant
                brand = Brand(tenant_id=tenant.id, name='Default Brand')
                session.add(brand)
                await session.flush()

                print(f"   Created brand: {brand.id} - {brand.name}")

                # Create user linked to tenant and brand
                user = User(
                    email=test_email,
                    password_hash=None,
                    tenant_id=tenant.id,
                    brand_id=brand.id
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

                print(f"   Created user: {user.id} - {user.email}")
                print(f"   User linked to tenant: {user.tenant_id}")
                print(f"   User linked to brand: {user.brand_id}")

            # Verify the relationships
            print("\n3. Verifying relationships...")

            # Check user with relationships
            user_query = await session.execute(text('''
                SELECT u.id, u.email, u.tenant_id, u.brand_id,
                       t.name as tenant_name, b.name as brand_name
                FROM users u
                LEFT JOIN tenants t ON u.tenant_id = t.id
                LEFT JOIN brands b ON u.brand_id = b.id
                WHERE u.email = :email
            '''), {'email': test_email})

            user_data = user_query.fetchone()
            if user_data:
                print(f"   User: {user_data.email}")
                print(f"   Tenant: {user_data.tenant_name} ({user_data.tenant_id})")
                print(f"   Brand: {user_data.brand_name} ({user_data.brand_id})")

                # Test tenant isolation - create an agent under this tenant
                print("\n4. Testing tenant isolation...")
                agent = Agent(
                    tenant_id=user_data.tenant_id,
                    brand_id=user_data.brand_id,
                    name='Test Agent'
                )
                session.add(agent)
                await session.commit()
                await session.refresh(agent)

                print(f"   Created agent under tenant: {agent.name} (ID: {agent.id})")
                print(f"   Agent tenant_id: {agent.tenant_id}")
                print(f"   Agent brand_id: {agent.brand_id}")

                # Verify agent belongs to correct tenant
                agent_query = await session.execute(text('''
                    SELECT a.id, a.name, a.tenant_id, a.brand_id,
                           t.name as tenant_name, b.name as brand_name
                    FROM agents a
                    LEFT JOIN tenants t ON a.tenant_id = t.id
                    LEFT JOIN brands b ON a.brand_id = b.id
                    WHERE a.id = :agent_id
                '''), {'agent_id': agent.id})

                agent_data = agent_query.fetchone()
                if agent_data:
                    print(f"   Agent belongs to tenant: {agent_data.tenant_name}")
                    print(f"   Agent belongs to brand: {agent_data.brand_name}")

            print("\n✅ Multi-tenant setup test completed successfully!")

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(test_multi_tenant_setup())