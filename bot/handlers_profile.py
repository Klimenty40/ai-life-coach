from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

PROFILE_MENU = "PROFILE_MENU"

async def profile_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    """Главное меню профиля — выбор, что редактировать."""
    kb = [
        [InlineKeyboardButton("♂️ / ♀️ Пол", callback_data="PROF_GENDER")],
        [InlineKeyboardButton("🎂 Возраст", callback_data="PROF_AGE")],
        [InlineKeyboardButton("⚖️ Вес", callback_data="PROF_WEIGHT")],
        [InlineKeyboardButton("📏 Рост", callback_data="PROF_HEIGHT")],
        [InlineKeyboardButton("🎯 Цель", callback_data="PROF_GOAL")],
        [InlineKeyboardButton("← Назад", callback_data="BACK_MAIN")],
    ]
    if update.callback_query:
         # Вернулись из inline-кнопки «← Назад» – редактируем существующее сообщение
        await update.callback_query.edit_message_text(
       "👤 <b>Профиль</b>\nВыберите, что хотите изменить:",
            reply_markup = InlineKeyboardMarkup(kb),
            parse_mode = "HTML",
        )
    else:
      # Пришли из главного меню – отправляем новое сообщение, чтобы его было
      # разрешено редактировать позже
        await update.message.reply_text(
        "👤 <b>Профиль</b>\nВыберите, что хотите изменить:",
            reply_markup = InlineKeyboardMarkup(kb),
            parse_mode = "HTML",
        )
    return PROFILE_MENU


async def profile_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    """Пока выводит заглушку о том, что функция в разработке."""
    data = update.callback_query.data
    await update.callback_query.answer()

    if data == "BACK_MAIN":
        # Возврат к ConversationHandler.END позволит внешнему роутеру
        # показать главное меню.
        return ConversationHandler.END

    await update.callback_query.edit_message_text(
        f"🚧 Раздел <code>{data}</code> ещё не реализован.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Назад", callback_data="BACK_PROFILE")]]
        ),
    )
    return PROFILE_MENU


# экспортируем, чтобы импорт «видел» эти имена
__all__ = ["profile_entry", "profile_callback", "PROFILE_MENU"]

async def profile_value_handler(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
) -> str:
    """Принимает введённое значение профиля, временно просто подтверждает."""
    value = update.message.text.strip()
    await update.message.reply_text(
        f"✅ Сохранил: <code>{value}</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

# экспортируем, чтобы бот.py увидел имя
__all__.append("profile_value_handler")