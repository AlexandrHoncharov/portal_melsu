"""
Скрипт для запуска сервера Flask в режиме разработки
"""
import os
import sys
from pathlib import Path

# Добавляем родительскую директорию в sys.path
sys.path.append(str(Path(__file__).parent))

from app import create_app

# Устанавливаем переменные окружения
os.environ['FLASK_ENV'] = 'dev'
os.environ['TESTING'] = 'true'  # Включаем тестовый режим (без отправки реальных писем)

# Создаем приложение
app = create_app()

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 5000
    
    print(f"🚀 Сервер запущен на http://{host}:{port}")
    print("📋 Для создания тестового админа: POST /api/dev/test/create-admin")
    print("🧹 Для очистки базы: POST /api/dev/test/cleanup")
    
    # Запускаем сервер
    app.run(debug=True, port=port, host=host) 