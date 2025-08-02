from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)

SETTINGS_MENU = "SETTINGS_MENU"

async def settings_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    """Показывает меню настроек."""
    kb = [
        [InlineKeyboardButton("🌐 Язык", callback_data="SET_LANG")],
        [InlineKeyboardButton("⏰ Время отчёта", callback_data="SET_TIME")],
        [InlineKeyboardButton("📅 Пропуск выходных", callback_data="TOGGLE_WEEKENDS")],
        [InlineKeyboardButton("💎 Подписка", callback_data="SUB_STATUS")],
        [InlineKeyboardButton("🐾 Аватар-питомец", callback_data="PET_AVATAR")],
        [InlineKeyboardButton("← Назад", callback_data="BACK_MAIN")],
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(
        "⚙️ <b>Настройки</b>",
            reply_markup = InlineKeyboardMarkup(kb),
            parse_mode = "HTML",
                )
    else:
          # обычное текстовое сообщение → шлём новый
            await update.message.reply_text(
        "⚙️ <b>Настройки</b>",
            reply_markup = InlineKeyboardMarkup(kb),
            parse_mode = "HTML",
        )
    return SETTINGS_MENU

async def settings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    """Обрабатывает нажатия внутри меню настроек (пока лишь заглушки)."""
    data = update.callback_query.data
    await update.callback_query.answer()
    if data == "BACK_MAIN":
        return ConversationHandler.END  # вернёмся в main-router
    await update.callback_query.edit_message_text(
        f"🚧 Функция <code>{data}</code> пока в разработке.",
        parse_mode="HTML"
    )
    return SETTINGS_MENU

__all__ = ["settings_entry", "settings_callback", "SETTINGS_MENU"]