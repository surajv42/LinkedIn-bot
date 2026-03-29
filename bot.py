import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
user_conversations = {}

SYSTEM_PROMPT = """You are LinkedInGPT, an elite LinkedIn content expert and ghostwriter.

You help users with:
- Writing viral LinkedIn posts with hooks, stories, hashtags
- Content calendars and strategies
- Connection outreach messages
- Profile optimization
- Post ideas for any niche
- Rewriting and improving existing content

Always be authentic, copy-paste ready, and ask clarifying questions if needed."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """🚀 LinkedIn AI Bot - 100% Free!

Commands:
/post [topic] - Write a LinkedIn post
/ideas [field] - Get 10 post ideas  
/connect [role] - Write outreach message
/profile [role] - Optimize your profile
/calendar [niche] - Content calendar
/rewrite [text] - Improve a post
/clear - Clear history

Or just type anything naturally! 💪"""
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text(msg)

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text("📝 What topic? Example: /post leadership tips")
        return
    await generate_content(update, f"Write an engaging LinkedIn post about {topic}. Include a strong hook, story, and 3-5 hashtags. Make it ready to post.")

async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = " ".join(context.args) if context.args else None
    if not field:
        await update.message.reply_text("💡 What field? Example: /ideas software engineer")
        return
    await generate_content(update, f"Give me 10 unique LinkedIn post ideas for a {field} professional. Make them specific and engaging.")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args) if context.args else None
    if not role:
        await update.message.reply_text("🤝 Who? Example: /connect startup founder")
        return
    await generate_content(update, f"Write a warm LinkedIn connection message for a {role}. Keep it under 150 words, non-spammy.")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args) if context.args else None
    if not role:
        await update.message.reply_text("👤 Your role? Example: /profile digital marketer 5 years")
        return
    await generate_content(update, f"Optimize LinkedIn profile for {role}. Give: 1) Powerful headline 2) Summary opening 3) 3 achievement bullets.")

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    niche = " ".join(context.args) if context.args else None
    if not niche:
        await update.message.reply_text("📅 Your niche? Example: /calendar fitness coach")
        return
    await generate_content(update, f"Create a 2-week LinkedIn content calendar for a {niche}. Include daily themes and specific post ideas.")

async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("✏️ Paste your post: /rewrite [your post here]")
        return
    await generate_content(update, f"Improve this LinkedIn post for better engagement:\n\n{text}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("🗑️ Cleared! Fresh start.")

async def generate_content(update: Update, user_message: str):
    user_id = update.effective_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    user_conversations[user_id].append({"role": "user", "content": user_message})
    await update.message.chat.send_action("typing")
    try:
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *user_conversations[user_id]],
            temperature=0.7,
            max_tokens=1500,
        )
        reply = response.choices[0].message.content
        user_conversations[user_id].append({"role": "assistant", "content": reply})
        if len(user_conversations[user_id]) > 10:
            user_conversations[user_id] = user_conversations[user_id][-10:]
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        return
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("ideas", ideas))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("rewrite", rewrite))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
