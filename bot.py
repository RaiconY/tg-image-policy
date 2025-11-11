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

# Фиксированный текст для наложения на изображения
OVERLAY_TEXT = 'ТОО "Ломбард "Деньги Населению", лицензия 10.21.0017.Л берілген күні: 12.03.2021 жыл, ҚР Қаржы нарықтарын реттеу және дамыту агенттігі берген ГЭСВ 179%'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = (
        "Привет! 👋\n\n"
        "Я бот для наложения юридической информации на изображения.\n\n"
        "Как пользоваться:\n"
        "1. Отправьте мне любое изображение\n"
        "2. Получите изображение с юридической информацией снизу слева\n\n"
        "Команды:\n"
        "/start - показать это сообщение\n"
        "/help - справка"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_message = (
        "Справка по использованию бота:\n\n"
        "Просто отправьте изображение (как фото или документ), "
        "и бот автоматически добавит юридическую информацию снизу слева.\n\n"
        "Юридическая информация:\n"
        f"{OVERLAY_TEXT}"
    )
    await update.message.reply_text(help_message)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """
    Разбивает текст на строки, чтобы он помещался по ширине

    Args:
        text: Текст для разбиения
        font: Шрифт для измерения
        max_width: Максимальная ширина в пикселях
        draw: Объект ImageDraw для измерения текста

    Returns:
        Список строк
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        # Пробуем добавить слово к текущей строке
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        test_width = bbox[2] - bbox[0]

        if test_width <= max_width:
            current_line.append(word)
        else:
            # Если текущая строка не пустая, сохраняем её
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Слово само по себе слишком длинное, всё равно добавляем
                lines.append(word)

    # Добавляем последнюю строку
    if current_line:
        lines.append(' '.join(current_line))

    return lines


def add_text_to_image(image: Image.Image, text: str) -> Image.Image:
    """
    Добавляет текст на изображение (юридическая информация снизу слева)

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

    # Размер шрифта зависит от высоты изображения (1.5% от высоты, минимум 10, максимум 20)
    font_size = max(10, min(20, int(height * 0.015)))

    # Пытаемся загрузить шрифт (обычный, не Bold)
    try:
        # Пробуем использовать обычный шрифт DejaVu Sans
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        try:
            # Альтернативный шрифт Liberation Sans
            font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", font_size)
        except:
            try:
                # Если обычных нет, используем Bold но маленький
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                # Используем дефолтный шрифт
                font = ImageFont.load_default()

    # Отступы
    padding = int(width * 0.01)  # 1% от ширины изображения

    # Максимальная ширина текста (ширина изображения минус отступы с обеих сторон)
    max_text_width = width - (padding * 4)

    # Разбиваем текст на строки
    lines = wrap_text(text, font, max_text_width, draw)

    # Вычисляем высоту одной строки
    bbox = draw.textbbox((0, 0), "Тест", font=font)
    line_height = bbox[3] - bbox[1]

    # Межстрочный интервал
    line_spacing = int(line_height * 0.3)

    # Общая высота текстового блока
    total_text_height = len(lines) * line_height + (len(lines) - 1) * line_spacing

    # Вычисляем максимальную ширину среди всех строк
    max_actual_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        max_actual_width = max(max_actual_width, line_width)

    # Позиция снизу слева
    x = padding * 2
    y = height - total_text_height - padding * 2

    # Добавляем полупрозрачный фон для читаемости
    background_bbox = [
        x - padding,
        y - padding,
        x + max_actual_width + padding,
        y + total_text_height + padding
    ]
    draw.rectangle(background_bbox, fill=(0, 0, 0, 150))

    # Рисуем текст построчно белым цветом
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, fill=(255, 255, 255, 255), font=font)
        current_y += line_height + line_spacing

    return img


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
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

        # Добавляем фиксированный текст на изображение
        result_image = add_text_to_image(image, OVERLAY_TEXT)

        # Сохраняем результат в буфер
        output_buffer = BytesIO()
        result_image.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)

        # Отправляем результат
        await update.message.reply_photo(
            photo=output_buffer,
            caption="Юридическая информация добавлена ✓"
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

    # Регистрируем обработчики сообщений
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_photo))

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
