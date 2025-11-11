#!/bin/bash
# Скрипт для быстрого деплоя бота

set -e

echo "🚀 Деплой Telegram бота..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "❌ Ошибка: файл .env не найден!"
    echo "Скопируйте .env.example в .env и заполните токен бота:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Загружаем переменные окружения
export $(cat .env | grep -v '^#' | xargs)

# Проверяем наличие токена
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен в .env"
    exit 1
fi

echo "✅ Токен бота найден"

# Выбор метода деплоя
echo ""
echo "Выберите метод деплоя:"
echo "1) Docker (рекомендуется)"
echo "2) Локально с venv"
echo "3) Только обновить контейнер"
read -p "Введите номер (1-3): " choice

case $choice in
    1)
        echo "🐳 Запуск через Docker..."

        # Останавливаем старый контейнер если есть
        docker-compose down 2>/dev/null || true

        # Собираем и запускаем
        docker-compose up -d --build

        echo "✅ Бот запущен в Docker контейнере"
        echo "📝 Просмотр логов: docker-compose logs -f"
        echo "🛑 Остановка: docker-compose down"
        ;;
    2)
        echo "💻 Запуск локально..."

        # Создаем venv если нет
        if [ ! -d "venv" ]; then
            echo "Создаю виртуальное окружение..."
            python3 -m venv venv
        fi

        # Активируем venv и устанавливаем зависимости
        source venv/bin/activate
        pip install -r requirements.txt

        echo "✅ Зависимости установлены"
        echo "🚀 Запускаю бота..."
        python bot.py
        ;;
    3)
        echo "🔄 Обновление контейнера..."
        docker-compose down
        docker-compose up -d --build
        echo "✅ Контейнер обновлен"
        echo "📝 Просмотр логов: docker-compose logs -f"
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac
