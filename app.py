import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config.config import get_config
from .models.models import db
from .utils.database import create_default_roles, cleanup_old_records
from .routes.auth import auth
from .routes.users import users
from .routes.forms import forms
from .routes.departments import departments
from .routes.dev import dev

def create_app(config_override=None):
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    # Загрузка конфигурации
    config_obj = config_override or get_config()
    app.config.from_object(config_obj)

    # Инициализация расширений
    db.init_app(app)
    jwt = JWTManager(app)
    
    # Обработчики ошибок JWT
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print(f"⚠️ Истек токен: {jwt_payload}")
        return jsonify({
            'status': 401,
            'sub_status': 42,
            'msg': 'Сессия истекла. Пожалуйста, войдите снова.'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"⚠️ Недействительный токен: {error}")
        return jsonify({
            'status': 401,
            'sub_status': 43,
            'msg': 'Недействительный токен. Пожалуйста, войдите снова.'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"⚠️ Отсутствует токен: {error}")
        return jsonify({
            'status': 401,
            'sub_status': 44,
            'msg': 'Отсутствует токен авторизации. Пожалуйста, войдите в систему.'
        }), 401
    
    # Настройка CORS - разрешаем все источники в режиме разработки
    CORS(app, 
         resources={r"/api/*": {
             "origins": ["http://localhost:5173"],  # Разрешаем только frontend origin
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
             "expose_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "allow_credentials": True,
             "max_age": 3600
         }})
    
    # Добавляем обработчик после запроса для логирования
    @app.after_request
    def after_request(response):
        print(f"{request.method} {request.path} -> {response.status_code}")
        return response

    # Регистрация Blueprint'ов
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(users, url_prefix='/api/user')
    app.register_blueprint(forms, url_prefix='/api/forms')
    app.register_blueprint(departments, url_prefix='/api/departments')
    app.register_blueprint(dev, url_prefix='/api/dev')

    # Инициализация базы данных и создание базовых ролей
    with app.app_context():
        # Создаем таблицы, если они не существуют
        db.create_all()  
        print("🗄️ База данных инициализирована")

        create_default_roles()
        cleanup_old_records()

    return app

if __name__ == '__main__':
    app = create_app()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'dev') != 'prod'
    
    print(f"🚀 Сервер запущен на http://{host}:{port}")
    print("📋 Для создания тестового админа: POST /api/dev/test/create-admin")
    print("🧹 Для очистки базы: POST /api/dev/test/cleanup")
    app.run(debug=debug, port=port, host=host)