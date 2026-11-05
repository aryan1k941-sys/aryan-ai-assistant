import os
import sys
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TelegramUserbot")

# Retrieve required credentials
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWLIST_IDS_STR = os.getenv("ALLOWLIST_IDS", "")

if not all([API_ID, API_HASH, GEMINI_API_KEY]):
    logger.error("Missing mandatory environment variables! Please check your .env or Render Config Vars.")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("TELEGRAM_API_ID must be an integer.")
    sys.exit(1)

# Parse allowlist IDs
ALLOWLIST = set()
if ALLOWLIST_IDS_STR.strip():
    for item in ALLOWLIST_IDS_STR.split(","):
        item = item.strip()
        if item:
            try:
                ALLOWLIST.add(int(item))
            except ValueError:
                logger.warning(f"Invalid user ID in ALLOWLIST_IDS: {item}")

# Initialize Gemini Client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Store chat history in memory per user: { user_id: [ {role, parts}, ... ] }
chat_histories = {}

# System prompt for Gemini
SYSTEM_INSTRUCTION = (
    "You are a personal Telegram AI Assistant acting on behalf of the account owner. "
    "Respond naturally, politely, and contextually. "
    "You must seamlessly understand and reply in Hindi, English, or Hinglish based on the user's input language. "
    "Keep responses helpful, concise, and friendly."
)

# Telethon client setup
if SESSION_STRING:
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    logger.info("Using StringSession for authentication.")
else:
    client = TelegramClient("personal_userbot", API_ID, API_HASH)
    logger.info("Using local session file for authentication.")

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_incoming_private_message(event):
    sender = await event.get_sender()
    if not sender or sender.bot:
        return

    sender_id = event.sender_id

    # Check allowlist if configured
    if ALLOWLIST and sender_id not in ALLOWLIST:
        logger.info(f"Ignored message from user {sender_id} (not in allowlist).")
        return

    user_text = event.text
    if not user_text:
        return

    logger.info(f"Received message from {sender_id}: {user_text}")

    # Maintain conversation history
    if sender_id not in chat_histories:
        chat_histories[sender_id] = []

    history = chat_histories[sender_id]
    history.append({"role": "user", "parts": [user_text]})

    # Limit context history to last 10 messages to prevent token bloat
    if len(history) > 10:
        history = history[-10:]
        chat_histories[sender_id] = history

    try:
        # Format history for Gemini API
        contents = []
        for msg in history:
            contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["parts"][0])]
                )
            )

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )

        reply_text = response.text
        if reply_text:
            history.append({"role": "model", "parts": [reply_text]})
            await event.reply(reply_text)
            logger.info(f"Sent reply to {sender_id}: {reply_text}")
        else:
            logger.warning(f"Empty response generated for user {sender_id}")

    except Exception as e:
        logger.error(f"Error generating Gemini AI response: {e}")

async def main():
    logger.info("Starting Telegram Personal AI Assistant Userbot...")
    await client.start()
    me = await client.get_me()
    logger.info(f"Successfully logged in as {me.first_name} (@{me.username or 'No Username'})")
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
