import json
import urllib.request
import subprocess
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import time
import os
import sys
from dotenv import load_dotenv

# Load .env automatically so users don't need to export env vars manually
load_dotenv()


# Usage: set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars.
# Optionally set TWILIO_PHONE_SID to skip interactive selection.
# Optionally set NGROK_PORT (default 8001), TWILIO_VOICE_WEBHOOK_PATH and TWILIO_MESSAGE_WEBHOOK_PATH.


def start_ngrok_port(port: int):
    """Start or discover an ngrok tunnel and return the public URL.

    This function intentionally avoids requesting reserved/dev domains and
    prefers the temporary public URL provided by the local ngrok agent or the
    system ngrok binary (which by default issues a free random domain).
    """

    def _query_local_api():
        try:
            with urllib.request.urlopen('http://127.0.0.1:4040/api/tunnels', timeout=1.0) as resp:
                data = json.load(resp)
                return data.get('tunnels', [])
        except Exception:
            return None

    # 1) If a local ngrok agent is already running, prefer its tunnel for our port
    tunnels = _query_local_api()
    if tunnels is not None:
        for t in tunnels:
            cfg = t.get('config', {})
            addr = cfg.get('addr') or ''
            if addr.endswith(f":{port}") or addr in (f"localhost:{port}", f"127.0.0.1:{port}"):
                public_url = t.get('public_url')
                if public_url:
                    print(f"Found existing ngrok tunnel '{public_url}' -> '{addr}'")
                    return public_url

    # 2) Start the system ngrok binary to ensure a free temporary domain is created.
    try:
        print(f"Starting system ngrok for port {port} (will create a temporary public URL)...")
        proc = subprocess.Popen(["ngrok", "http", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("ngrok binary not found on PATH. Install ngrok (https://ngrok.com/download) or run ngrok manually and re-run this script.")
        return None
    except Exception as e:
        print(f"Failed to start ngrok binary: {e}")
        return None

    # Poll the local ngrok agent API for the created tunnel
    public_url = None
    for _ in range(20):
        time.sleep(0.5)
        tunnels = _query_local_api()
        if not tunnels:
            continue
        for t in tunnels:
            cfg = t.get('config', {})
            addr = cfg.get('addr') or ''
            if addr.endswith(f":{port}") or addr in (f"localhost:{port}", f"127.0.0.1:{port}"):
                public_url = t.get('public_url')
                break
        if public_url:
            break

    if public_url:
        print(f"Ngrok tunnel '{public_url}' -> 'http://localhost:{port}'")
        return public_url
    else:
        print("Timed out waiting for ngrok to register the tunnel. Check 'http://127.0.0.1:4040' for more info.")
        return None


def choose_phone_number(client: Client):
    """List available incoming phone numbers and allow the user to choose one.

    Returns the chosen phone number SID (string) or None.
    """
    try:
        numbers = client.incoming_phone_numbers.list()
    except Exception as e:
        print(f"Failed to list incoming phone numbers: {e}")
        return None

    if not numbers:
        print("No phone numbers found in the Twilio account.")
        return None

    print(f"Found {len(numbers)} phone number(s):")
    for idx, num in enumerate(numbers, start=1):
        friendly = getattr(num, 'friendly_name', '')
        print(f"{idx}. {num.phone_number} (SID: {num.sid}) {friendly}")

    # If only one number, choose it
    if len(numbers) == 1:
        choice = 1
        print(f"Automatically selecting the only number: {numbers[0].phone_number}")
    else:
        # Allow non-interactive auto-selection via env var
        auto_first = os.getenv('TWILIO_AUTO_SELECT_FIRST', '').lower() in ('1', 'true', 'yes')
        if auto_first:
            choice = 1
            print(f"Auto-selecting first number: {numbers[0].phone_number}")
        else:
            # Prompt user to select a number
            try:
                selection = input(f"Select a number to update (1-{len(numbers)}) or 'q' to cancel: ").strip()
            except KeyboardInterrupt:
                print("\nSelection cancelled")
                return None

            if selection.lower() == 'q':
                print("Cancelled by user")
                return None
            try:
                choice = int(selection)
                if choice < 1 or choice > len(numbers):
                    print("Invalid selection")
                    return None
            except ValueError:
                print("Invalid input")
                return None

    selected = numbers[choice - 1]
    print(f"Selected: {selected.phone_number} (SID: {selected.sid})")
    return selected.sid


def update_number_webhook(account_sid: str, auth_token: str, phone_sid: str, voice_url: str = None, sms_url: str = None):
    client = Client(account_sid, auth_token)
    try:
        # Fetch the phone number resource to include the E.164 number in output
        try:
            number_res = client.incoming_phone_numbers(phone_sid).fetch()
            phone_number = getattr(number_res, 'phone_number', None)
        except Exception:
            phone_number = None

        update_args = {}
        if voice_url:
            update_args['voice_url'] = voice_url
        if sms_url:
            update_args['sms_url'] = sms_url

        if not update_args:
            print("No webhook URLs provided to update")
            return False

        client.incoming_phone_numbers(phone_sid).update(**update_args)

        # Friendly, readable summary
        print("\n" + "=" * 60)
        if phone_number:
            print(f"✓ Updated phone number: {phone_number}   (SID: {phone_sid})")
        else:
            print(f"✓ Updated phone SID: {phone_sid}")
        print("Set webhooks:")
        if voice_url:
            print(f"  • Voice webhook: {voice_url}")
        if sms_url:
            print(f"  • SMS webhook:   {sms_url}")
        print("=" * 60 + "\n")
        return True
    except TwilioRestException as e:
        print("Failed to update Twilio phone number webhook:")
        try:
            print(f"Twilio error {e.status} code={e.code}: {e.msg}")
        except Exception:
            print(str(e))
        return False
    except Exception as e:
        print(f"Failed to update Twilio phone number webhook: {e}")
        return False


def main():
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    env_phone_sid = os.getenv('TWILIO_PHONE_SID')
    ngrok_port = int(os.getenv('NGROK_PORT', os.getenv('PORT', '8001')))
    voice_path = os.getenv('TWILIO_VOICE_WEBHOOK_PATH', '/webhook/twilio/voice')
    sms_path = os.getenv('TWILIO_MESSAGE_WEBHOOK_PATH', '/webhook/twilio')

    if not account_sid or not auth_token:
        print('Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables')
        return

    # Start ngrok
    public_url = start_ngrok_port(ngrok_port)
    if not public_url:
        return

    voice_url = f"{public_url}{voice_path}"
    sms_url = f"{public_url}{sms_path}"

    client = Client(account_sid, auth_token)

    # Determine phone SID. If an env-provided phone SID exists, validate
    # that it's owned by the account; otherwise, prompt the user to choose.
    phone_sid = env_phone_sid
    if phone_sid:
        try:
            client.incoming_phone_numbers(phone_sid).fetch()
            print(f"Using TWILIO_PHONE_SID from environment: {phone_sid}")
        except TwilioRestException as e:
            print(f"TWILIO_PHONE_SID from env appears invalid or not owned by this account: {phone_sid}")
            try:
                print(f"Twilio error {e.status} code={e.code}: {e.msg}")
            except Exception:
                print(str(e))
            print("Falling back to interactive phone selection...")
            phone_sid = None
        except Exception as e:
            print(f"Failed to validate TWILIO_PHONE_SID: {e}")
            phone_sid = None

    if not phone_sid:
        phone_sid = choose_phone_number(client)
        if not phone_sid:
            print("No phone SID selected; aborting")
            return

    # Update webhooks (voice and SMS)
    success = update_number_webhook(account_sid, auth_token, phone_sid, voice_url=voice_url, sms_url=sms_url)
    if success:
        print("Twilio phone number webhook(s) updated successfully.")
    else:
        print("Failed to update one or more webhooks")


if __name__ == '__main__':
    main()
