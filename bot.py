import os
import logging
import asyncio
import tempfile
import httpx
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

# Pending posts waiting for approval
pending_posts = {}

# LinkedIn credentials from environment
LI_EMAIL = os.getenv("LINKEDIN_EMAIL")
LI_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# ── Personal Profile ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are LinkedInGPT — the personal LinkedIn AI manager for Suraj Vishwakarma.

=== SURAJ'S PROFILE ===
Name: Suraj Vishwakarma
Location: Vadodara, India
Current Role: Quality Lead & Business Quality Consultant at Etech Global Services (Jun 2025 - Present)
LinkedIn: linkedin.com/in/surajv42

Professional Summary:
Strategic Quality Lead & Business Consultant with 10+ years of experience in quality assurance, audit governance, and performance management across BPO, healthcare, and service operations. Lean Six Sigma certified professional specializing in multi-process quality frameworks, business insights, and client consulting.

Key Strengths: Quality Governance, Multi-Process QA, RCA & CAPA, CSAT/FCR Metrics, Team Leadership, Power BI & Excel Dashboards, Lean Six Sigma, Process Excellence

Career: Etech Global Services → Kochar Infotech → Wellness Forever Medicare → Medlife International → Zorticos Lifesciences

Certifications: Lean Six Sigma Professional (Expert), Power BI, Excel Dashboard, SQL

Target Audience: Quality professionals, BPO leaders, operations managers, business consultants
Goals: Build personal brand as quality & process excellence expert, attract consulting opportunities
Tone: Professional yet approachable, data-driven, confident, first-person voice

Best Topics: Quality management, Lean Six Sigma, BPO insights, CSAT improvement, leadership, Power BI tips, career lessons, process improvement

=== LANGUAGE RULES ===
- If user writes in Hindi or Hinglish → respond in Hindi (Devanagari script) AND English both
- If user writes in English → respond in English only
- Always write LinkedIn posts in English (professional audience)
- For voice messages → understand Hindi or English, respond accordingly

=== POST FORMAT ===
Always write posts AS Suraj in first person.
1. Hook — strong first line
2. Body — short paragraphs, 1-2 lines each
3. CTA — question or engagement prompt
4. Hashtags — 3-5: #QualityManagement #LeanSixSigma #BPO #ProcessExcellence #Leadership

=== IMPORTANT ===
When asked to write a post for LinkedIn, always end your response with exactly this line:
READY_TO_POST: [yes]
This signals the bot to offer the auto-post option."""

# ── LinkedIn Auto-Post (Unofficial API) ──────────────────────────────────────
async def post_to_linkedin(content: str) -> tuple[bool, str]:
    """Post to LinkedIn using unofficial API via linkedin-api library simulation."""
    try:
        # Using linkedin_api library approach
        import subprocess
        result = subprocess.run(
            ["python3", "-c", f"""
