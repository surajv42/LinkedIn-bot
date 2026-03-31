import os
import logging
import tempfile
from urllib.parse import quote
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

from groq import Groq

# Optional OpenAI fallback
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    openai_client = None

# ---------- CONFIG ----------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=GROQ_API_KEY)

user_conversations = {}
pending_posts = {}

# ---------- SYSTEM PROMPT ----------
SYSTEM_PROMPT = """
You are LinkedInGPT — personal AI branding manager for Suraj Vishwakarma.

Write posts in first person.

HOOK RULES:
- Max 12 words
- Must create curiosity or pain

BODY:
- Short paragraphs
- Clear insights
- Practical value

CTA:
- Ask a strong engaging question

HASHTAGS:
- 3–5 relevant

STYLE TYPES:
- viral → bold, engaging
- storytelling → personal journey
- data → insights, metrics

Always end with:
READY_TO_POST: [yes]
"""

# ---------- AI ENGINE ----------
def generate_ai_response(messages):
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1200
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.warning("Groq failed, switching to OpenAI")

        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            return response.choices[0].message.content

        return "AI service error. Check API keys."

# ---------- LINKEDIN ----------
def create_linkedin_url(post):
    encoded = quote(post)
    return f"https://www.linkedin.com/feed/?shareActive=true&text={encoded}"

# ---------- COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 LinkedIn AI Manager Ready\n\n"
        "/post topic | style\n"
        "Example:\n"
        "/post AI in marketing | viral"
    )

# ---------- POST ----------
async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)

    if not text:
        await update.message.reply_text("Use: /post topic | style")
        return

    parts = text.split("|")
    topic = parts[0].strip()
    style = parts[1].strip() if len(parts) > 1 else "professional"

    prompt = f"""
    Write a LinkedIn post about: {topic}

    Style: {style}

    Follow all rules.
    """

    await generate_content(update, prompt)

# ---------- GENERATE ----------
async def generate_content(update: Update, prompt: str):
    user_id = update.effective_user.id

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}]

    await update.message.chat.send_action("typing")

    reply = generate_ai_response(messages)

    if "READY_TO_POST: [yes]" in reply:
        clean_post = reply.replace("READY_TO_POST: [yes]", "").strip()
        pending_posts[user_id] = clean_post

        keyboard = [
            [
                InlineKeyboardButton("🚀 Post", callback_data=f"post_{user_id}"),
                InlineKeyboardButton("✏️ Improve", callback_data=f"improve_{user_id}")
            ],
            [
                InlineKeyboardButton("❌ Skip", callback_data="skip")
            ]
        ]

        await update.message.reply_text(
            f"📝 *Generated Post:*\n\n{clean_post}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(reply)

# ---------- BUTTON HANDLER ----------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data.startswith("post_"):
        post = pending_posts.get(user_id)

        if post:
            url = create_linkedin_url(post)

            keyboard = [
                [InlineKeyboardButton("👉 Open LinkedIn", url=url)]
            ]

            await query.edit_message_text(
                "Click below to post on LinkedIn 👇",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif query.data.startswith("improve_"):
        post = pending_posts.get(user_id)

        if post:
            new_prompt = "Improve this LinkedIn post:\n\n" + post
            await generate_content(update, new_prompt)

    elif query.data == "skip":
        await query.edit_message_text("Skipped.")

# ---------- VOICE ----------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Processing voice...")

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            await file.download_to_drive(tmp.name)

            with open(tmp.name, "rb") as audio:
                transcription = groq_client.audio.transcriptions.create(
                    file=(tmp.name, audio),
                    model="whisper-large-v3",
                    response_format="text"
                )

        os.unlink(tmp.name)

        await update.message.reply_text(f"You said:\n{transcription}")

        await generate_content(update, transcription)

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ---------- TEXT ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)

# ---------- MAIN ----------
def main():
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_BOT_TOKEN")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
