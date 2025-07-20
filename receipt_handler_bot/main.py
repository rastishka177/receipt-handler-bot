
import os
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram import  Router
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram import F
from receipt_handler_bot.google_sheets import add_receipt
from receipt_handler_bot.google_sheets import generate_report_excel
import time
from yandex_disk import upload_file
from utils import generate_receipt_code
from utils import  get_current_date
from receipt_handler_bot.config import BOT_TOKEN, TEMP_DIR

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Временное хранилище данных пользователя
user_data = {}

# /start
@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет! Как называется проект?")
    user_data[message.from_user.id] = {}


# команда /report
@router.message(Command("report"))
async def send_report(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or 'department' not in user_data[user_id]:
        await message.answer("Вы еще не отправляли чеков. Сначала создайте хотя бы один!")
        return

    department = user_data[user_id]['department']
    timestamp = int(time.time())
    report_filename = f"{department}_report_{timestamp}.xlsx"
    report_path = os.path.join(TEMP_DIR, report_filename)

    success = generate_report_excel(department, report_path)
    if not success:
        await message.answer(f"Не удалось найти данные для цеха {department}.")
        return

    # Отправляем файл пользователю
    await message.answer_document(types.FSInputFile(report_path), caption=f"📊 Отчет для цеха {department}")

    # Удаляем файл после отправки (по желанию)
    os.remove(report_path)

# Пользователь пишет название проекта (любое)
@router.message(lambda m: m.from_user.id in user_data and 'project' not in user_data[m.from_user.id])
async def get_project(message: types.Message):
    user_data[message.from_user.id]['project'] = message.text

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Администрация")],
            [KeyboardButton(text="Гримерный цех")],
            [KeyboardButton(text="Реквизиторский цех")],
            [KeyboardButton(text="Костюмерный цех")],
            [KeyboardButton(text="Художественный цех")]
        ],
        resize_keyboard=True
    )
    await message.answer("Какой цех выбираете?", reply_markup=kb)

# Цех
# Выбор цеха
@router.message(lambda m: m.text in [
    "Администрация", "Гримерный цех", "Реквизиторский цех",
    "Костюмерный цех", "Художественный цех"
])
async def get_department(message: types.Message):
    user_data[message.from_user.id]['department'] = message.text

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Трата")],
            [KeyboardButton(text="Поступление")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите позицию: трата или поступление?", reply_markup=kb)

# Трата или поступление
@router.message(lambda m: 'operation' not in user_data[m.from_user.id])
async def get_operation(message: types.Message):
    user_data[message.from_user.id]['operation'] = message.text
    await message.answer("Теперь пришлите фото чека и краткое описание, например: 'Покупка аптечки 26.05'")

router = Router()

# Обработка фото
@router.message(F.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    caption = message.caption or "Без описания"
    user_data[user_id]['description'] = caption

    # Сохраняем фото локально
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    local_file_name = f"{file_id}.jpg"
    local_path = os.path.join(TEMP_DIR, local_file_name)
    await bot.download_file(file_path, local_path)

    # Генерация кода
    project_code = ''.join(filter(str.isalpha, user_data[user_id]['project'].upper()))[:3]
    department_code = ''.join(filter(str.isalpha, user_data[user_id]['department'].upper()))[:2]
    receipt_code = generate_receipt_code(project_code, department_code, user_id % 1000)
    user_data[user_id]['receipt_code'] = receipt_code

    # Сохраняем локальный путь для повторного использования
    user_data[user_id]['local_path'] = local_path

    # Формируем текст для подтверждения
    text = (
        f"Проверьте чек:\n"
        f"Проект: {user_data[user_id]['project']}\n"
        f"Цех: {user_data[user_id]['department']}\n"
        f"Операция: {user_data[user_id]['operation']}\n"
        f"Описание: {caption}\n"
        f"Код чека: {receipt_code}\n\n"
        f"Всё верно?"
    )

    # Кнопки ОК и РЕДАКТИРОВАТЬ ЧЕК
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ОК"), KeyboardButton(text="РЕДАКТИРОВАТЬ ЧЕК")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(text, reply_markup=kb)

# Обработка ответа на подтверждение
@router.message(lambda m: m.text in ["ОК", "РЕДАКТИРОВАТЬ ЧЕК"])
async def handle_check_confirmation(message: types.Message):
    user_id = message.from_user.id
    choice = message.text

    if choice == "ОК":
        # Загружаем в Яндекс.Диск
        local_path = user_data[user_id].get('local_path')
        receipt_code = user_data[user_id]['receipt_code']
        remote_path = f"/{user_data[user_id]['project']}/{user_data[user_id]['department']}/{receipt_code}.jpg"
        link = upload_file(local_path, remote_path)
        user_data[user_id]['photo_link'] = link

        # Добавляем в Google Sheets
        current_date = get_current_date()
        data_row = [
            receipt_code,
            current_date,
            user_data[user_id]['operation'],
            user_data[user_id]['description'],
            link
        ]
        add_receipt(user_data[user_id]['department'], data_row)

        # Удаляем локальный файл
        if os.path.exists(local_path):
            os.remove(local_path)

        await message.answer(f"✅ Чек {receipt_code} успешно зафиксирован!", reply_markup=ReplyKeyboardRemove())
        user_data.pop(user_id, None)  # очищаем данные

    elif choice == "РЕДАКТИРОВАТЬ ЧЕК":
        # Удаляем локальный файл, если сохранился
        local_path = user_data[user_id].get('local_path')
        if local_path and os.path.exists(local_path):
            os.remove(local_path)

        user_data.pop(user_id, None)  # очистить все данные пользователя
        await message.answer("Давайте начнём заново. Как называется проект?", reply_markup=ReplyKeyboardRemove())

# fallback
@router.message()
async def fallback(message: types.Message):
    await message.answer("Пожалуйста, пришлите фото чека с описанием как подпись к фото.")

# Запуск
async def main():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
