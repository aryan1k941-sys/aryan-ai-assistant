====================================================================
      TELEGRAM PERSONAL AI ASSISTANT USERBOT - SETUP GUIDE
====================================================================

Project Overview:
-----------------
This is a personal Telegram Userbot built using Telethon and the latest Google Gemini SDK (`google-genai`).
It automatically responds to incoming private Telegram messages in Hindi, English, and Hinglish, maintaining
conversation context while ignoring groups, channels, and non-allowlisted users.

--------------------------------------------------------------------
1. STEP 1: GENERATE TELEGRAM STRING SESSION (LOCALLY FIRST)
--------------------------------------------------------------------
Render is a cloud environment, so it cannot prompt for phone OTP interactively.
You must generate a `TELEGRAM_SESSION_STRING` on your local machine or Termux once:

1. Install requirements locally:
   pip install telethon python-dotenv

2. Run the generator script:
   python generate_session.py

3. Follow the prompts (Enter your API ID, API Hash, Phone Number, and OTP).
4. Copy the long Session String generated on screen. Keep it safe!

--------------------------------------------------------------------
2. STEP 2: GET YOUR CREDENTIALS
--------------------------------------------------------------------
- Telegram API ID & Hash:
  1. Go to https://my.telegram.org and log in with your phone number.
  2. Click on "API Development tools".
  3. Create an application and copy your API ID and API Hash.

- Google Gemini API Key:
  1. Go to https://aistudio.google.com/
  2. Click "Get API Key" and generate a free API key.

--------------------------------------------------------------------
3. STEP 3: DEPLOY ON RENDER (BACKGROUND WORKER)
--------------------------------------------------------------------
1. Create a GitHub Repository (Public or Private) and upload all project files.
   IMPORTANT: DO NOT upload your `.env` file or session string to GitHub!

2. Log in to Render (https://render.com).
3. Click "New +" -> "Background Worker".
4. Connect your GitHub repository.
5. Configure deployment settings:
   - Name: telegram-ai-userbot
   - Region: Select nearest location
   - Branch: main
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: python main.py

6. Environment Variables Setup on Render:
   Under the "Environment Variables" section, add the following key-value pairs:
   - TELEGRAM_API_ID = <Your API ID>
   - TELEGRAM_API_HASH = <Your API Hash>
   - TELEGRAM_SESSION_STRING = <Your Generated String Session>
   - GEMINI_API_KEY = <Your Gemini API Key>
   - ALLOWLIST_IDS = <Comma-separated User IDs, e.g., 12345678,987654321> (Optional)

7. Click "Create Background Worker".

--------------------------------------------------------------------
4. LIMITATIONS & IMPORTANT NOTES
--------------------------------------------------------------------
1. Free Gemini API Limits:
   - Gemini 2.5 Flash Free Tier includes generous rate limits (15 Requests Per Minute / 1,500 Requests Per Day).
   - If exceeded, rate limit errors will appear in your logs without crashing the bot.

2. Render Free Tier Limitations:
   - Free Background Workers on Render provide 750 free instance hours per month.
   - Ensure you only have 1 active worker running so it stays 100% free month-to-month.

3. Security Notice:
   - Your String Session gives full access to your Telegram account. Never share it or push it to public repositories.

====================================================================
