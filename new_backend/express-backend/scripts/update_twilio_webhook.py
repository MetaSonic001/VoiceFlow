#!/usr/bin/env python3
"""
Script to update Twilio webhook URL for voice calls.
This script uses ngrok to create a public tunnel to the local server
and updates the Twilio phone number webhook URL.
"""

import os
import requests
import json
import sys
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

def get_ngrok_url():
    """Get the current ngrok tunnel URL"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        data = response.json()
        tunnels = data.get('tunnels', [])

        for tunnel in tunnels:
            if tunnel['proto'] == 'https':
                return tunnel['public_url']

        print("No HTTPS tunnel found. Make sure ngrok is running with: ngrok http 3000")
        return None
    except Exception as e:
        print(f"Error getting ngrok URL: {e}")
        print("Make sure ngrok is running: ngrok http 3000")
        return None

def update_twilio_webhook(webhook_url):
    """Update Twilio phone number webhook URL"""
    try:
        # Get Twilio credentials from environment
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        phone_number_sid = os.getenv('TWILIO_PHONE_NUMBER_SID')

        if not all([account_sid, auth_token, phone_number_sid]):
            print("Missing Twilio environment variables. Please set:")
            print("- TWILIO_ACCOUNT_SID")
            print("- TWILIO_AUTH_TOKEN")
            print("- TWILIO_PHONE_NUMBER_SID")
            return False

        # Initialize Twilio client
        client = Client(account_sid, auth_token)

        # Update webhook URL for voice calls
        phone_number = client.incoming_phone_numbers(phone_number_sid).update(
            voice_url=f"{webhook_url}/api/twilio/voice",
            voice_method="POST"
        )

        print(f"Successfully updated Twilio webhook URL to: {webhook_url}/api/twilio/voice")
        print(f"Phone number: {phone_number.phone_number}")
        return True

    except Exception as e:
        print(f"Error updating Twilio webhook: {e}")
        return False

def main():
    print("VoiceFlow Twilio Webhook Updater")
    print("=" * 40)

    # Get ngrok URL
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        sys.exit(1)

    print(f"Found ngrok URL: {ngrok_url}")

    # Update Twilio webhook
    if update_twilio_webhook(ngrok_url):
        print("\n✅ Twilio webhook updated successfully!")
        print("Your phone number should now be able to receive voice calls.")
        print(f"Voice endpoint: {ngrok_url}/api/twilio/voice")
    else:
        print("\n❌ Failed to update Twilio webhook")
        sys.exit(1)

if __name__ == "__main__":
    main()