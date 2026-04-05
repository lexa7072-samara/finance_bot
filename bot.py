import os
from datetime import datetime, time
from dotenv import load_dotenv
import pytz
import asyncio

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from database import Database
from categories import CategoryDetector
from analytics import Analytics
from reminders import ReminderMessages

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

db = Database()
category_detector = CategoryDetector(
    db.get_category_keywords(),
    db.get_income_category_keywords()
)
analytics = Analytics()

# Хранилище для пользователей с включенными напоминаниями
reminders_enabled = set()
# Хранилище для редактирования
edit_data = {}

MONTH_NAMES = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
}


def get_main_keyboard():
    keyboard = [
        ["📊 Отчёт за месяц", "💵 Доходы"],
        ["📂 Категории", "🔔 Напоминания"],
        ["📝 История", "❓ Помощь"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_report_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📅 Текущий месяц", callback_data="report_current"),
            InlineKeyboardButton("📆 Прошлый месяц", callback_data="report_previous")
        ],
        [
            InlineKeyboardButton("💵 Доходы", callback_data="income_current")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "👋 Привет! Я твой личный финансовый помощник.\n\n"
    msg += "📝 Как пользоваться:\n"
    msg += "• Расход: 500 продукты\n"
    msg += "• Доход: +50000 зарплата\n\n"
    msg += "📊 Используй кнопки ниже!\n\n"
    msg += "Давай начнём экономить вместе! 💰"
    
    await update.message.reply_text(msg, reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "ℹ️ Справка\n\n"
    msg += "Добавление расхода:\n"
    msg += "• 500 продукты\n"
    msg += "• 1200 такси\n\n"
    msg += "Добавление дохода:\n"
    msg += "• +50000 зарплата\n"
    msg += "• +5000 подработка\n"
    msg += "• +500 кэшбэк\n\n"
    msg += "🔔 Напоминания:\n"
    msg += "• /reminder - включить\n"
    msg += "• /reminder_off - выключить\n\n"
    msg += "В отчёте увидишь % от дохода!"
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=get_main_keyboard())
    else:
        await update.callback_query.message.reply_text(msg, reply_markup=get_main_keyboard())


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categories = db.get_category_keywords()
    text = "📂 Категории расходов:\n\n"
    for category, keywords in categories.items():
        if keywords:
            keywords_str = ", ".join(keywords[:5])
            text += "• " + category + "\n  " + keywords_str + "\n\n"
        else:
            text += "• " + category + "\n\n"
    
    income_categories = db.get_income_category_keywords()
    text += "💵 Категории доходов:\n\n"
    for category, keywords in income_categories.items():
        if keywords:
            keywords_str = ", ".join(keywords[:3])
            text += "• " + category + "\n  " + keywords_str + "\n\n"
        else:
            text += "• " + category + "\n\n"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=get_main_keyboard())
    else:
        await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())


async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📊 Выбери период для отчёта:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=get_report_inline_keyboard())
    else:
        await update.callback_query.message.reply_text(text, reply_markup=get_report_inline_keyboard())


async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE, month_offset=0):
    user_id = update.effective_user.id
    now = datetime.now()
    
    target_month = now.month - month_offset
    target_year = now.year
    
    if target_month <= 0:
        target_month += 12
        target_year -= 1
    
    # Получаем данные за текущий месяц
    expenses = db.get_month_expenses(user_id, target_year, target_month)
    income = db.get_month_income(user_id, target_year, target_month)
    
    expense_totals = analytics.calculate_totals(expenses)
    income_totals = analytics.calculate_income_totals(income)
    
    # Получаем остаток с предыдущих месяцев
    previous_balance = db.get_total_balance(user_id, target_year, target_month)
    
    month_name = MONTH_NAMES[target_month]
    report = analytics.format_report(
        expense_totals, 
        month_name, 
        income_totals['total'],
        previous_balance
    )
    
    await update.callback_query.message.reply_text(report, reply_markup=get_main_keyboard())


