"""
Shared pytest fixtures for VoiceFlow backend tests.
"""
import asyncio
import sys
import os
import pytest

# Make sure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
