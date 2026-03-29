import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from groq import Groq

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔥 ADD YOUR KEYS HERE (REPLACE BELOW)
GROQ_API_KEY = "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"
TELEGRAM_TOKEN = "8543795911:AAF791LA5MgjXIZeXBv-NGmid3dv809MlWU"

print("GROQ KEY:", GROQ_API_KEY)
print("TELEGRAM TOKEN:", TELEGRAM_TOKEN)

# Initialize Groq
groq_client = Groq(api_key=GROQ_API_KEY)

user_conversations = {}
pending_posts = {}

# ---------------- SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are Suraj Vishwakarma's AI LinkedIn Coach and Productivity Partner.

- Help create LinkedIn posts
- Ask smart questions
- Guide professionally
- Convert daily work into content

Language:
Hindi → Hindi + English
English → English
Posts always in English
"""

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 LinkedIn AI Bot Ready\n\n"
        "/coach\n/post topic\n/ideas field\n\n"
        "Or just chat 💬"
    )

# ---------------- AI CORE ----------------
async def generate_content(update: Update, user_message: str):
    user_id = update.effective_user.id

    if user_id not in user_conversations:
        user_conversations[user_id] = []

    user_conversations[user_id].append({"role": "user", "content": user_message})

    await update.message.chat.send_action("typing")

    response = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *user_conversations[user_id]],
        temperature=0.7,
        max_tokens=1200,
    )

    reply = response.choices[0].message.content

    user_conversations[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)

# ---------------- COMMANDS ----------------
async def coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, "Start coaching me based on my work.")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    await generate_post(update, f"Write LinkedIn post about {topic}")

async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = " ".join(context.args)
    await generate_content(update, f"Give 10 LinkedIn ideas for {field}")

# ---------------- POST WITH APPROVAL ----------------
async def generate_post(update: Update, prompt: str):
    user_id = update.effective_user.id

    response = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
    )

    post_text = response.choices[0].message.content
    pending_posts[user_id] = post_text

    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data="approve")],
        [InlineKeyboardButton("❌ Skip", callback_data="skip")]
    ]

    await update.message.reply_text(post_text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "approve":
        await query.edit_message_text("✅ Approved! Copy & post on LinkedIn.")
    else:
        await query.edit_message_text("❌ Skipped")

# ---------------- CHAT ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coach", coach))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("ideas", ideas))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")

    import asyncio
    asyncio.run(app.run_polling())
if __name__ == "__main__":
    main()
