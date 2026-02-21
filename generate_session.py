"""
Run this once locally to generate your SESSION_STRING for 4 GB uploads.
Usage:
    python3 generate_session.py

Copy the printed session string into your .env file as SESSION_STRING=
"""
from pyrogram import Client
from pyrogram.utils import compute_password_check

API_ID   = int(input("Enter API_ID: "))
API_HASH = input("Enter API_HASH: ").strip()

with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as app:
    print("\n✅ SESSION_STRING (copy this into your .env):\n")
    print(app.export_session_string())
    print()
