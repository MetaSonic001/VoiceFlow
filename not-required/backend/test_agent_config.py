#!/usr/bin/env python3
"""
Test script to verify agent configuration storage
"""
import asyncio
import os
from backend.backend.db import get_session
from backend.backend.models import AgentConfiguration, Agent, Tenant, Brand
from sqlalchemy import text

async def test_agent_configuration():
    """Test agent configuration storage and retrieval"""

    print("Testing Agent Configuration Storage...")

    # Test data
    test_email = "config-test@example.com"
    agent_name = "Test Support Agent"

    async with get_session() as session:
        try:
            # Clean up any existing test data
            await session.execute(text('DELETE FROM agent_configurations WHERE agent_name = :name'), {'name': agent_name})
            await session.execute(text('DELETE FROM agents WHERE name = :name'), {'name': agent_name})
            await session.execute(text('DELETE FROM brands WHERE name = :brand'), {'brand': 'Test Brand'})
            await session.execute(text('DELETE FROM tenants WHERE name = :tenant'), {'tenant': f"{test_email.split('@')[0]}'s Organization"})
            await session.commit()

            # Create tenant and brand (simulating user onboarding)
            tenant_name = f"{test_email.split('@')[0]}'s Organization"
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            await session.flush()

            brand = Brand(tenant_id=tenant.id, name='Test Brand')
            session.add(brand)
            await session.flush()

            # Create agent
            agent = Agent(
                tenant_id=tenant.id,
                brand_id=brand.id,
                name=agent_name,
                chroma_collection=f"test_collection_{tenant.id}"
            )
            session.add(agent)
            await session.flush()

            print(f"1. Created test agent: {agent.id}")

            # Test agent configuration data (from onboarding)
            config_data = {
                'agent_name': agent_name,
                'agent_role': 'Customer Support Agent',
                'agent_description': 'Handles customer inquiries and provides technical support',
                'personality_traits': ['friendly', 'professional', 'helpful'],
                'communication_channels': ['chat', 'email', 'voice'],
                'preferred_response_style': 'professional',
                'response_tone': 'empathetic',
                'company_name': 'TestCorp Solutions',
                'industry': 'Technology',
                'primary_use_case': 'Customer Support',
                'brief_description': 'Leading provider of AI-powered customer service',
                'behavior_rules': {
                    'always_be_polte': True,
                    'ask_for_clarification': True,
                    'provide_sources': False
                },
                'escalation_triggers': ['angry_customer', 'complex_technical_issue'],
                'knowledge_boundaries': ['cannot_process_refunds', 'cannot_access_customer_data'],
                'max_response_length': 300,
                'confidence_threshold': 0.8,
                'chroma_collection_name': agent.chroma_collection
            }

            # Create agent configuration
            config = AgentConfiguration(agent_id=agent.id, **config_data)
            session.add(config)
            await session.commit()
            await session.refresh(config)

            print(f"2. Created agent configuration: {config.id}")

            # Verify the configuration was stored correctly
            print("\n3. Verifying stored configuration...")

            stored_config = await session.execute(text('''
                SELECT
                    ac.agent_name, ac.agent_role, ac.agent_description,
                    ac.personality_traits, ac.communication_channels,
                    ac.company_name, ac.industry, ac.primary_use_case,
                    ac.behavior_rules, ac.escalation_triggers,
                    ac.chroma_collection_name, ac.max_response_length, ac.confidence_threshold,
                    a.chroma_collection as agent_chroma_collection
                FROM agent_configurations ac
                JOIN agents a ON ac.agent_id = a.id
                WHERE ac.agent_id = :agent_id
            '''), {'agent_id': agent.id})

            row = stored_config.fetchone()
            if row:
                print(f"   Agent Name: {row.agent_name}")
                print(f"   Role: {row.agent_role}")
                print(f"   Company: {row.company_name}")
                print(f"   Industry: {row.industry}")
                print(f"   Personality Traits: {row.personality_traits}")
                print(f"   Communication Channels: {row.communication_channels}")
                print(f"   Chroma Collection: {row.chroma_collection_name}")
                print(f"   Agent's Chroma Collection: {row.agent_chroma_collection}")
                print(f"   Max Response Length: {row.max_response_length}")
                print(f"   Confidence Threshold: {row.confidence_threshold}")

                # Verify ChromaDB connection
                assert row.chroma_collection_name == row.agent_chroma_collection, "Chroma collection mismatch!"

                print("\n✅ Agent configuration storage test passed!")
                print("✅ Configuration properly linked to agent's ChromaDB collection!")

            else:
                print("❌ No configuration found!")
                return False

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

    return True

if __name__ == "__main__":
    success = asyncio.run(test_agent_configuration())
    if success:
        print("\n🎉 All agent configuration tests passed!")
    else:
        print("\n💥 Agent configuration tests failed!")
        exit(1)