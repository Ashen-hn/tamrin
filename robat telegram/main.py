# ==========================
# 🩺 ash MedBot (main.py)
# Telegram Medicine Reminder Bot
# ==========================

import sqlite3
import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)
from dotenv import load_dotenv
import os

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# --------------------------
# Database initialization
# --------------------------
def init_db():
    conn = sqlite3.connect("medbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            medicine TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

# --------------------------
# Start command
# --------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name}! 🌿\n"
        "من ash MedBot هستم — یادآور داروها.\n"
        "برای اضافه کردن داروی جدید بنویس:\n"
        "`/add [نام دارو] [ساعت:دقیقه]`\n"
        "مثلاً: `/add ویتامین D 09:00`",
        parse_mode="Markdown"
    )

# --------------------------
# Add new reminder
# --------------------------
async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("فرمت اشتباهه!\nمثال: `/add بروفن 14:30`", parse_mode="Markdown")
            return

        medicine = " ".join(context.args[:-1])
        time = context.args[-1]

        # Validate time format
        datetime.datetime.strptime(time, "%H:%M")

        conn = sqlite3.connect("medbot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reminders (user_id, medicine, time) VALUES (?, ?, ?)",
                       (update.effective_user.id, medicine, time))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ یادآور برای '{medicine}' در ساعت {time} تنظیم شد.")

    except ValueError:
        await update.message.reply_text("فرمت ساعت اشتباهه! مثال درست: `14:30`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {e}")

# --------------------------
# List all reminders
# --------------------------
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("medbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT medicine, time FROM reminders WHERE user_id=?", (update.effective_user.id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("هنوز یادآوری ثبت نکردی 🕰️")
        return

    text = "🩺 یادآوری‌های فعلی:\n\n"
    for medicine, time in rows:
        text += f"- {medicine} در {time}\n"

    await update.message.reply_text(text)

# --------------------------
# Background reminder loop
# --------------------------
async def reminder_loop(app: Application):
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        conn = sqlite3.connect("medbot.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, medicine FROM reminders WHERE time=?", (now,))
        rows = cursor.fetchall()
        conn.close()

        for user_id, medicine in rows:
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ وقت خوردن داروی *{medicine}* رسیده 💊",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"خطا در ارسال پیام به {user_id}: {e}")

        await asyncio.sleep(60)

# --------------------------
# Inline reminder test
# --------------------------
async def test_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💊 یادآوری تستی", callback_data="remind_test")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("برای تست یادآوری روی دکمه بزن 👇", reply_markup=markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "remind_test":
        await query.edit_message_text("⏰ یادآوری تستی فعال شد! (فقط آزمایشی است)")

# --------------------------
# Main function
# --------------------------
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_reminder))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("test", test_reminder))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Run background reminder task
    app.job_queue.run_repeating(lambda _: asyncio.create_task(reminder_loop(app)), interval=60, first=5)

    print("✅ ash MedBot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
