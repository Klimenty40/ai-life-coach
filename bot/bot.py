import os
import logging
from datetime import datetime, timezone
from io import BytesIO

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    PicklePersistence,
    filters,
)
import matplotlib.pyplot as plt

from backend.db import (
    save_event,
    get_daily_metrics_for_date,
    get_weekly_metrics,
    get_settings,
    update_settings,
    set_last_report_request,
    create_profile,
    get_user_profile
)
from backend.recommender import generate_recommendations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MENU, ADD, REPORTS, SETTINGS = range(4)

ADD_SLEEP, ADD_STEPS, ADD_SCREEN, ADD_MOOD = range(10, 14)
SET_LANGUAGE, SET_SUBSCRIPTION, SET_AVATAR, SET_DELETE = range(20, 24)


def build_main_menu():
    return ReplyKeyboardMarkup(
        [["➕ Добавить данные", "📊 Отчёты"], ["👤 Профиль", "⚙️ Настройки"]], resize_keyboard=True
    )


def build_add_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛌 Сон", callback_data="ADD_SLEEP")],
        [InlineKeyboardButton("👟 Шаги", callback_data="ADD_STEPS")],
        [InlineKeyboardButton("📱 Экран-тайм", callback_data="ADD_SCREEN")],
        [InlineKeyboardButton("🙂 Настроение", callback_data="ADD_MOOD")]
    ])


def build_reports_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Сегодня", callback_data="REPORT_TODAY")],
        [InlineKeyboardButton("📈 За неделю", callback_data="REPORT_WEEK")],
        [InlineKeyboardButton("🧠 AI-анализ", callback_data="REPORT_AI")]
    ])


