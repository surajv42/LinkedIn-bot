import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
user_conversations = {}
pending_posts = {}

SYSTEM_PROMPT = """You are LinkedInGPT — the personal LinkedIn AI manager for Suraj Vishwakarma.

=== SURAJ'S PROFILE ===
Name: Suraj Vishwakarma
Location: Vadodara, India
Current Role: Quality Lead & Business Quality Consultant at Etech Global Services (Jun 2025 - Present)
LinkedIn: linkedin.com/in/surajv42

Professional Summary:
Strategic Quality Lead & Business Consultant with 10+ years of experience in quality assurance, audit governance, and performance management across BPO, healthcare, and service operations. Lean Six Sigma certified professional specializing in multi-process quality frameworks, business insights, and client consulting.

Key Strengths: Quality Governance, Multi-Process QA, RCA & CAPA, CSAT/FCR Metrics, Team Leadership, Power BI & Excel Dashboards, Lean Six Sigma, Process Excellence

Career: Etech Global Services > Kochar Infotech > Wellness Forever Medicare > Medlife International > Zorticos Lifesciences

Certifications: Lean Six Sigma Professional (Expert), Power BI, Excel Dashboard, SQL

Target Audience: Quality professionals, BPO leaders, operations managers, business consultants
Goals: Build personal brand as quality and process excellence expert, attract consulting opportunities
Tone: Professional yet approachable, data-driven, confident, first-person voice

Best Topics: Quality management, Lean Six Sigma, BPO insights, CSAT improvement, leadership, Power BI tips, career lessons, process improvement

=== LANGUAGE RULES ===
- If user writes in Hindi or Hinglish, respond in Hindi AND English both
- If user writes in English, respond in English only
- Always write LinkedIn posts in English
- For voice messages, understand Hindi or English and respond accordingly

=== POST FORMAT ===
Always write posts AS Suraj in first person.
1. Hook - strong first line
2. Body - short paragraphs, 1-2 lines each
3. CTA - question or engagement prompt
4. Hashtags - 3-5 relevant ones like #QualityManagement #LeanSixSigma #BPO #ProcessExcellence #Leadership

When you write a LinkedIn post, always end your response with exactly this line:
READY_TO_POST: [yes]"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "Hey Suraj! Main hoon aapka LinkedIn AI Manager!\n\n"
        "Main jaanta hoon aapka poora profile:\n"
        "Quality Lead & Business Consultant\n"
        "10+ years BPO & Healthcare experience\n"
        "Lean Six Sigma Expert\n"
        "Vadodara, India\n\n"
        "Commands:\n"
        "/post [topic] - LinkedIn post likhna\n"
        "/ideas - 10 post ideas aapke niche ke liye\n"
        "/connect [role] - Outreach message\n"
        "/profile - Profile improve karna\n"
        "/calendar - 2-week content calendar\n"
        "/rewrite [text] - Post improve karna\n"
        "/announce - AI managed profile post banana\n"
        "/clear - History clear karo\n\n"
        "Voice messages bhi bhej sakte ho!\n"
        "Hindi ya English - dono samajhta hoon!"
    )
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text(msg)


async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text(
            "Kis topic par post likhun?\n\n"
            "Example:\n"
            "/post lessons from 10 years in quality management\n"
            "/post how to improve CSAT in BPO"
        )
        return
    await generate_content(
        update,
        "Write a LinkedIn post for Suraj about: " + topic + ". Write in first person as Suraj. End with READY_TO_POST: [yes]"
    )


async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(
        update,
        "Give Suraj 10 specific LinkedIn post ideas based on his background in quality management, BPO, Lean Six Sigma, and business consulting. Make them specific and engaging."
    )


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args) if context.args else None
    if not role:
        await update.message.reply_text(
            "Kisko connect karna hai?\n"
            "Example: /connect VP of Operations at BPO"
        )
        return
    await generate_content(
        update,
        "Write a LinkedIn connection message from Suraj Vishwakarma (Quality Lead & Business Consultant) to a " + role + ". Keep it warm, specific, non-spammy, under 150 words."
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(
        update,
        "Suggest improvements for Suraj's LinkedIn: 1) A powerful headline, 2) A strong About section opening, 3) 3 achievement-focused bullet points for his current role at Etech Global Services."
    )


async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(
        update,
        "Create a 2-week LinkedIn content calendar for Suraj Vishwakarma. Mix topics: quality tips, BPO insights, Lean Six Sigma, leadership stories, Power BI tips, career lessons. Include day, theme, and specific post angle for each day."
    )


async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("Post paste karo:\n/rewrite [aapka post yahan]")
        return
    await generate_content(
        update,
        "Rewrite this LinkedIn post for Suraj with a better hook and stronger CTA. End with READY_TO_POST: [yes]\n\n" + text
    )


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = (
        "Write a LinkedIn post for Suraj Vishwakarma announcing that his LinkedIn profile is now being managed with AI assistance. "
        "The post should be authentic and professional. "
        "Explain that AI helps him share more consistent insights from his 10+ years of quality management experience. "
        "Emphasize that all thoughts and expertise are 100% his own - AI just helps him express them better and more consistently. "
        "Invite his network to engage and give feedback. "
        "Make it exciting and forward-thinking for the quality management and BPO community. "
        "End with READY_TO_POST: [yes]"
    )
    await generate_content(update, prompt)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("History clear ho gayi! Fresh start.")


async def generate_content(update: Update, user_message: str):
    user_id = update.effective_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    user_conversations[user_id].append({"role": "user", "content": user_message})
    await update.message.chat.send_action("typing")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + user_conversations[user_id],
            temperature=0.7,
            max_tokens=1500,
        )
        reply = response.choices[0].message.content
        user_conversations[user_id].append({"role": "assistant", "content": reply})

        if len(user_conversations[user_id]) > 10:
            user_conversations[user_id] = user_conversations[user_id][-10:]

        if "READY_TO_POST: [yes]" in reply:
            clean_reply = reply.replace("READY_TO_POST: [yes]", "").strip()
            pending_posts[user_id] = clean_reply
            keyboard = [
                [
                    InlineKeyboardButton("✅ Post to LinkedIn", callback_data="approve_" + str(user_id)),
                    InlineKeyboardButton("❌ Skip", callback_data="skip_post")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                clean_reply + "\n\nReady to post this on LinkedIn?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text("Error: " + str(e))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("approve_"):
        user_id = int(query.data.replace("approve_", ""))
        post_content = pending_posts.get(user_id)
        if post_content:
            await query.edit_message_text(
                post_content + "\n\n"
                "Copy the post above and paste it on LinkedIn!\n"
                "Auto-posting coming soon."
            )
            del pending_posts[user_id]
        else:
            await query.edit_message_text("Post not found. Please generate again.")

    elif query.data == "skip_post":
        await query.edit_message_text("Skipped! Generate another one anytime.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Voice message mila! Transcribe kar raha hoon...")
    try:
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await voice_file.download_to_drive(tmp_path)

        with open(tmp_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(os.path.basename(tmp_path), audio_file),
                model="whisper-large-v3",
                response_format="text"
            )
        os.unlink(tmp_path)

        await update.message.reply_text("Aapne kaha:\n" + transcription)
        await generate_content(update, transcription)

    except Exception as e:
        await update.message.reply_text("Voice processing error: " + str(e))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(CommandHandler("ideas", ideas))
    app.add_handler(CommandHandler("connect", connect))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("calendar", calendar))
    app.add_handler(CommandHandler("rewrite", rewrite))
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("LinkedIn AI Bot v2 is running!")
    app.run_polling()


if __name__ == "__main__":
    main()
