from pyngrok import ngrok
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
    """Start an ngrok tunnel and return the public URL."""
    try:
        http_tunnel = ngrok.connect(port, bind_tls=True)
        public_url = http_tunnel.public_url
        print(f'Ngrok tunnel "{public_url}" -> "http://localhost:{port}"')
        # give ngrok a moment
        time.sleep(1)
        return public_url
    except Exception as e:
        print(f"Failed to start ngrok tunnel: {e}")
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
        update_args = {}
        if voice_url:
            update_args['voice_url'] = voice_url
        if sms_url:
            update_args['sms_url'] = sms_url

        if not update_args:
            print("No webhook URLs provided to update")
            return False

        client.incoming_phone_numbers(phone_sid).update(**update_args)
        print(f"✓ Updated phone SID {phone_sid} with: {update_args}")
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
