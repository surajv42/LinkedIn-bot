import logging
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
from groq import Groq

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔥 PUT YOUR REAL KEYS HERE
GROQ_API_KEY = "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"
TELEGRAM_TOKEN = "8543795911:AAF791LA5MgjXIZeXBv-NGmid3dv809MlWU"

print("GROQ KEY:", GROQ_API_KEY)
print("TELEGRAM TOKEN:", TELEGRAM_TOKEN)

groq_client = Groq(api_key=GROQ_API_KEY)

user_conversations = {}
pending_posts = {}

# ---------------- SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are a LinkedIn AI coach.

- Help create LinkedIn posts
- Ask smart questions
- Keep responses professional
- Convert daily work into content
"""

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Bot Ready\n\n"
        "/coach\n/post topic\n/ideas field\n\n"
        "Or just chat 💬"
    )

# ---------------- AI RESPONSE ----------------
async def generate_content(update: Update, text: str):
    user_id = update.effective_user.id

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    user_conversations[user_id].append({"role": "user", "content": text})

    response = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *user_conversations[user_id],
        ],
        max_tokens=800,
    )

    reply = response.choices[0].message.content

    user_conversations[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)

# ---------------- COMMANDS ----------------
async def coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, "Start coaching me.")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    await generate_post(update, topic)

async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    await generate_content(update, f"Give LinkedIn ideas for {topic}")

# ---------------- POST ----------------
async def generate_post(update: Update, topic: str):
    user_id = update.effective_user.id

    response = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Write LinkedIn post about {topic}"},
        ],
    )

    post_text = response.choices[0].message.content
    pending_posts[user_id] = post_text

    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data="approve")],
        [InlineKeyboardButton("❌ Skip", callback_data="skip")],
    ]

    await update.message.reply_text(
        post_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- BUTTON ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "approve":
        await query.edit_message_text("✅ Approved! Copy & post on LinkedIn.")
    else:
        await query.edit_message_text("❌ Skipped")

# ---------------- CHAT ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)

# ---------------- MAIN ----------------
async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coach", coach))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("ideas", ideas))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")

    # ✅ THIS LINE MAKES BOT RESPOND
    await app.run_polling(close_loop=False)

# ---------------- RUN ----------------
if __name__ == "__main__":
    import asyncio

    try:
        asyncio.get_running_loop()
        # If loop already exists → use it
        asyncio.create_task(main())
    except RuntimeError:
        # No loop → create one
        asyncio.run(main())    