def build_settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏰ Время рассылки", callback_data="SET_TIME")],
        [InlineKeyboardButton("🗓 Пропуск выходных", callback_data="SET_WEEKENDS")],
        [InlineKeyboardButton("🌐 Язык интерфейса", callback_data="SET_LANGUAGE")],
        [InlineKeyboardButton("💎 Подписка Ultra", callback_data="SET_SUBSCRIPTION")],
        [InlineKeyboardButton("🐾 Мой аватар-питомец", callback_data="SET_AVATAR")],
        [InlineKeyboardButton("🗑 Удалить все данные", callback_data="SET_DELETE")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🦊 Добро пожаловать в NeuroFox AI Life Coach", reply_markup=build_main_menu())
    return MENU


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ Добавить данные":
        await update.message.reply_text("Выберите метрику:", reply_markup=build_add_menu())
        return ADD
    if text == "📊 Отчёты":
        await update.message.reply_text("Выберите отчёт:", reply_markup=build_reports_menu())
        return REPORTS
    if text == "👤 Профиль":
        from handlers_profile import profile_entry as show_profile_menu
        return await show_profile_menu(update, context)
    if text == "⚙️ Настройки":
        from handlers_settings import settings_entry as show_settings_menu
        return await show_settings_menu(update, context)
    return MENU


async def add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ADD_SLEEP":
        keyboard = [[InlineKeyboardButton(f"{h} ч", callback_data=f"ADD_SLEEP_{h}") for h in range(5, 10)], [InlineKeyboardButton("🖊 Точно", callback_data="ADD_SLEEP_EXACT")]]
        await query.edit_message_text("Выберите количество сна:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "ADD_STEPS":
        keyboard = [[InlineKeyboardButton(txt, callback_data=f"ADD_STEPS_{txt}") for txt in ["<5000", "5000-8000", "8000-10000", "10000+"]], [InlineKeyboardButton("🖊 Точно", callback_data="ADD_STEPS_EXACT")]]
        await query.edit_message_text("Выберите шаги:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "ADD_SCREEN":
        keyboard = [[InlineKeyboardButton(f"{h} ч", callback_data=f"ADD_SCREEN_{h}") for h in range(1, 4)], [InlineKeyboardButton("🖊 Точно", callback_data="ADD_SCREEN_EXACT")]]
        await query.edit_message_text("Выберите экран-время:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "ADD_MOOD":
        keyboard = [[InlineKeyboardButton(m, callback_data=f"ADD_MOOD_{i}") for i, m in enumerate(["🥱", "😐", "😊", "🚀"], start=1)], [InlineKeyboardButton("🖊 Точно", callback_data="ADD_MOOD_EXACT")]]
        await query.edit_message_text("Выберите настроение:", reply_markup=InlineKeyboardMarkup(keyboard))


async def add_exact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.endswith("EXACT"):
        metric = query.data.split("_")[1].lower()
        await query.message.reply_text("Введите точное значение:", reply_markup=ForceReply())
        context.user_data["exact_metric"] = metric


async def add_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    metric = context.user_data.get("exact_metric")
    if not metric:
        return MENU
    value = int(update.message.text)
    save_event(update.effective_user.id, metric, value)
    await update.message.reply_text(f"{metric} сохранено!", reply_markup=build_main_menu())
    context.user_data.pop("exact_metric", None)
    return MENU


async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    today = datetime.now(timezone.utc).date()
    if query.data == "REPORT_TODAY":
        dms = get_daily_metrics_for_date(today)
        if not dms:
            await query.edit_message_text("Нет данных за сегодня.")
        else:
            m = dms[0]
            txt = f"Сегодня:\nСон: {m.total_sleep} мин\nЭкран: {m.total_screen} мин\nШаги: {m.total_steps}\n"
            await query.edit_message_text(txt)
    elif query.data == "REPORT_WEEK":
        week = get_weekly_metrics(uid, today)
        if not week:
            await query.edit_message_text("Нет данных за неделю.")
        else:
            dates = [m.date.strftime("%d.%m") for m in week]
            pct_steps = [min(m.total_steps / 10000 * 100, 150) for m in week]
            pct_sleep = [min(m.total_sleep / (8 * 60) * 100, 150) for m in week]
            pct_screen = [min(m.total_screen / (2 * 60) * 100, 150) for m in week]
            plt.figure()
            plt.plot(dates, pct_steps, marker='o', label="Шаги")
            plt.plot(dates, pct_sleep, marker='o', label="Сон")
            plt.plot(dates, pct_screen, marker='o', label="Экран")
            plt.ylim(0, 150); plt.legend(); plt.grid(True); plt.tight_layout()
            buf = BytesIO(); plt.savefig(buf, format="png"); buf.seek(0); plt.close()
            await query.message.reply_photo(buf)
    elif query.data == "REPORT_AI":
        dms = get_daily_metrics_for_date(today)
        if not dms:
            await query.edit_message_text("Нет данных для AI-анализа.")
        else:
            recs = await generate_recommendations(dms[0])
            await query.edit_message_text("AI-анализ:\n" + recs)


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "SET_TIME":
        await query.edit_message_text("Функция смены времени (заглушка)")
    elif query.data == "SET_WEEKENDS":
        await query.edit_message_text("Переключение выходных (заглушка)")
    elif query.data == "SET_LANGUAGE":
        await query.edit_message_text("Выбор языка (заглушка)")
    elif query.data == "SET_SUBSCRIPTION":
        await query.edit_message_text("Подписка Ultra (заглушка)")
    elif query.data == "SET_AVATAR":
        await query.edit_message_text("Аватар (заглушка)")
    elif query.data == "SET_DELETE":
        await query.edit_message_text("Удаление данных (заглушка)")


def main():
    token = os.getenv("BOT_TOKEN")
    persistence = PicklePersistence(filepath="bot_data.pkl")
    app = ApplicationBuilder().token(token).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router))
    app.add_handler(CallbackQueryHandler(add_callback, pattern="^ADD_(SLEEP|STEPS|SCREEN|MOOD)$"))
    app.add_handler(CallbackQueryHandler(add_exact_callback, pattern="^ADD_.*_EXACT$"))
    app.add_handler(CallbackQueryHandler(report_callback, pattern="^REPORT_.*$"))
    from handlers_settings import settings_callback
    from handlers_profile import profile_callback, profile_value_handler
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^SET_.*$"))
    app.add_handler(CallbackQueryHandler(profile_callback, pattern="^PROF_.*$"))
    app.add_handler(MessageHandler(filters.REPLY, profile_value_handler))
    app.add_handler(MessageHandler(filters.REPLY, add_value_handler))

    app.run_polling()


if __name__ == "__main__":
    main()