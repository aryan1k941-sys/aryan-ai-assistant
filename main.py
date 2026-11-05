import os
import sys
import asyncio
import logging
import random
from dotenv import load_dotenv
from telethon import TelegramClient, events
from google import genai
from google.genai import types

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TelegramUserbot")

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWLIST_IDS_STR = os.getenv("ALLOWLIST_IDS", "")

if not all([API_ID, API_HASH, GEMINI_API_KEY]):
    logger.error("Missing mandatory environment variables. Check Render Environment.")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("TELEGRAM_API_ID must be an integer.")
    sys.exit(1)

ALLOWLIST = set()
if ALLOWLIST_IDS_STR.strip():
    for item in ALLOWLIST_IDS_STR.split(","):
        item = item.strip()
        if item:
            try:
                ALLOWLIST.add(int(item))
            except ValueError:
                logger.warning("Invalid user ID in ALLOWLIST_IDS: %s", item)

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a personal Telegram AI Assistant acting on behalf of the account owner. "
    "Respond naturally, politely, and contextually. "
    "Understand and reply in Hindi, English, or Hinglish based on the user's language. "
    "Keep responses helpful, concise, and friendly."
)

# Primary stable model, then a lighter fallback if the primary is temporarily busy.
GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite"),
]

# Avoid duplicate model names if environment variables happen to match.
GEMINI_MODELS = list(dict.fromkeys(GEMINI_MODELS))

chat_histories = {}

if SESSION_STRING:
    from telethon.sessions import StringSession
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    logger.info("Using StringSession for authentication.")
else:
    client = TelegramClient("personal_userbot", API_ID, API_HASH)
    logger.info("Using local session file for authentication.")


def is_temporary_error(error):
    """Identify errors that are commonly temporary (overload/rate-limit/server errors)."""
    status = getattr(error, "code", None) or getattr(error, "status_code", None)
    message = str(error).lower()
    if status in (408, 429, 500, 502, 503, 504):
        return True
    return any(term in message for term in (
        "503", "service unavailable", "high demand", "429",
        "resource_exhausted", "too many requests", "500",
        "internal server error", "502", "504", "deadline"
    ))


async def generate_reply(history):
    contents = []
    for msg in history:
        contents.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["parts"][0])]
            )
        )

    last_error = None
    for model in GEMINI_MODELS:
        # Three attempts per model, with exponential backoff and a little jitter.
        for attempt in range(3):
            try:
                response = await asyncio.to_thread(
                    gemini_client.models.generate_content,
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7,
                    ),
                )
                if response and response.text:
                    logger.info("Gemini response generated using model %s", model)
                    return response.text
                raise RuntimeError(f"Gemini returned an empty response from {model}")
            except Exception as error:
                last_error = error
                if not is_temporary_error(error):
                    logger.exception("Non-retryable Gemini error on %s", model)
                    break

                if attempt < 2:
                    wait_seconds = min(2 ** (attempt + 1), 20) + random.uniform(0, 1)
                    logger.warning(
                        "Gemini model %s temporarily unavailable (attempt %s/3). "
                        "Retrying in %.1f seconds. Error: %s",
                        model, attempt + 1, wait_seconds, error
                    )
                    await asyncio.sleep(wait_seconds)
                else:
                    logger.warning("Gemini model %s failed after 3 attempts: %s", model, error)

    raise RuntimeError(f"All configured Gemini models failed. Last error: {last_error}")


@client.on(events.NewMessage(incoming=True, func=lambda event: event.is_private))
async def handle_incoming_private_message(event):
    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False):
        return

    sender_id = event.sender_id
    if ALLOWLIST and sender_id not in ALLOWLIST:
        logger.info("Ignored message from user %s (not in allowlist).", sender_id)
        return

    user_text = event.raw_text
    if not user_text:
        return

    logger.info("Received private message from user %s", sender_id)

    history = chat_histories.setdefault(sender_id, [])
    history.append({"role": "user", "parts": [user_text]})
    if len(history) > 10:
        del history[:-10]

    try:
        reply_text = await generate_reply(history)
        history.append({"role": "model", "parts": [reply_text]})
        if len(history) > 10:
            del history[:-10]
        await event.reply(reply_text)
        logger.info("Sent AI reply to user %s", sender_id)
    except Exception as error:
        logger.error("Could not generate reply for user %s: %s", sender_id, error)
        # Remove the unanswered user turn so it is not repeatedly sent as stale context.
        if history and history[-1].get("role") == "user":
            history.pop()
        try:
            await event.reply(
                "Sorry, AI service abhi busy hai. Main thodi der mein dobara try karunga. "
                "Please apna message phir se bhej dein."
            )
        except Exception:
            logger.exception("Could not send temporary-error notice to user %s", sender_id)


async def main():
    logger.info("Starting Telegram Personal AI Assistant Userbot...")
    await client.start()
    me = await client.get_me()
    logger.info(
        "Successfully logged in as %s (@%s)",
        me.first_name, me.username or "No Username"
    )
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
