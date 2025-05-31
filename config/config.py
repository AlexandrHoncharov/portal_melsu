import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///university.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT настройки с увеличенным сроком действия
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-string-for-development')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Увеличиваем до 24 часов для разработки
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_SECURE = False  # Для разработки используем False
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_BLACKLIST_ENABLED = False
    
    # Режим тестирования (без отправки писем)
    TESTING = os.environ.get('TESTING', 'false').lower() == 'true'
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'email.melsu.ru')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'help@melsu.ru')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')  # Пароль должен быть в переменной окружения
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'help@melsu.ru')

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True
    # В режиме разработки не отправляем реальные письма
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # В продакшене SECRET_KEY должен быть установлен через переменную окружения
    JWT_COOKIE_SECURE = True  # Для продакшена используем True

config_by_name = {
    'dev': DevelopmentConfig,
    'test': TestingConfig,
    'prod': ProductionConfig
}

def get_config():
    """Возвращает конфигурацию на основе переменной окружения FLASK_ENV"""
    env = os.environ.get('FLASK_ENV', 'dev')
    return config_by_name.get(env, DevelopmentConfig) 