async def generate_income_report(update: Update, context: ContextTypes.DEFAULT_TYPE, month_offset=0):
    user_id = update.effective_user.id
    now = datetime.now()
    
    target_month = now.month - month_offset
    target_year = now.year
    
    if target_month <= 0:
        target_month += 12
        target_year -= 1
    
    income = db.get_month_income(user_id, target_year, target_month)
    income_totals = analytics.calculate_income_totals(income)
    
    month_name = MONTH_NAMES[target_month]
    report = analytics.format_income_report(income_totals, month_name)
    
    if update.message:
        await update.message.reply_text(report, reply_markup=get_main_keyboard())
    else:
        await update.callback_query.message.reply_text(report, reply_markup=get_main_keyboard())


async def setup_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включить напоминания"""
    user_id = update.effective_user.id
    
    reminders_enabled.add(user_id)
    
    await update.message.reply_text(
        "✅ Напоминания включены!\n\n"
        "Каждый день в 20:00 (МСК) я буду напоминать записать расходы.\n\n"
        "Отключить: /reminder_off",
        reply_markup=get_main_keyboard()
    )


async def disable_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отключить напоминания"""
    user_id = update.effective_user.id
    
    if user_id in reminders_enabled:
        reminders_enabled.remove(user_id)
        await update.message.reply_text(
            "🔕 Напоминания отключены.\n\n"
            "Включить снова: /reminder",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "ℹ️ Напоминания уже отключены.",
            reply_markup=get_main_keyboard()
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "report_current":
        await generate_report(update, context, month_offset=0)
    
    elif query.data == "report_previous":
        await generate_report(update, context, month_offset=1)
    
    elif query.data == "income_current":
        await generate_income_report(update, context, month_offset=0)
    
    elif query.data == "add_expense_reminder":
        await query.message.reply_text(
            "📝 Отлично! Записывай расход:\n\n"
            "Формат: сумма описание\n"
            "Пример: 500 продукты\n\n"
            "Или доход: +50000 зарплата"
        )
    
    # Подтверждение удаления
    elif query.data.startswith("confirm_del_"):
        expense_id = int(query.data.split("_")[2])
        if db.delete_expense(expense_id, user_id):
            await query.edit_message_text("✅ Запись удалена!")
        else:
            await query.edit_message_text("❌ Не удалось удалить запись.")
    
    elif query.data == "cancel_del":
        await query.edit_message_text("❌ Удаление отменено.")
    
    # Редактирование суммы
    elif query.data.startswith("edit_amount_"):
        expense_id = int(query.data.split("_")[2])
        edit_data[user_id] = {'expense_id': expense_id, 'field': 'amount'}
        await query.edit_message_text(
            "💰 Введи новую сумму:\n\n"
            "Например: 1500"
        )
    
    # Редактирование категории
    elif query.data.startswith("edit_category_"):
        expense_id = int(query.data.split("_")[2])
        edit_data[user_id] = {'expense_id': expense_id, 'field': 'category'}
        
        categories = list(db.get_category_keywords().keys())
        categories_text = "\n".join([f"• {cat}" for cat in categories])
        
        await query.edit_message_text(
            f"📁 Введи новую категорию:\n\n{categories_text}"
        )
    
    # Редактирование описания
    elif query.data.startswith("edit_desc_"):
        expense_id = int(query.data.split("_")[2])
        edit_data[user_id] = {'expense_id': expense_id, 'field': 'description'}
        await query.edit_message_text(
            "📝 Введи новое описание:"
        )
    
    elif query.data == "cancel_edit":
        if user_id in edit_data:
            del edit_data[user_id]
        await query.edit_message_text("❌ Редактирование отменено.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    # Проверяем, не в режиме ли редактирования
    if user_id in edit_data:
        await process_edit(update, context)
        return
    
    if text == "📊 Отчёт за месяц":
        await show_report(update, context)
        return
    elif text == "💵 Доходы":
        await generate_income_report(update, context)
        return
    elif text == "📂 Категории":
        await show_categories(update, context)
        return
    elif text == "🔔 Напоминания":
        await setup_reminder(update, context)
        return
    elif text == "📝 История":
        await show_history(update, context)
        return
    elif text == "❓ Помощь":
        await help_command(update, context)
        return
    
    await handle_expense(update, context)


async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        amount, description, is_income = category_detector.parse_expense(text)
        
        if is_income:
            category = category_detector.detect_income_category(description)
            db.add_expense(user_id, amount, category, description, is_income=True)
            funny = category_detector.get_income_comment(category)
            
            response = "✅ Доход записан!\n\n"
            response += "💵 Сумма: +" + str(amount) + " руб.\n"
            response += "📁 Категория: " + category
        else:
            category = category_detector.detect_category(description)
            db.add_expense(user_id, amount, category, description, is_income=False)
            funny = category_detector.get_funny_comment(category)
            
            response = "✅ Расход записан!\n\n"
            response += "💰 Сумма: " + str(amount) + " руб.\n"
            response += "📁 Категория: " + category
        
        if description:
            response += "\n📝 Описание: " + description
        response += "\n\n" + funny
        
        keyboard = [[InlineKeyboardButton("📊 Посмотреть отчёт", callback_data="report_current")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
        
    except ValueError as e:
        error_msg = "❌ Ошибка: " + str(e) + "\n\nФормат:\n• Расход: 500 продукты\n• Доход: +50000 зарплата"
        await update.message.reply_text(error_msg, reply_markup=get_main_keyboard())
    except Exception as e:
        await update.message.reply_text("❌ Ошибка: " + str(e), reply_markup=get_main_keyboard())


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("❌ Ошибка:", context.error)

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать последние записи"""
    user_id = update.effective_user.id
    
    expenses = db.get_last_expenses(user_id, limit=10)
    
    if not expenses:
        await update.message.reply_text(
            "📝 История пуста.\n\nДобавь первую запись!",
            reply_markup=get_main_keyboard()
        )
        return
    
    text = "📝 Последние 10 записей:\n\n"
    
    for exp in expenses:
        emoji = "💵" if exp['is_income'] else "💸"
        sign = "+" if exp['is_income'] else "-"
        date_short = exp['date'][5:16]  # MM-DD HH:MM
        
        text += f"{emoji} #{exp['id']} | {sign}{exp['amount']} руб.\n"
        text += f"   {exp['category']}"
        if exp['description']:
            text += f" | {exp['description']}"
        text += f"\n   📅 {date_short}\n\n"
    
    text += "Для управления записью:\n"
    text += "• Удалить: /del [номер]\n"
    text += "• Удалить последнюю: /undo\n"
    text += "• Изменить: /edit [номер]"
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard())


async def delete_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить запись по ID"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи номер записи:\n/del 123\n\n"
            "Посмотреть номера: 📝 История",
            reply_markup=get_main_keyboard()
        )
        return
    
    try:
        expense_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Номер должен быть числом!",
            reply_markup=get_main_keyboard()
        )
        return
    
    expense = db.get_expense_by_id(expense_id, user_id)
    
    if not expense:
        await update.message.reply_text(
            f"❌ Запись #{expense_id} не найдена.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Показываем запись и просим подтверждение
    emoji = "💵" if expense['is_income'] else "💸"
    sign = "+" if expense['is_income'] else "-"
    
    text = f"🗑️ Удалить эту запись?\n\n"
    text += f"{emoji} #{expense['id']}\n"
    text += f"Сумма: {sign}{expense['amount']} руб.\n"
    text += f"Категория: {expense['category']}\n"
    if expense['description']:
        text += f"Описание: {expense['description']}\n"
    text += f"Дата: {expense['date'][:16]}"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_del_{expense_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_del")
        ]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def undo_last_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить последнюю запись"""
    user_id = update.effective_user.id
    
    expense = db.delete_last_expense(user_id)
    
    if expense:
        emoji = "💵" if expense['is_income'] else "💸"
        sign = "+" if expense['is_income'] else "-"
        
        await update.message.reply_text(
            f"✅ Последняя запись удалена!\n\n"
            f"{emoji} {sign}{expense['amount']} руб.\n"
            f"Категория: {expense['category']}\n"
            f"Описание: {expense['description'] or '-'}",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Нет записей для удаления.",
            reply_markup=get_main_keyboard()
        )


async def edit_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать редактирование записи"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи номер записи:\n/edit 123\n\n"
            "Посмотреть номера: 📝 История",
            reply_markup=get_main_keyboard()
        )
        return
    
    try:
        expense_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Номер должен быть числом!",
            reply_markup=get_main_keyboard()
        )
        return
    
    expense = db.get_expense_by_id(expense_id, user_id)
    
    if not expense:
        await update.message.reply_text(
            f"❌ Запись #{expense_id} не найдена.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Показываем запись и варианты редактирования
    emoji = "💵" if expense['is_income'] else "💸"
    sign = "+" if expense['is_income'] else "-"
    
    text = f"✏️ Редактирование записи #{expense['id']}\n\n"
    text += f"{emoji} Сумма: {sign}{expense['amount']} руб.\n"
    text += f"📁 Категория: {expense['category']}\n"
    text += f"📝 Описание: {expense['description'] or '-'}\n\n"
    text += "Что изменить?"
    
    keyboard = [
        [InlineKeyboardButton("💰 Сумму", callback_data=f"edit_amount_{expense_id}")],
        [InlineKeyboardButton("📁 Категорию", callback_data=f"edit_category_{expense_id}")],
        [InlineKeyboardButton("📝 Описание", callback_data=f"edit_desc_{expense_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def process_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового значения при редактировании"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in edit_data:
        return False
    
    data = edit_data[user_id]
    expense_id = data['expense_id']
    field = data['field']
    
    try:
        if field == 'amount':
            new_amount = float(text.replace(',', '.'))
            db.update_expense(expense_id, user_id, amount=new_amount)
            await update.message.reply_text(
                f"✅ Сумма изменена на {new_amount} руб.",
                reply_markup=get_main_keyboard()
            )
        
        elif field == 'category':
            db.update_expense(expense_id, user_id, category=text)
            await update.message.reply_text(
                f"✅ Категория изменена на: {text}",
                reply_markup=get_main_keyboard()
            )
        
        elif field == 'description':
            db.update_expense(expense_id, user_id, description=text)
            await update.message.reply_text(
                f"✅ Описание изменено на: {text}",
                reply_markup=get_main_keyboard()
            )
        
        del edit_data[user_id]
        return True
    
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат! Попробуй ещё раз.",
            reply_markup=get_main_keyboard()
        )
        return True
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка: {e}",
            reply_markup=get_main_keyboard()
        )
        del edit_data[user_id]
        return True

# ============================================
# ФУНКЦИЯ ОТПРАВКИ НАПОМИНАНИЙ (перед main)
# ============================================

async def send_reminders_to_all(application):
    """Отправка напоминаний всем пользователям в 20:00 МСК"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    last_sent_date = None
    
    while True:
        now = datetime.now(moscow_tz)
        today = now.date()
        
        # Проверяем: 20:00 и ещё не отправляли сегодня
        if now.hour == 20 and now.minute == 0 and last_sent_date != today:
            print(f"🔔 Отправка напоминаний... Пользователей: {len(reminders_enabled)}")
            
            for user_id in reminders_enabled.copy():
                message = ReminderMessages.get_random_message()
                keyboard = [[InlineKeyboardButton("📝 Записать расход", callback_data="add_expense_reminder")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    await application.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        reply_markup=reply_markup
                    )
                    print(f"✅ Напоминание отправлено: {user_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки для {user_id}: {e}")
            
            last_sent_date = today
        
        # Ждём 30 секунд перед следующей проверкой
        await asyncio.sleep(30)


# ============================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# ============================================

def main():
    print("🤖 Запуск бота...")
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("categories", show_categories))
    application.add_handler(CommandHandler("report", show_report))
    application.add_handler(CommandHandler("reminder", setup_reminder))
    application.add_handler(CommandHandler("reminder_off", disable_reminder))
    application.add_handler(CommandHandler("del", delete_expense_command))
    application.add_handler(CommandHandler("undo", undo_last_expense))
    application.add_handler(CommandHandler("edit", edit_expense_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)
    
    print("✅ Бот запущен!")
    print("📱 Найди бота в Telegram и напиши /start")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_bot():
        async with application:
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            
            reminder_task = asyncio.create_task(send_reminders_to_all(application))
            
            try:
                await asyncio.Future()
            except:
                reminder_task.cancel()
                await application.updater.stop()
                await application.stop()
    
    loop.run_until_complete(run_bot())


if __name__ == "__main__":
    main()