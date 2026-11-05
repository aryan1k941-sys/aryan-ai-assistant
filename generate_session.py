import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

print("--- Telegram Session String Generator ---")
api_id = input("Enter your TELEGRAM_API_ID: ").strip()
api_hash = input("Enter your TELEGRAM_API_HASH: ").strip()

async def generate():
    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        session_str = client.session.save()
        print("\n================ YOUR SESSION STRING ================")
        print(session_str)
        print("=====================================================")
        print("\nKeep this session string SECRET! Add it to Render Environment Variables as TELEGRAM_SESSION_STRING.")

if __name__ == "__main__":
    asyncio.run(generate())