import os
try:
    from linkedin_api import Linkedin
    api = Linkedin('{LI_EMAIL}', '{LI_PASSWORD}')
    # linkedin_api doesn't support posting directly
    # We use the internal share endpoint
    import requests
    session = api._session
    headers = {{
        'Content-Type': 'application/json',
        'X-RestLi-Protocol-Version': '2.0.0',
    }}
    profile = api.get_profile()
    urn = profile.get('entityUrn', '').replace('urn:li:fs_profile:', 'urn:li:person:')
    payload = {{
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {{
            "com.linkedin.ugc.ShareContent": {{
                "shareCommentary": {{"text": """{content}"""}},
                "shareMediaCategory": "NONE"
            }}
        }},
        "visibility": {{"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
    }}
    r = session.post('https://api.linkedin.com/v2/ugcPosts', json=payload, headers=headers)
    print('SUCCESS' if r.status_code == 201 else f'FAIL:{{r.status_code}}')
except Exception as e:
    print(f'ERROR:{{e}}')
"""],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        if "SUCCESS" in output:
            return True, "✅ Posted successfully to LinkedIn!"
        else:
            return False, f"❌ LinkedIn posting failed: {output}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


# ── Voice Transcription ───────────────────────────────────────────────────────
async def transcribe_voice(file_path: str) -> str:
    """Transcribe voice using Groq Whisper."""
    try:
        with open(file_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=(os.path.basename(file_path), audio_file),
                model="whisper-large-v3",
                language=None,  # auto-detect Hindi or English
                response_format="text"
            )
        return transcription
    except Exception as e:
        return f"ERROR:{str(e)}"


# ── Core AI Generator ─────────────────────────────────────────────────────────
async def generate_content(update: Update, user_message: str, show_post_button: bool = False):
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

        # Check if post is ready for LinkedIn
        if "READY_TO_POST: [yes]" in reply:
            clean_reply = reply.replace("READY_TO_POST: [yes]", "").strip()

            # Store post content for approval
            pending_posts[user_id] = clean_reply

            # Show approval buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Post to LinkedIn", callback_data=f"approve_post_{user_id}"),
                    InlineKeyboardButton("❌ Skip", callback_data="skip_post")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                clean_reply + "\n\n─────────────────\n🚀 *Ready to post this on LinkedIn?*",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ── Callback Handler (Post Approval) ─────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("approve_post_"):
        user_id = int(query.data.replace("approve_post_", ""))
        post_content = pending_posts.get(user_id)

        if not post_content:
            await query.edit_message_text("⚠️ Post content not found. Please generate again.")
            return

        if not LI_EMAIL or not LI_PASSWORD:
            await query.edit_message_text(
                "⚠️ LinkedIn credentials not set up yet!\n\n"
                "Add these to Render Environment Variables:\n"
                "• `LINKEDIN_EMAIL` — your LinkedIn email\n"
                "• `LINKEDIN_PASSWORD` — your LinkedIn password\n\n"
                "Then redeploy. For now, copy the post above and paste it manually on LinkedIn! 📋"
            )
            return

        await query.edit_message_text("⏳ Posting to LinkedIn... please wait.")
        success, message = await post_to_linkedin(post_content)
        await query.edit_message_text(message)
        if user_id in pending_posts:
            del pending_posts[user_id]

    elif query.data == "skip_post":
        await query.edit_message_text("👍 No problem! You can copy the post above and paste it on LinkedIn manually.")


# ── Command Handlers ──────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """👋 Hey Suraj! Main hoon aapka LinkedIn AI Manager! 🤖

Main jaanta hoon aapka poora profile:
✅ Quality Lead & Business Consultant
✅ 10+ years BPO & Healthcare experience
✅ Lean Six Sigma Expert
✅ Vadodara, India

*Commands:*
/post [topic] — LinkedIn post likhna
/ideas — 10 post ideas aapke niche ke liye
/connect [role] — Outreach message
/profile — Profile improve karna
/calendar — 2-week content calendar
/rewrite [text] — Post improve karna
/announce — "Managed by AI" post banao
/clear — History clear karo

🎙️ *Voice messages bhi bhej sakte ho!*
🌐 *Hindi ya English — dono samajhta hoon!*

Kya karna hai aaj? 💪"""
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text(msg, parse_mode="Markdown")


async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text(
            "📝 Kis topic par post likhun?\n\nExample:\n"
            "/post lessons from 10 years in quality management\n"
            "/post how to improve CSAT in BPO"
        )
        return
    await generate_content(
        update,
        f"Write a LinkedIn post for Suraj about: {topic}. Write in first person. End with READY_TO_POST: [yes]",
        show_post_button=True
    )


async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(
        update,
        "Give Suraj 10 specific LinkedIn post ideas based on his quality management, BPO, Lean Six Sigma background."
    )


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args) if context.args else None
    if not role:
        await update.message.reply_text("🤝 Kisko connect karna hai?\nExample: /connect VP of Operations at BPO")
        return
    await generate_content(
        update,
        f"Write a LinkedIn connection message from Suraj to a {role}. Warm, specific, under 150 words."
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(
        update,
        "Suggest improvements for Suraj's LinkedIn: 1) Powerful headline, 2) Strong About section, 3) 3 achievement bullets for his current role."
    )


async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(
        update,
        "Create a 2-week LinkedIn content calendar for Suraj. Mix: quality tips, BPO insights, Lean Six Sigma, leadership, Power BI. Include day, theme, post angle."
    )


async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("✏️ Post paste karo:\n/rewrite [aapka post yahan]")
        return
    await generate_content(
        update,
        f"Rewrite this LinkedIn post for Suraj with better hook and CTA. End with READY_TO_POST: [yes]\n\n{text}",
        show_post_button=True
    )


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate the 'managed by AI' announcement post."""
    prompt = """Write a LinkedIn post for Suraj Vishwakarma announcing that his LinkedIn profile is now being managed with the help of AI. 

The post should:
- Be authentic and professional, not gimmicky
- Explain that he's using AI as a tool to share more consistent insights from his 10+ years of quality management experience
- Emphasize that all thoughts and expertise are still 100% his own — AI just helps him express them better and more consistently
- Invite his network to engage and give feedback
- Sound exciting and forward-thinking
- Be relevant to his quality management / BPO / consulting audience

End with READY_TO_POST: [yes]"""
    await generate_content(update, prompt, show_post_button=True)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text("🗑️ History clear ho gayi! Fresh start. 🚀")


# ── Voice Message Handler ─────────────────────────────────────────────────────
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎙️ Voice message mila! Transcribe kar raha hoon...")

    try:
        # Download voice file
        voice = update.message.voice
        voice_file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await voice_file.download_to_drive(tmp_path)

        # Transcribe with Groq Whisper
        transcribed_text = await transcribe_voice(tmp_path)
        os.unlink(tmp_path)

        if transcribed_text.startswith("ERROR:"):
            await update.message.reply_text(f"❌ Transcription failed: {transcribed_text}")
            return

        await update.message.reply_text(f"📝 *Aapne kaha:*\n_{transcribed_text}_", parse_mode="Markdown")

        # Now process the transcribed text as a regular message
        await generate_content(update, transcribed_text)

    except Exception as e:
        await update.message.reply_text(f"❌ Voice processing error: {str(e)}")


# ── Text Message Handler ──────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, update.message.text)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
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

    logger.info("🤖 LinkedIn AI Bot v2 is running!")
    app.run_polling()


if __name__ == "__main__":
    main()
