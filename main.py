import logging
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread
import nest_asyncio

# === CONFIGURATION ===
api_id = 21603561
api_hash = '64a44e5bfcf5150e7e9e237ac7a3039f'
bot_token = '6847262494:AAEgfjf7YDav02q17Jjb7Zl75h-RHeKT-ho'
quotex_bot_username = 'QuotexPartnerBot'
private_channel_invite = 'https://t.me/+ro00SU8yukw1MDRl'
bypass_trader_id = '2003'

# ✅ Your Telegram session string
SESSION_STRING = "1BVtsOLABu7DqUKmAxDwS_Q2tAMfOV3ASsBQgr5HaHSNGv-h97A7fWTXFrvhiBdPTX1mkIDWc1_mKJkSy20v6217VVPHLfWSwRn2IKDiAloqpWJBGvMiQAFMnRb5ektMhXYmp34xUHbkOzZiYp_HLCblqWq7yByhOnV39zOgP3SryiRZeuaz8hfQQoxObFa0hzBhO1aH_h1g6_5W2jmiJCN8OUtw0CVQMXn6R-2r4szLXIYPOdN8T2R80EZvB2VzrSf4Nt3JLUrnr7LUXYHdwbDxhV894e4y6eZiJOOpOxASumDk1u1ppSMFqJ0vwE_EcCXJWIBl5iHIWWbdedO4gYrRFTPYNfuI="

# === Apply async patch for Replit or Railway ===
nest_asyncio.apply()

# === Logging Setup ===
logging.basicConfig(level=logging.INFO)

# === Flask Keep-Alive ===
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# === Telethon Client for Your Personal Account ===
client = TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)

# === Telegram Bot Client ===
bot = Bot(token=bot_token)

async def check_user_with_quotex(trader_id: str) -> (bool, str):
    if trader_id.strip() == bypass_trader_id:
        logging.info("Bypass ID detected inside check_user_with_quotex.")
        return True, "Bypass successful."
    response_future = asyncio.Future()

    async def response_handler(event):
        message = event.message.message
        logging.info(f"Response from Quotex bot: {message}")

        if "Deposit" in message:
            lines = message.split('\n')
            deposit_line = next((l for l in lines if "Deposit" in l), None)
            if deposit_line:
                amount = float(''.join(filter(str.isdigit, deposit_line))) / 100
                if amount >= 10:
                    response_future.set_result((True, message))
                else:
                    response_future.set_result((False, f"Deposit is only ${amount:.2f}"))
        else:
            response_future.set_result((False, "User not found or no deposit info"))

    client.add_event_handler(response_handler, events.NewMessage(from_users=quotex_bot_username))

    try:
        await client.send_message(quotex_bot_username, trader_id)
        logging.info(f"[User Session] Sent Trader ID: {trader_id} to @QuotexPartnerBot")

        try:
            result = await asyncio.wait_for(response_future, timeout=10)
        except asyncio.TimeoutError:
            result = (False, "No response received from Quotex bot.")

    except Exception as e:
        logging.error("Error during check:", exc_info=True)
        result = (False, str(e))

    finally:
        client.remove_event_handler(response_handler, events.NewMessage(from_users=quotex_bot_username))

    return result

# === Telegram Bot Handler ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trader_id = update.message.text.strip()
    logging.info(f"Received Trader ID: '{trader_id}'")
    chat_id = update.effective_chat.id

    await context.bot.send_message(chat_id, f"🔍 Checking Trader ID: {trader_id}...")
    success, msg = await check_user_with_quotex(trader_id)

    if success:
        await context.bot.send_message(chat_id, "✅ Verification successful! Join the private channel:")
        await context.bot.send_message(chat_id, private_channel_invite)
    else:
        await context.bot.send_message(chat_id, f"❌ Verification failed: {msg}")

# === Main Bot Execution ===
async def main():
    logging.info("Starting Telegram user session...")
    await client.start()
    application = ApplicationBuilder().token(bot_token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot is running...")
    await application.run_polling()

# === Run the Bot ===
asyncio.run(main())
