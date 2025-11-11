#!/usr/bin/env python3
"""
Telegram бот для наложения текста на изображения
"""

import os
import logging
from io import BytesIO
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont

# Загружаем переменные окружения из .env файла (если есть)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv не установлен - это нормально, будем использовать системные переменные
    pass

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("Необходимо установить переменную окружения TELEGRAM_BOT_TOKEN")

# Глобальные настройки для текста
user_texts = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = (
        "Привет! 👋\n\n"
        "Я бот для наложения текста на изображения.\n\n"
        "Как пользоваться:\n"
        "1. Отправьте команду /text с текстом, который хотите добавить\n"
        "   Например: /text Мой текст\n"
        "2. Отправьте мне изображение\n"
        "3. Получите изображение с наложенным текстом\n\n"
        "Команды:\n"
        "/start - показать это сообщение\n"
        "/text <текст> - установить текст для наложения\n"
        "/help - справка"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_message = (
        "Справка по использованию бота:\n\n"
        "1. Установите текст командой:\n"
        "   /text Ваш текст здесь\n\n"
        "2. Отправьте изображение (как фото или документ)\n\n"
        "3. Бот вернет изображение с наложенным текстом\n\n"
        "Текст будет размещен по центру изображения с полупрозрачным фоном."
    )
    await update.message.reply_text(help_message)


async def set_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /text для установки текста"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Использование: /text <ваш текст>\n"
            "Например: /text Привет, мир!"
        )
        return

    # Объединяем все аргументы в один текст
    text = ' '.join(context.args)
    user_texts[user_id] = text

    await update.message.reply_text(
        f"Текст установлен: '{text}'\n\n"
        "Теперь отправьте изображение, чтобы наложить на него этот текст."
    )


def add_text_to_image(image: Image.Image, text: str) -> Image.Image:
    """
    Добавляет текст на изображение

    Args:
        image: Исходное изображение PIL
        text: Текст для наложения

    Returns:
        Изображение с наложенным текстом
    """
    # Создаем копию изображения
    img = image.copy()
    draw = ImageDraw.Draw(img, 'RGBA')

    # Получаем размеры изображения
    width, height = img.size

    # Пытаемся загрузить шрифт
    try:
        # Пробуем использовать стандартный шрифт (если доступен)
        font_size = max(30, min(width, height) // 15)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        try:
            # Альтернативный шрифт
            font_size = max(30, min(width, height) // 15)
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", font_size)
        except:
            # Используем дефолтный шрифт
            font = ImageFont.load_default()

    # Получаем размеры текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Вычисляем позицию для центрирования текста
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # Добавляем полупрозрачный фон для текста
    padding = 20
    background_bbox = [
        x - padding,
        y - padding,
        x + text_width + padding,
        y + text_height + padding
    ]
    draw.rectangle(background_bbox, fill=(0, 0, 0, 180))

    # Рисуем текст
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    return img


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
    user_id = update.effective_user.id

    # Проверяем, установлен ли текст для пользователя
    if user_id not in user_texts:
        await update.message.reply_text(
            "Сначала установите текст с помощью команды /text\n"
            "Например: /text Мой текст"
        )
        return

    text = user_texts[user_id]

    # Отправляем сообщение о начале обработки
    processing_msg = await update.message.reply_text("Обрабатываю изображение...")

    try:
        # Получаем файл изображения
        if update.message.photo:
            # Берем самое качественное фото
            photo_file = await update.message.photo[-1].get_file()
        elif update.message.document:
            photo_file = await update.message.document.get_file()
        else:
            await processing_msg.edit_text("Ошибка: не удалось получить изображение")
            return

        # Загружаем изображение в память
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(BytesIO(photo_bytes))

        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Добавляем текст на изображение
        result_image = add_text_to_image(image, text)

        # Сохраняем результат в буфер
        output_buffer = BytesIO()
        result_image.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)

        # Отправляем результат
        await update.message.reply_photo(
            photo=output_buffer,
            caption=f"Текст '{text}' добавлен на изображение ✓"
        )

        # Удаляем сообщение о обработке
        await processing_msg.delete()

    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        await processing_msg.edit_text(f"Произошла ошибка при обработке изображения: {str(e)}")


def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("text", set_text))

    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_photo))

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
