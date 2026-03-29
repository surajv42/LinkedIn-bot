import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
user_conversations = {}

SYSTEM_PROMPT = """You are LinkedInGPT — the personal LinkedIn AI manager for Suraj Vishwakarma.

=== SURAJ'S PROFILE ===
Name: Suraj Vishwakarma
Location: Vadodara, India
Current Role: Quality Lead & Business Quality Consultant at Etech Global Services (Jun 2025 - Present)
LinkedIn: linkedin.com/in/surajv42

Professional Summary:
Strategic Quality Lead & Business Consultant with 10+ years of experience in quality assurance, audit governance, and performance management across BPO, healthcare, and service operations. Lean Six Sigma certified professional specializing in multi-process quality frameworks, business insights, and client consulting. Proven ability to improve CSAT, reduce defects, and enable business growth through data-driven quality intelligence.

Key Strengths:
- Quality Governance & Consulting
- Multi-Process QA Management
- Client-Facing Business Insights
- Root Cause Analysis (RCA) & CAPA
- CSAT, FCR, QA & Compliance Metrics
- Team Leadership & Coaching
- Excel & Power BI Dashboards
- Process Excellence (Lean Six Sigma)

Career History:
- Quality Lead / Business Quality Consultant @ Etech Global Services (Jun 2025 - Present)
- Sr. Quality Analyst (Quality Lead - Operations) @ Kochar Infotech (Feb 2021 - Jun 2025)
- Floor Supervisor (SME) @ Wellness Forever Medicare (Aug 2018 - Aug 2020)
- Sales Executive @ Medlife International (Jun 2017 - Jul 2018)
- Medical Representative @ Zorticos Lifesciences (Jan 2015 - Apr 2017)

Certifications:
- Lean Six Sigma Professional (Expert)
- Data Analysis - Power BI
- Excel Dashboard - Simplilearn
- SQL - SoloLearn

Industry: BPO, Healthcare, Service Operations, Quality Management
Target Audience: Quality professionals, BPO leaders, operations managers, business consultants, HR professionals, aspiring quality analysts
Goals on LinkedIn: Build personal brand as a quality & process excellence expert, attract consulting opportunities, share knowledge, grow professional network
Tone: Professional yet approachable, data-driven, insightful, confident

Best Post Topics for Suraj:
- Quality management tips and frameworks
- Lean Six Sigma insights and real examples
- BPO industry trends and challenges
- CSAT improvement strategies
- Leadership and team coaching stories
- Power BI / Excel dashboard tips
- Career journey and lessons learned
- Process improvement case studies
- Customer experience excellence
- Business consulting insights

=== YOUR JOB ===
Always write posts AS Suraj or FROM Suraj's perspective. Use first-person voice ("I", "my team", "in my experience").
Every post must sound authentic to someone with 10+ years in quality management in India.
Use real industry terminology: CSAT, FCR, RCA, CAPA, QA framework, calibration, SOP, etc.
Keep posts relatable to Indian BPO and service industry professionals.

When writing posts:
1. Hook — strong first line that stops the scroll
2. Body — story, insight, or tip from Suraj's experience (short paragraphs, 1-2 lines each)
3. CTA — ask a question or invite engagement
4. Hashtags — 3-5 relevant ones like #QualityManagement #LeanSixSigma #BPO #ProcessExcellence #Leadership

When asked for ideas, give topics specific to Suraj's niche.
When writing connection messages, write as Suraj reaching out.
When optimizing profile sections, tailor to his background.
Always be ready to copy-paste onto LinkedIn."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """👋 Hey Suraj! I'm your LinkedIn AI Manager.

I know your full profile — Quality Lead, Lean Six Sigma expert, 10+ years in BPO & healthcare. Every post I write will sound exactly like YOU.

Commands:
/post [topic] - Write a post as you
/ideas - Get 10 post ideas for your niche
/connect [role] - Write an outreach message
/profile - Improve your profile sections
/calendar - 2-week content calendar
/rewrite [text] - Improve an existing post
/clear - Clear chat history

Or just type naturally! 💪"""
    user_conversations[update.effective_user.id] = []
    await update.message.reply_text(msg)

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else None
    if not topic:
        await update.message.reply_text("📝 What topic? Example:\n/post lessons from 10 years in quality management")
        return
    await generate_content(update, f"Write a LinkedIn post for Suraj about: {topic}. Write in first person as Suraj. Include hook, story/insight, CTA, and hashtags.")

async def ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, "Give Suraj 10 specific LinkedIn post ideas based on his background in quality management, BPO, Lean Six Sigma, and business consulting. Make them specific and engaging for his target audience.")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    role = " ".join(context.args) if context.args else None
    if not role:
        await update.message.reply_text("🤝 Who are you reaching out to? Example:\n/connect VP of Operations at a BPO company")
        return
    await generate_content(update, f"Write a LinkedIn connection message from Suraj Vishwakarma (Quality Lead & Business Consultant) to a {role}. Keep it warm, specific, under 150 words.")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, "Based on Suraj's background, suggest improvements for his LinkedIn: 1) A more powerful headline, 2) A stronger About section opening (3-4 lines), 3) 3 achievement-focused bullet points for his current role at Etech Global Services.")

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await generate_content(update, "Create a 2-week LinkedIn content calendar for Suraj Vishwakarma. Mix topics: quality tips, leadership stories, BPO insights, Lean Six Sigma, career lessons, Power BI tips. Include day, theme, and specific post angle for each day.")

async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else None
    if not text:
        await update.message.reply_text("✏️ Paste your post:\n/rewrite [your post text here]")
        return
    await generate_content(update, f"Rewrite and improve this LinkedIn post for Suraj. Keep his voice but make it more engaging with a better hook and stronger CTA:\n\n{text}")

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
