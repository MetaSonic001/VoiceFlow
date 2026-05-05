"""
voiceflow CLI — developer tooling for VoiceFlow agents.

Commands:
  voiceflow new <project_name>   — scaffold a new agent project
  voiceflow test                 — run simulation test suite
  voiceflow deploy               — push to hosted VoiceFlow platform
  voiceflow call <phone>         — make a test outbound call
"""
from __future__ import annotations

import json
import os
import sys
import textwrap


def _require_typer():
    try:
        import typer
        return typer
    except ImportError:
        print("typer is required for the CLI: pip install typer[all]")
        sys.exit(1)


def main():
    typer = _require_typer()
    from typing import Optional

    app = typer.Typer(help="VoiceFlow — AI Voice Agent developer CLI", add_completion=False)

    # ------------------------------------------------------------------ #
    # `voiceflow new <name>`                                               #
    # ------------------------------------------------------------------ #
    @app.command()
    def new(
        project_name: str = typer.Argument(..., help="Name of the new agent project"),
        language: str = typer.Option("en-IN", help="Default language code"),
        template: str = typer.Option("sales", help="Agent template: sales | support | survey"),
    ):
        """Scaffold a new VoiceFlow agent project."""
        base = os.path.join(os.getcwd(), project_name)
        if os.path.exists(base):
            typer.echo(f"Directory '{project_name}' already exists.", err=True)
            raise typer.Exit(1)

        os.makedirs(base)
        os.makedirs(os.path.join(base, "knowledge"))

        templates = {
            "sales": "You are a friendly sales agent. Your goal is to qualify leads and book demos.",
            "support": "You are a helpful customer support agent. Resolve issues quickly and empathetically.",
            "survey": "You are conducting a brief customer satisfaction survey. Be concise and friendly.",
        }
        system_prompt = templates.get(template, templates["sales"])

        agent_code = textwrap.dedent(f'''\
            from voiceflow import VoiceAgent, voice_tool, KnowledgeBase

            kb = KnowledgeBase()
            # kb.add("knowledge/faq.pdf")

            @voice_tool
            def book_demo(name: str, email: str, preferred_time: str) -> str:
                """Book a product demo for a prospect."""
                return f"Demo booked for {{name}} at {{preferred_time}}. Confirmation sent to {{email}}."

            agent = VoiceAgent(
                name="{project_name}",
                system_prompt="{system_prompt}",
                language="{language}",
                knowledge_base=kb,
            )
            agent.add_tool(book_demo)

            if __name__ == "__main__":
                agent.start()
        ''')

        requirements = textwrap.dedent('''\
            voiceflow
            httpx
            fastapi
            uvicorn[standard]
        ''')

        env_example = textwrap.dedent('''\
            GROQ_API_KEY=your_groq_key_here
            TWILIO_ACCOUNT_SID=ACxxxxx
            TWILIO_AUTH_TOKEN=xxxxxxx
            TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
        ''')

        with open(os.path.join(base, "agent.py"), "w") as f:
            f.write(agent_code)
        with open(os.path.join(base, "requirements.txt"), "w") as f:
            f.write(requirements)
        with open(os.path.join(base, ".env.example"), "w") as f:
            f.write(env_example)
        with open(os.path.join(base, "README.md"), "w") as f:
            f.write(f"# {project_name}\n\nVoiceFlow agent project.\n\n"
                    "## Quick start\n\n```bash\npip install -r requirements.txt\n"
                    "cp .env.example .env  # fill in your keys\n"
                    "python agent.py\n```\n")

        typer.echo(f"Created project '{project_name}'/")
        typer.echo(f"  agent.py              — edit your agent logic here")
        typer.echo(f"  knowledge/            — drop PDFs / docs here")
        typer.echo(f"  .env.example          — copy to .env and fill keys")
        typer.echo(f"\nNow run:")
        typer.echo(f"  cd {project_name} && python agent.py")

    # ------------------------------------------------------------------ #
    # `voiceflow test`                                                     #
    # ------------------------------------------------------------------ #
    @app.command()
    def test(
        agent_file: str = typer.Option("agent.py", help="Path to agent.py"),
        scenarios: int = typer.Option(5, help="Number of simulation scenarios to run"),
        threshold: float = typer.Option(0.80, help="Minimum pass-rate to succeed"),
    ):
        """Run simulation tests against the agent and print a report."""
        import importlib.util
        import asyncio

        spec = importlib.util.spec_from_file_location("_agent_module", agent_file)
        if spec is None:
            typer.echo(f"Cannot load '{agent_file}'", err=True)
            raise typer.Exit(1)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]

        agent = getattr(mod, "agent", None)
        if agent is None:
            typer.echo("No 'agent' variable found in agent file.", err=True)
            raise typer.Exit(1)

        typer.echo(f"Testing agent: {agent.name}")
        typer.echo(f"Running {scenarios} scenarios (pass-rate threshold: {threshold:.0%})")

        # Minimal simulation: engage agent with canned user messages
        test_messages = [
            "Hello, I'd like to know more about your product.",
            "What are your pricing plans?",
            "Can I speak to someone?",
            "I'm not interested, thank you.",
            "What's your refund policy?",
        ][:scenarios]

        async def _run():
            passed = 0
            for msg in test_messages:
                reply = await agent.llm.chat(
                    system_prompt=agent.system_prompt,
                    user_message=msg,
                )
                ok = bool(reply and len(reply) > 5)
                status = "PASS" if ok else "FAIL"
                typer.echo(f"  [{status}] {msg[:50]}")
                if ok:
                    passed += 1
            rate = passed / len(test_messages)
            typer.echo(f"\nResult: {passed}/{len(test_messages)} passed ({rate:.0%})")
            if rate < threshold:
                typer.echo(f"FAILED: pass rate {rate:.0%} < threshold {threshold:.0%}")
                raise typer.Exit(1)
            typer.echo("PASSED")

        asyncio.run(_run())

    # ------------------------------------------------------------------ #
    # `voiceflow deploy`                                                   #
    # ------------------------------------------------------------------ #
    @app.command()
    def deploy(
        platform_url: str = typer.Option(
            "https://api.voiceflow.ai", envvar="VOICEFLOW_PLATFORM_URL",
            help="VoiceFlow platform API URL"),
        api_key: str = typer.Option(
            ..., envvar="VOICEFLOW_API_KEY", help="Your VoiceFlow API key"),
        agent_file: str = typer.Option("agent.py", help="Path to agent.py"),
    ):
        """Deploy this agent to the hosted VoiceFlow platform (placeholder)."""
        typer.echo(f"Deploying '{agent_file}' to {platform_url} …")
        typer.echo("(deploy command will upload agent config + knowledge base)")
        typer.echo("Not yet implemented — contact support@voiceflow.ai for early access.")

    # ------------------------------------------------------------------ #
    # `voiceflow call <phone>`                                             #
    # ------------------------------------------------------------------ #
    @app.command()
    def call(
        phone: str = typer.Argument(..., help="Phone number in E.164 format, e.g. +919876543210"),
        from_number: str = typer.Option(
            ..., envvar="TWILIO_PHONE_NUMBER", help="Your Twilio number"),
        webhook_url: str = typer.Option(
            ..., envvar="VOICEFLOW_WEBHOOK_URL",
            help="Public webhook URL where your agent is listening"),
        account_sid: str = typer.Option("", envvar="TWILIO_ACCOUNT_SID"),
        auth_token: str = typer.Option("", envvar="TWILIO_AUTH_TOKEN"),
    ):
        """Make a test outbound call via Twilio."""
        import asyncio
        from voiceflow.plugins.telephony import TwilioTelephony

        if not account_sid or not auth_token:
            typer.echo("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars.", err=True)
            raise typer.Exit(1)

        telephony = TwilioTelephony(account_sid, auth_token, from_number)

        async def _call():
            sid = await telephony.make_call(to=phone, from_=from_number, webhook_url=webhook_url)
            typer.echo(f"Call initiated: {sid}")

        asyncio.run(_call())

    app()


if __name__ == "__main__":
    main()
