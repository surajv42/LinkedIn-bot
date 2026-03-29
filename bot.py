import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from groq import Groq

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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

Always:
- Be practical
- Be structured
- Be insightful
"""

# ---------------- BASIC COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """🚀 LinkedIn AI Coach Bot

Commands:
/coach - Start coaching conversation
/daily - Daily productivity check
/post [topic]
/ideas [field]
/connect [role]
/profile [role]
/calendar [niche]
/rewrite [text]
/announce - AI-managed profile post
/clear - Reset chat

Or just chat normally 💬
"""
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text(msg)

# ---------------- COACH MODE ----------------
async def coach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, """
Start coaching me.

Ask:
- What did I work on today?
- Any problem solved?
- Any insight?

Then suggest a LinkedIn post.
""")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, """
Run daily check:

1. What did I accomplish?
2. Challenges?
3. Learnings?
4. Suggest LinkedIn post
""")

# ---------------- LINKEDIN FUNCTIONS ----------------
async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args)
    await generate_post(update, f"Write LinkedIn post about {topic}")

async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = " ".join(context.args)
    await generate_content(update, f"Give 10 LinkedIn ideas for {field}")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args)
    await generate_content(update, f"Write connection message for {role}")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args)
    await generate_content(update, f"Optimize LinkedIn profile for {role}")

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    niche = " ".join(context.args)
    await generate_content(update, f"Create 2-week content calendar for {niche}")

async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    await generate_content(update, f"Improve this post:\n{text}")

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_post(update, "Write a post announcing my profile is AI-assisted but insights are mine")

# ---------------- AI RESPONSE ----------------
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
        max_tokens=1500,
    )

    reply = response.choices[0].message.content

    user_conversations[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)

# ---------------- POST WITH APPROVAL ----------------
async def generate_post(update: Update, prompt: str):
    user_id = update.effective_user.id

    response = groq_client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1200,
    )

    post_text = response.choices[0].message.content

    pending_posts[user_id] = post_text

    keyboard = [
        [InlineKeyboardButton("✅ Approve & Post", callback_data="approve")],
        [InlineKeyboardButton("❌ Skip", callback_data="skip")]
    ]

    await update.message.reply_text(post_text, reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BUTTON HANDLER ----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "approve":
        post_text = pending_posts.get(user_id)

        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")

        try:
            from linkedin_api import Linkedin
            api = Linkedin(email, password)
            api.submit_share(commentary=post_text)

            await query.edit_message_text("✅ Posted to LinkedIn!")

        except Exception as e:
            await query.edit_message_text(f"❌ Failed: {str(e)}")

    else:
        await query.edit_message_text("❌ Skipped")

# ---------------- VOICE HANDLER ----------------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    file_path = "voice.ogg"
    await file.download_to_drive(file_path)

    transcription = groq_client.audio.transcriptions.create(
        file=open(file_path, "rb"),
        model="whisper-large-v3"
    )

    text = transcription.text
    await generate_content(update, text)

# ---------------- GENERAL CHAT ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)

# ---------------- CLEAR ----------------
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("🗑️ Reset done")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("coach", coach))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("ideas", ideas))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("rewrite", rewrite))
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("clear", clear))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
