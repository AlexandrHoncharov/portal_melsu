"""
Скрипт для создания тестового пользователя с указанными учетными данными
"""
from app import create_app
from models.models import db, User, UserProfile, Role
from werkzeug.security import generate_password_hash
from datetime import datetime

# Данные пользователя
USER_EMAIL = 'sanumxxx@yandex.ru'
USER_USERNAME = 'sanum'
USER_PASSWORD = '111111'

# Создаем экземпляр приложения
app = create_app()

with app.app_context():
    # Проверяем, существует ли пользователь
    existing_user = User.query.filter_by(email=USER_EMAIL).first()
    if existing_user:
        print(f"Пользователь с email {USER_EMAIL} уже существует.")
        # Обновляем пароль существующего пользователя
        existing_user.password_hash = generate_password_hash(USER_PASSWORD)
        existing_user.is_verified = True
        db.session.commit()
        print(f"Пароль пользователя обновлен на '{USER_PASSWORD}'")
    else:
        # Создаем нового пользователя
        user = User(
            email=USER_EMAIL,
            username=USER_USERNAME,
            password_hash=generate_password_hash(USER_PASSWORD),
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        # Добавляем пользователя в базу
        db.session.add(user)
        db.session.flush()  # Получаем ID пользователя
        
        # Создаем профиль пользователя
        profile = UserProfile(
            user_id=user.id,
            first_name='Тестовый',
            last_name='Пользователь'
        )
        db.session.add(profile)
        
        # Добавляем роль 'student' пользователю
        student_role = Role.query.filter_by(name='student').first()
        if student_role:
            user.roles.append(student_role)
        else:
            print("Роль 'student' не найдена в базе данных.")
        
        # Сохраняем изменения
        db.session.commit()
        print(f"Создан новый пользователь: {USER_EMAIL} с паролем '{USER_PASSWORD}'")

print("Операция завершена.") 