import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from groq import Groq

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- API KEY HANDLING ----------------

GROQ_API_KEY = os.getenv("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")

# 🔥 Fallback if .env not working (PUT YOUR KEY HERE)
if not GROQ_API_KEY:
    print("⚠️ .env not working, using fallback key")
    GROQ_API_KEY = "PASTE_YOUR_GROQ_API_KEY_HERE"

# Debug check
print("DEBUG GROQ KEY:", GROQ_API_KEY)

groq_client = Groq(api_key=GROQ_API_KEY)

user_conversations = {}
pending_posts = {}

# ---------------- SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are Suraj Vishwakarma's AI LinkedIn Coach and Productivity Partner.

Profile:
- Quality Lead with 10+ years experience
- Expertise: Lean Six Sigma, QA, BPO, RCA, CAPA, Power BI
- Audience: BPO leaders, quality professionals, operations managers

Your role:
- Act like mentor + strategist + content writer
- Ask questions before answering
- Convert daily work into LinkedIn posts
- Push for clarity and real examples

Language Rules:
- If user writes in Hindi → reply in Hindi + English
- If English → reply in English
- LinkedIn posts MUST be in English
"""

# ---------------- BASIC COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """🚀 LinkedIn AI Coach Bot

/coach - Coaching mode
/daily - Daily review
/post [topic]
/ideas [field]
/connect [role]
/profile [role]
/calendar [niche]
/rewrite [text]
/announce
/clear
"""
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text(msg)

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
    await generate_content(update, "Start coaching conversation with me.")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, "Run a daily productivity review.")

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    await generate_post(update, f"Write LinkedIn post about {topic}")

async def generate_post(update: Update, prompt: str):
    user_id = update.effective_user.id

    response = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}],
    )

    post_text = response.choices[0].message.content
    pending_posts[user_id] = post_text

    keyboard = [
        [InlineKeyboardButton("✅ Approve & Post", callback_data="approve")],
        [InlineKeyboardButton("❌ Skip", callback_data="skip")]
    ]

    await update.message.reply_text(post_text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BUTTON ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "approve":
        post_text = pending_posts.get(user_id)

        await query.edit_message_text("✅ Approved! Copy & paste to LinkedIn.")

    else:
        await query.edit_message_text("❌ Skipped")

# ---------------- CHAT ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)

# ---------------- MAIN ----------------
def main():
    TELEGRAM_TOKEN = os.getenv("8543795911:AAF791LA5MgjXIZeXBv-NGmid3dv809MlWU")

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN missing")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coach", coach))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
