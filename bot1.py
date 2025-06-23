import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import sqlite3
import re

conn = sqlite3.connect('reminders.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS reminders
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              text TEXT,
              time TEXT)''')
conn.commit()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Отправьте напоминание в формате:\n"
        "<code>/remind [текст] [ДД.ММ.ГГГГ ЧЧ:ММ]</code>\n\n"
        "Пример:\n"
        "<code>/remind сделать покушать 23.06.2025 15:30</code>",
        parse_mode="HTML"
    )

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        match = re.match(r'/remind\s+(.+?)\s+(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})', update.message.text)
        if not match:
            raise ValueError

        text = match.group(1)
        day, month, year, hour, minute = map(int, match.group(2, 3, 4, 5, 6))
        
        reminder_time = datetime(year, month, day, hour, minute)
        if reminder_time <= datetime.now():
            await update.message.reply_text("⏳ Нельзя установить напоминание в прошлом!")
            return

        cursor.execute(
            "INSERT INTO reminders (user_id, text, time) VALUES (?, ?, ?)",
            (update.effective_user.id, text, reminder_time.isoformat())
        )
        conn.commit()

        await update.message.reply_text(
            f"✅ Напоминание установлено на {reminder_time.strftime('%d.%m.%Y %H:%M')}:\n"
            f"📌 {text}"
        )

        context.job_queue.run_once(
            callback=send_reminder,
            when=(reminder_time - datetime.now()).total_seconds(),
            data=(update.effective_user.id, text),
            name=str(cursor.lastrowid)
        )

    except Exception:
        await update.message.reply_text(
            "❌ Неверный формат. Пример правильной команды:\n"
            "<code>/remind сделать покушать 23.06.2025 15:30</code>\n\n"
            "Обратите внимание:\n"
            "- Дата и время должны быть в конце сообщения\n"
            "- Используйте точки как разделители даты\n"
            "- Часы и минуты разделяются двоеточием",
            parse_mode="HTML"
        )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    user_id, text = context.job.data
    await context.bot.send_message(chat_id=user_id, text=f"🔔 Напоминание: {text}")

if __name__ == '__main__':
    application = ApplicationBuilder().token('your-token').build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("remind", set_reminder))
    application.run_polling()
